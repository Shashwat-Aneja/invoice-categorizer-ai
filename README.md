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

Seekable caller-owned text and UTF-8 binary CSV streams now receive the same duplicate-header checks as file paths, before pandas can rename ambiguous columns. Validation restores the starting position and leaves caller streams open; nonseekable stream objects are rejected explicitly.

`--rules-json rules.json` loads custom category-to-keyword lists, matched literally with word-edge checks before built-in fallbacks. Custom rules are bounded to 100 categories and 1,000 keywords of at most 100 characters. JSON duplicate categories are rejected; explanations report distinct matching categories, including any built-in ambiguity.

`--id-column invoice_id` validates non-empty unique IDs after optional date selection and before exports. IDs are read as text to preserve leading zeros; surrounding whitespace is ignored for uniqueness checks. Duplicate rows are rejected, never silently dropped.

CSV paths ending in `.gz`, `.bz2`, or `.xz` are supported without unpacking a separate file. Header validation reads the same compression format as pandas and still rejects duplicate columns, including BOM-prefixed quoted headers and alternate delimiters. Archive containers such as ZIP/TAR are outside this feature.

`--custom-rules-only --rules-json taxonomy.json` disables built-in fallback categories for workflows with a strict custom taxonomy. Non-empty custom rules are required; unmatched descriptions remain Miscellaneous and are still eligible for manual review.

Corrupt compressed bodies, invalid DEFLATE blocks and header-parser limit failures use the normal validation-error path rather than escaping as EOFError, zlib.error or csv.Error. Header inspection restores caller stream position/ownership on these failures. No invalid input is exported.

### Optional raw CSV row budget

Use `--max-input-rows 100000` to reject an input file with more than that many data rows before modeling or export. The budget is per file, including comparison/training/scoring inputs, and applies before filtering or aggregation. The default remains unlimited. Values must be integers from 1 to 10,000,000. Only the budget plus one rows are loaded; oversized inputs fail rather than being silently truncated. This is a row limit, not a byte or field-size limit. Python callers can use `max_rows=`.

Explain/review exports include `review_reason`: `unmatched`, `multiple_categories`, or `none`. An existing source column of that name is rejected before export when diagnostics are requested.
