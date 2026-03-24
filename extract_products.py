import argparse
import json
import os
import re
import sys
import unicodedata
from typing import List, Dict, Tuple

from google import genai
from dotenv import load_dotenv


load_dotenv()

DEFAULT_MODEL = "gemini-3-pro-preview"


def _extract_product_lines(text: str) -> List[Tuple[int, str]]:
    """
    Pre-parse input to identify product lines (lines starting with - or •).
    Returns list of (line_number, content) tuples.
    Handles pipe-separated values by replacing pipes with spaces.
    """
    products = []
    lines = text.split('\n')
    line_num = 1
    
    for idx, line in enumerate(lines, 1):
        line = line.strip()
        # Skip empty lines and noise indicators
        if not line or line.startswith(('Non-product', 'noise:', 'Accessoires')):
            continue
        
        # Product lines typically start with - or •
        if line.startswith(('-', '•')):
            # Remove the leading dash/bullet
            content = line.lstrip('-•').strip()
            
            # Skip lines that are clearly not products
            if len(content) < 5:
                continue
            
            # Skip noise patterns
            if content.startswith(('Conseil', 'Livraison', 'Accessoires', 'Reviews')):
                continue
            
            # Handle pipe-separated values: replace pipes with spaces
            pipe_count = content.count('|')
            if pipe_count > 0:
                # Replace pipes with spaces and clean up multiple spaces
                content = re.sub(r'\s*\|\s*', ' ', content)
                content = re.sub(r'\s+', ' ', content).strip()
            
            # Skip if it looks like encoded/OCR garbage (too many % or mixed case patterns)
            percent_count = content.count('%')
            if percent_count > 2:
                continue
            
            products.append((idx, content))
    
    return products


def _clean_product_name(raw_name: str) -> str:
    """
    Use regex to clean product name: remove measurements, qualifiers, etc.
    Handles pipe-separated values and various product encoding formats.
    """
    cleaned = raw_name
    
    # Handle concatenated descriptors (e.g., "SOINANTI-ROUGEUURS" -> split into "SOIN ANTI-ROUGEURS")
    # Insert spaces before capital letters in concatenated words marked as descriptors
    cleaned = re.sub(r'(SOIN)(ANTI)', r'\1 \2', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'(ANTI[A-Z])', r' \1', cleaned)
    
    # Fix common OCR typos in French product descriptors
    cleaned = re.sub(r'ROUGEUURS?', 'ROUGEURS', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'NTENSIF', 'INTENSIF', cleaned, flags=re.IGNORECASE)
    
    # Remove "lot X", "lot 2x200ml" patterns completely
    cleaned = re.sub(r'\s+lot\s+\d+x\d+(?:ml|g)?', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+lot\b', '', cleaned, flags=re.IGNORECASE)
    
    # Remove quantity markers (2x200ml, 3x100ml, etc.)
    cleaned = re.sub(r'\s+\d+x\d+(?:ml|g|l)?', '', cleaned, flags=re.IGNORECASE)
    
    # Remove standalone "promo" word
    cleaned = re.sub(r'\s+promo\b', '', cleaned, flags=re.IGNORECASE)
    
    # Remove percentages and promo discounts (promo -15%, -20%, etc.)
    # But keep them if they're likely ingredient percentages within the name
    cleaned = re.sub(r'\s+(?:promo)?\s*-?\s*\d+\s*%(?=\s|$)', '', cleaned, flags=re.IGNORECASE)
    
    # Remove measurements (ml, g, kg, l, oz, FL OZ, etc.)
    cleaned = re.sub(r'\s+\d+(?:\.\d+)?\s*(?:ml|l|litre|liter|g|gram|kg|kilo|oz|fl\s?oz)\b', '', cleaned, flags=re.IGNORECASE)
    
    # Remove marketing terms and qualifiers
    cleaned = re.sub(r'\s+(?:edition\s+limitee|limited\s+edition|nouvelle\s+formule|new\s+formula|fortifiant|verbesserte\s+formel)\b', '', cleaned, flags=re.IGNORECASE)
    
    # Remove "pack of X", "buy X get X" patterns
    cleaned = re.sub(r'\s+(?:pack\s+of|buy\s+|get\s+)\s*\d+', '', cleaned, flags=re.IGNORECASE)
    
    # Remove trailing + or ® or ™ or © when clearly separate
    cleaned = re.sub(r'\s+[+®™©]\s*$', '', cleaned)
    cleaned = re.sub(r'[+®™©]\s+$', '', cleaned)
    
    # Remove common French/English product descriptors and benefit claims
    # These typically come at the end or scattered in pipe-separated values
    descriptor_pattern = r'\s+(?:ANTI-?REDNESS|MOISTURISING|MOISTURIZING|INTENSIVE|INTENSIF|NTENSIVE|NTENSIF|CARE|SC|HYDRATANT|APAISANT|TREATMENT|SERUM|GEL|CREAM|BALM|SPRAY|LOTION|SHAMPOO|CONDITIONER|MASK|OIL|ESSENCE|TONER|SOAP|CLEANER|CLEANSER|WASH|FOAM|MOUSSE|SOIN|ANTI-?ROUGEURS?|ANTI-?ROUGES?|SUPER|ULTRA)\b'
    cleaned = re.sub(descriptor_pattern, '', cleaned, flags=re.IGNORECASE)
    
    # Clean up extra spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned


def extract_product_names(text: str, model: str | None = None) -> List[Dict[str, any]]:
    """
    Extract product names from text using:
    1. Regex-based line identification (prevents hallucination)
    2. Regex-based cleaning (deterministic)
    3. Optional LLM for complex OCR corrections only
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY. Add it to your environment or .env file.")

    # Step 1: Identify product lines using regex
    product_lines = _extract_product_lines(text)
    
    if not product_lines:
        return []
    
    # Step 2: Clean each product line using regex only
    cleaned_products = []
    seen = set()
    
    for line_num, raw_content in product_lines:
        cleaned_name = _clean_product_name(raw_content)
        
        if not cleaned_name or len(cleaned_name.strip()) < 3:
            continue
        
        # Deduplication
        norm_key = cleaned_name.lower()
        if norm_key in seen:
            continue
        seen.add(norm_key)
        
        cleaned_products.append({
            "name": cleaned_name,
            "line": line_num,
            "confidence": 1.0
        })
    
    # Step 3: Optional: Use LLM ONLY to fix OCR errors, NOT to extract
    if model or os.getenv("GEMINI_MODEL"):
        client = genai.Client(api_key=api_key)
        requested_model = model or os.getenv("GEMINI_MODEL") or DEFAULT_MODEL
        
        # Format products as plain text for OCR correction
        products_text = "\n".join([f"- {p['name']}" for p in cleaned_products])
        
        prompt = f"""Fix ONLY OCR errors in these product names. Do NOT change, add, or remove products.

RULES:
- Fix 0→O confusion: "L'0real" → "L'Oreal"
- Fix common typos: "Shampo0ing" → "Shampooing"
- Normalize accents slightly if needed for readability
- Do NOT add, remove, or create any new product names
- Return ONLY a JSON list of corrected names

Product names to fix:
{products_text}

Return: {{"products": ["name1", "name2", ...]}}"""

        try:
            response = client.models.generate_content(
                model=requested_model,
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            
            raw = (response.text or "").strip()
            if raw:
                try:
                    data = json.loads(raw)
                    corrected = data.get("products", [])
                    if isinstance(corrected, list) and len(corrected) == len(cleaned_products):
                        # Only use corrected names if same count (prevents hallucination)
                        for i, name in enumerate(corrected):
                            if isinstance(name, str):
                                cleaned_products[i]["name"] = name.strip()
                except json.JSONDecodeError:
                    pass  # Keep original cleaned names
        except Exception:
            pass  # Keep original cleaned names if LLM fails
    
    return cleaned_products


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract product references from text file or stdin."
    )
    parser.add_argument("input", nargs="?", help="Input file path or text. If omitted, reads from stdin.")
    parser.add_argument(
        "--model",
        default=None,
        help="Gemini model name. Defaults to GEMINI_MODEL from .env.",
    )
    args = parser.parse_args()

    # Try to read as file first, then as text
    text = None
    if args.input:
        # Check if it's a file
        if os.path.isfile(args.input):
            try:
                with open(args.input, 'r', encoding='utf-8') as f:
                    text = f.read().strip()
            except Exception as e:
                print(f"Error reading file: {e}", file=sys.stderr)
                return 1
        else:
            # Treat as direct text
            text = args.input.strip()
    
    # If no input arg, read from stdin
    if not text:
        text = sys.stdin.read().strip()
    
    if not text:
        print("Provide text as argument, file path, or through stdin.", file=sys.stderr)
        return 1

    try:
        products = extract_product_names(text=text, model=args.model)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if products:
        print("Extracted Products:")
        print("-" * 60)
        for i, product in enumerate(products, 1):
            print(f"{i}. {product['name']} [{product['confidence']}]")
        print("-" * 60)
        print(f"Total: {len(products)} products")
    else:
        print("No products found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
