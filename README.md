# Product Extractor (Gemini API)

This project extracts product references (brand + product name) from raw text using the Gemini API.

It is tuned to:
- Handle noisy text (OCR-style errors like 0 instead of o).
- Normalize accents before analysis.
- Remove packaging and marketing descriptors such as 200ml, 250ml, Edition Limitee, etc.
- Return clean JSON output.

## 1) Prerequisites

- Python 3.10+
- A valid Gemini API key

## 2) Install dependencies

In the project folder:

python -m pip install -r requirements.txt

## 3) Configure environment

Edit the .env file:

GEMINI_API_KEY=YOUR_REAL_API_KEY
GEMINI_MODEL=gemini-2.5-flash

## 4) Run extraction

From direct text:

python extract_products.py "Garnier Fructis Shampo0ing Fortifiant 250ml Edition Limitee"

From a file (stdin):

python extract_products.py < test_products_pharma.txt
python extract_products.py < test_products_parapharma.txt

## 5) Expected output format

The script prints JSON like:

{"products": ["Garnier Fructis Shampooing"]}

