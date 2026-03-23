import argparse
import json
import os
import re
import sys
import unicodedata
from typing import List

from google import genai
from dotenv import load_dotenv


load_dotenv()

DEFAULT_MODEL = "gemini-2.5-flash"

DESCRIPTOR_PATTERN = re.compile(
    r"\b(\d+[\.,]?\d*\s?(?:ml|l|g|kg|oz|fl\s?oz)|edition\s+limitee|limited\s+edition|fortifiant|verbesserte\s+formel)\b",
    re.IGNORECASE,
)


def _strip_accents(value: str) -> str:
    """Removes diacritics (e.g., é, è, ö) while keeping base characters."""
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _normalized_name_key(name: str) -> str:
    """Builds a normalization key for semantic dedupe across noisy variants."""
    key = name.strip().lower()
    # Replace common OCR digit substitutions only when surrounded by letters.
    key = re.sub(r"(?<=[a-z])0(?=[a-z])", "o", key)
    # Collapse accents/diacritics: "k\N{LATIN SMALL LETTER O WITH DIAERESIS}rper" -> "korper".
    key = "".join(
        ch
        for ch in unicodedata.normalize("NFKD", key)
        if not unicodedata.combining(ch)
    )
    key = re.sub(r"\s+", " ", key)
    return key


def _clean_product_reference(value: str) -> str:
    """Removes packaging/marketing descriptors while keeping brand + product reference."""
    cleaned = DESCRIPTOR_PATTERN.sub("", value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,;-")
    return cleaned


def extract_product_names(text: str, model: str | None = None) -> List[str]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY. Add it to your environment or .env file.")

    client = genai.Client(api_key=api_key)
    requested_model = model or os.getenv("GEMINI_MODEL") or DEFAULT_MODEL
    text_for_analysis = _strip_accents(text)

    prompt = f"""
You are an information extraction system.

Task:
Extract product references mentioned in the input text.

Output contract:
- Return ONLY JSON (no markdown, no explanations).
- Use exactly this schema: {{"products": ["..."]}}
- "products" must be an array of strings.

Extraction rules:
- Return brand + product reference only (example: "Garnier Fructis Shampooing").
- Remove packaging/quantity/promotional descriptors: "250ml", "200ml", "Edition Limitee", "Limited Edition", etc.
- Remove marketing/formulation qualifiers when they are not part of the core product reference.
- Keep clear product model references when relevant.
- Exclude generic categories (example: "lip gloss", "headphones", "laptop").
- Exclude quantities, prices, promo text, and shipping terms.
- Exclude person names, job titles, and organization names that are not products.
- If no product references are present, return {{"products": []}}.
- Deduplicate semantically identical product references.

Normalization guidance for noisy input:
- Treat common OCR substitutions as equivalent when they appear inside words: 0 -> o (example: "Shampo0ing" -> "Shampooing").
- Treat accented variants as equivalent when useful for matching (example: "\N{LATIN SMALL LETTER O WITH DIAERESIS}" and "o").
- Remove legitimate model numbers unchanged (example: "XPS 13", "WH-1000XM5", "250ml").
- Prefer a readable, corrected product reference in final output.

Input text:
{text_for_analysis}
""".strip()

    candidate_models = [requested_model]
    if requested_model != DEFAULT_MODEL:
        candidate_models.append(DEFAULT_MODEL)

    last_error = None
    response = None
    for candidate in candidate_models:
        try:
            response = client.models.generate_content(
                model=candidate,
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            break
        except Exception as exc:
            last_error = exc
            error_text = str(exc)
            if "404" in error_text and "no longer available" in error_text.lower():
                continue
            raise

    if response is None:
        raise RuntimeError(
            f"No available model from candidates: {candidate_models}. Last error: {last_error}"
        )

    raw = (response.text or "").strip()
    if not raw:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Model did not return valid JSON. Raw output: {raw}") from exc

    products = data.get("products", data.get("brands", []))
    if not isinstance(products, list):
        return []

    cleaned = []
    seen = set()
    for item in products:
        if not isinstance(item, str):
            continue
        name = _clean_product_reference(item.strip())
        if not name:
            continue
        normalized_key = _normalized_name_key(name)
        if normalized_key in seen:
            continue
        seen.add(normalized_key)
        cleaned.append(name)

    return cleaned


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract product references (brand + product name) from text using Gemini API."
    )
    parser.add_argument("text", nargs="?", help="Input product text. If omitted, reads from stdin.")
    parser.add_argument(
        "--model",
        default=None,
        help="Gemini model name. Defaults to GEMINI_MODEL from .env or gemini-2.5-flash.",
    )
    args = parser.parse_args()

    text = args.text if args.text is not None else sys.stdin.read().strip()
    if not text:
        print("Provide text either as an argument or through stdin.", file=sys.stderr)
        return 1

    try:
        products = extract_product_names(text=text, model=args.model)
    except Exception as exc:  # Keep user-facing errors simple for CLI usage
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({"products": products}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
