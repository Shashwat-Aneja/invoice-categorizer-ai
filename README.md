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

Use `--json` to emit complete category counts and optional currency-separated totals. Decimal amounts are JSON strings so downstream tools do not silently lose invoice precision.

Use `--escape-formulas` when CSV exports will be opened in spreadsheet software. Formula-like text cells beginning with `=`, `+`, `-` or `@` after leading whitespace receive an apostrophe; numeric cells and in-memory calculations remain unchanged. The default export preserves original text.

`--delimiter ";"`, `--delimiter tab` and `--delimiter "|"` support alternate input CSV separators, including quoted fields. Duplicate-header validation uses the selected separator. The default input and all CSV exports remain comma-separated.

`--date-column date --start-date 2026-01-01 --end-date 2026-01-31` selects inclusive local calendar dates before categorization, totals and exports. Missing/invalid dates and empty selections fail explicitly; the default remains all rows. Numeric epoch offsets are not accepted as calendar dates.

`--review-output review.csv` exports ambiguous and unmatched descriptions with explanation columns for manual triage. Optional complete exports retain all selected invoices. The review file cannot alias the source or complete export and follows `--escape-formulas`. Each output is atomic individually; multiple output files are not a single transaction.
