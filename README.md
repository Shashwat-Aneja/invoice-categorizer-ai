# Invoice Categorizer AI

A simple NLP tool that categorizes invoices based on their description into business-relevant labels.  
This project demonstrates text processing, automation logic, and integrates well with financial systems like XYLO.

---

## 📊 Supported Categories
| Category | Examples of matches |
|----------|---------------------|
| Rent | office rent, lease |
| Utilities | electricity, water bill |
| Equipment | hardware, laptops |
| Vendor Payment | consulting, invoice |
| Miscellaneous | others |

---

## 🧪 CSV Input Example
```
description,amount
Office rent January,12000
Electricity bill,3500
Bought sensor module,1500
Vendor invoice #452,9000
Snacks,500
```

---

## 🚀 Usage

### 1. Clone the repo
```bash
git clone https://github.com/Shashwat-Aneja/invoice-categorizer-ai
cd invoice-categorizer-ai
```

### 2. Install dependencies
```bash
pip install pandas
```

### 3. Run the script
```bash
python categorize_invoices.py data.csv
```

---

## 📁 Project Structure
```
invoice-categorizer-ai/
│
├── categorize_invoices.py
└── README.md
```

---

## 📌 Future Enhancements
- Use NLP libraries (spaCy or transformers)
- Train custom financial categorization model
- Connect directly into XYLO’s OCR pipeline

---

Developed by **Shashwat Aneja**

Use `--amount-column amount` to report category totals in addition to counts. Totals remain separated by currency when a currency column exists; missing currency metadata is labeled unspecified. Negative amounts are retained as credits/refunds, and non-finite amounts are rejected before export.

`--explain --output categorized.csv` includes all matching rule categories and a `needs_review` flag for unmatched or ambiguous descriptions. The selected category retains the documented rule priority.

Amount summaries use decimal arithmetic and preserve CSV amount text during loading, preventing binary floating-point rounding and large-integer precision loss. Returned amount totals are `Decimal` values.

Console previews default to 20 invoice rows. `--max-display-rows N` controls the preview only; CSV exports and category totals still include the complete input.
