import re
import sys

import pandas as pd

CATEGORY_RULES = (
    ("Rent", re.compile(r"\b(?:rent|lease)\b", re.IGNORECASE)),
    ("Utilities", re.compile(r"\b(?:electricity|water|utility|utilities|bill)\b", re.IGNORECASE)),
    ("Equipment", re.compile(r"\b(?:sensor|laptop|hardware|equipment)\b", re.IGNORECASE)),
    ("Vendor Payment", re.compile(r"\b(?:invoice|vendor)\b", re.IGNORECASE)),
)


def categorize(description):
    """Map an invoice description to a stable business expense category."""
    if pd.isna(description):
        return "Miscellaneous"
    desc = str(description).strip()
    if not desc:
        return "Miscellaneous"

    for category, pattern in CATEGORY_RULES:
        if pattern.search(desc):
            return category
    return "Miscellaneous"


def process_invoice_file(csv_file):
    try:
        df = pd.read_csv(csv_file)
        if "description" not in df.columns:
            print("❌ CSV must contain a 'description' column.")
            return 1

        df = df.copy()
        df["category"] = df["description"].apply(categorize)
        print("\n===== Invoice Categorization Report =====")
        print(df[["description", "category"]].to_string(index=False))
        print("=========================================\n")
        return 0
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        print(f"❌ Error reading file: {exc}")
        return 1


def main():
    if len(sys.argv) != 2:
        print("Usage: python categorize_invoices.py <csv_file>")
        return 2
    return process_invoice_file(sys.argv[1])


if __name__ == "__main__":
    raise SystemExit(main())
