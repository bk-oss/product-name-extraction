# Product Name Extraction Tool

A high-precision product name extractor designed to extract brand + product references from messy, noisy text inputs (receipts, OCR-ed documents, product lists). Uses a **hybrid approach**: regex-based extraction (deterministic, prevents hallucination) with optional LLM-powered OCR correction.

## Features

✅ **No Hallucination** - Regex-based line identification prevents inventing products  
✅ **Deterministic Cleaning** - Removes measurements, quantities, marketing terms via regex patterns  
✅ **OCR Error Handling** - Fixes common mistakes: `L'0real` → `L'Oreal`, `Shampo0ing` → `Shampooing`  
✅ **Noisy Data Filtering** - Automatically filters out noise, corrupted lines, and non-product text  
✅ **Preserves Order** - Products extracted in the order they appear in input  
✅ **High Confidence Scoring** - All extracted products have 1.0 confidence (only actual products extracted)

## How It Works

### 3-Step Pipeline:

1. **Line Identification (Regex)**
   - Scans for lines starting with `-` or `•`
   - Filters out noise sections (Non-product, Conseil, Livraison, etc.)
   - Detects and extracts from heavily corrupted lines (too many pipes)

2. **Cleaning (Regex)**
   - Removes measurements: `100ml`, `500g`, `%`
   - Removes quantities: `lot 2x200ml`, `pack of`, `buy 1 get`
   - Removes marketing: `edition limitee`, `nouvelle formule`, `promo -15%`
   - Removes special characters: `+`, `®`, `™`, `©`

3. **Optional OCR Correction (LLM)**
   - Uses Gemini API (if enabled) to fix OCR errors only
   - Does NOT add/remove/invent products - validates output count matches input count
   - Falls back to regex-cleaned names if LLM fails

## Prerequisites

- **Python 3.10+**
- **Gemini API key** (free tier available at [ai.google.dev](https://ai.google.dev))

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/product-name-extraction.git
   cd product-name-extraction
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   Create or edit `.env` file:
   ```
   GEMINI_API_KEY=your_actual_api_key_here
   GEMINI_MODEL=gemini-2.5-flash
   ```

## Usage

### From File:
```bash
python extract_products.py test_products_parapharma.txt
python extract_products.py /path/to/your/file.txt
```

### From Direct Text:
```bash
python extract_products.py "La Roche-Posay Cicaplast Baume B5+ 100ml edition limitee"
```

### From Standard Input:
```bash
python extract_products.py < test_products_pharma.txt
```

## Output Format

The script prints extracted products in a clean, readable format:

```
Extracted Products:
------------------------------------------------------------
1. La Roche-Posay Cicaplast Baume B5+ [1.0]
2. Bioderma Sensibio H2O eau micellaire [1.0]
3. Avene Cleanance Gel Nettoyant [1.0]
4. Uriage Xemose Creme Relipidante [1.0]
5. SVR Sebiaclear Serum [1.0]
6. Mustela Stelatopia Huile Lavante [1.0]
7. Vichy Dercos Shampooing Anti-Pelliculaire [1.0]
8. Ducray Anaphase+ Shampooing [1.0]
9. SVR [1.0]
------------------------------------------------------------
Total: 9 products
```

## Example Input & Output

### Input (Messy):
```
- La Roche-Posay Cicaplast Baume B5+ 100ml edition limitee
- Bioderma Sensibio H2O eau micellaire 500ml
- Avene Cleanance Gel Nettoyant 400ml lot 2x200ml
- SVR Sebiaclear Serum 30ml nouvelle formule
- Ducray Anaphase+ Shampooing 400ml promo -15%
```

### Output (Clean):
```
1. La Roche-Posay Cicaplast Baume B5+
2. Bioderma Sensibio H2O eau micellaire
3. Avene Cleanance Gel Nettoyant
4. SVR Sebiaclear Serum
5. Ducray Anaphase+ Shampooing
```

## Testing

Test files are included:
- `test_products_pharma.txt` - Pharmacy products (prescriptions, medications)
- `test_products_parapharma.txt` - Parapharmacy products (cosmetics, skincare)

```bash
python extract_products.py test_products_parapharma.txt
python extract_products.py test_products_pharma.txt
```

## Architecture

```
extract_products.py
├── _extract_product_lines()     # Regex-based line identification
├── _clean_product_name()        # Regex-based cleaning
└── extract_product_names()      # Main extraction pipeline
    └── Optional: LLM OCR correction (Gemini API)
```

## Why This Approach?

**Pure LLM extraction** suffers from hallucination - it can "complete predictions" and invent products that don't exist.

**This hybrid approach:**
- ✅ Guarantees no hallucination (regex controls scope)
- ✅ Fast and deterministic (regex processes instantly)
- ✅ Optional LLM for OCR fixes (improves accuracy without risk)
- ✅ Transparent and auditable

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Your Gemini API authentication key | `sk-xyz...` |
| `GEMINI_MODEL` | Gemini model to use (optional, defaults to gemini-2.5-flash) | `gemini-2.5-flash` |

## License

MIT License - see LICENSE file for details

## Support

If you encounter issues:
1. Check that `.env` has a valid `GEMINI_API_KEY`
2. Verify file encoding is UTF-8
3. Ensure input lines start with `-` or `•` to be recognized as products
4. Check test files for format examples

## Contributing

Contributions welcome! Please submit issues or pull requests on GitHub.

