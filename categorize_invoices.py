import argparse
from pathlib import Path
import re

import pandas as pd

CATEGORY_RULES = (
    ("Rent", re.compile(r"\b(?:rent|lease)\b", re.IGNORECASE)),
    ("Utilities", re.compile(r"\b(?:electricity|water|utility|utilities|gas|internet|broadband)\b", re.IGNORECASE)),
    ("Equipment", re.compile(r"\b(?:sensor|laptop|hardware|equipment)\b", re.IGNORECASE)),
    ("Travel", re.compile(r"\b(?:travel|flight|airfare|hotel|taxi|cab|transport|train ticket)\b", re.IGNORECASE)),
    ("Marketing", re.compile(r"\b(?:marketing|advertising|advertisement|campaign|promotion)\b", re.IGNORECASE)),
    ("Software", re.compile(r"\b(?:software|subscription|saas|cloud hosting|domain renewal)\b", re.IGNORECASE)),
    ("Insurance", re.compile(r"\b(?:insurance|premium)\b", re.IGNORECASE)),
    ("Payroll", re.compile(r"\b(?:salary|payroll|wages|stipend)\b", re.IGNORECASE)),
    ("Vendor Payment", re.compile(r"\b(?:invoice|vendor|supplier)\b", re.IGNORECASE)),
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


def summarize_categories(df):
    """Return category counts in descending frequency order."""
    if "category" not in df.columns:
        raise ValueError("DataFrame must contain a 'category' column.")
    counts = df["category"].value_counts(dropna=False)
    return {str(category): int(count) for category, count in counts.items()}


def process_invoice_file(csv_file, output_csv=None):
    try:
        df = pd.read_csv(csv_file)
        if "description" not in df.columns:
            print("❌ CSV must contain a 'description' column.")
            return 1

        df = df.copy()
        df["category"] = df["description"].apply(categorize)
        if output_csv is not None:
            source_path = Path(csv_file).expanduser().resolve()
            output_path = Path(output_csv).expanduser().resolve()
            if source_path == output_path:
                print("❌ Output CSV must be different from the source file.")
                return 1
            output_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                df.to_csv(output_path, index=False)
            except OSError as exc:
                print(f"❌ Could not write categorized CSV: {exc}")
                return 1

        print("\n===== Invoice Categorization Report =====")
        print(df[["description", "category"]].to_string(index=False))
        print("\nCategory totals:")
        for category, count in summarize_categories(df).items():
            print(f"  {category}: {count}")
        print("=========================================\n")
        return 0
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        print(f"❌ Error reading file: {exc}")
        return 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="Categorize invoice descriptions from a CSV file.")
    parser.add_argument("csv_file", help="Input CSV containing a description column")
    parser.add_argument(
        "--output",
        "-o",
        help="Optional destination CSV containing the original columns and assigned categories",
    )
    args = parser.parse_args(argv)
    return process_invoice_file(args.csv_file, output_csv=args.output)


if __name__ == "__main__":
    raise SystemExit(main())
