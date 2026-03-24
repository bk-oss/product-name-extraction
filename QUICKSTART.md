# Quick Start Guide

## 1 Minute Setup

### Step 1: Get API Key
1. Go to [ai.google.dev](https://ai.google.dev)
2. Sign in with Google account
3. Create a new API key
4. Copy it

### Step 2: Setup Project
```bash
git clone https://github.com/yourusername/product-name-extraction.git
cd product-name-extraction

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows or: source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure
Copy `.env.example` to `.env` and add your API key:
```bash
cp .env.example .env
# Edit .env with your GEMINI_API_KEY
```

### Step 4: Run
```bash
python extract_products.py test_products_parapharma.txt
```

## Expected Output
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

## Common Commands

### Extract from file:
```bash
python extract_products.py path/to/file.txt
```

### Extract from text:
```bash
python extract_products.py "La Roche-Posay Baume B5+ 100ml"
```

### Pipe from another command:
```bash
cat products.txt | python extract_products.py
```

## Troubleshooting

**No products found?**
- Ensure lines start with `-` or `•`
- Check file encoding is UTF-8

**API key error?**
- Verify `.env` file exists and has `GEMINI_API_KEY`
- Restart the application after changing `.env`

**Strange product names?**
- That's likely OCR noise in the input - it's working as designed
- Enable LLM OCR correction (it's automatic if API key is set)

Need help? Check the main [README.md](README.md)
