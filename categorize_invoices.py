import argparse
import math
import os
from pathlib import Path
import re
import tempfile

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


def explain_category(description):
    """Expose all matching categories so ambiguous rules can be reviewed."""
    text = "" if pd.isna(description) else str(description).strip()
    matches = [category for category, pattern in CATEGORY_RULES if pattern.search(text)]
    return {"category": matches[0] if matches else "Miscellaneous",
            "matching_categories": matches,
            "needs_review": len(matches) != 1}


def summarize_categories(df):
    """Return category counts in descending frequency order."""
    if "category" not in df.columns:
        raise ValueError("DataFrame must contain a 'category' column.")
    counts = df["category"].value_counts(dropna=False)
    return {str(category): int(count) for category, count in counts.items()}


def _write_csv_atomically(df, output_path):
    """Replace an export only after the complete CSV has been written successfully."""
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            dir=output_path.parent,
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            df.to_csv(temporary_file, index=False)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        os.replace(temporary_path, output_path)
    except Exception:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise


def summarize_category_amounts(df, amount_column="amount"):
    if amount_column not in df.columns:
        raise ValueError(f"Amount column {amount_column!r} was not found.")
    if df[amount_column].map(lambda value: isinstance(value, bool)).any():
        raise ValueError("Invoice amounts must be numeric, not booleans.")
    amounts = pd.to_numeric(df[amount_column], errors="coerce")
    if amounts.isna().any() or not amounts.map(lambda value: math.isfinite(float(value))).all():
        raise ValueError("Invoice amounts must be finite numeric values.")
    data = df.copy()
    data["_amount"] = amounts
    if "currency" in data.columns:
        if data["currency"].isna().any() or data["currency"].astype(str).str.strip().eq("").any():
            raise ValueError("Currency cannot be blank when amount totals are requested.")
        data["currency"] = data["currency"].astype(str).str.strip().str.upper()
    else:
        data["currency"] = "unspecified"
    totals = []
    for (category, currency), group in data.groupby(["category", "currency"], sort=True):
        try:
            total = math.fsum(float(value) for value in group["_amount"])
        except OverflowError as exc:
            raise ValueError("Invoice totals exceed the supported numeric range.") from exc
        totals.append({"category": category, "currency": currency, "invoice_count": len(group), "total_amount": total})
    return totals


def process_invoice_file(csv_file, output_csv=None, amount_column=None, explain=False):
    try:
        df = pd.read_csv(csv_file)
        if "description" not in df.columns:
            print("❌ CSV must contain a 'description' column.")
            return 1

        if df.empty:
            print("❌ CSV contains no invoice rows.")
            return 1
        df = df.copy()
        df["category"] = df["description"].apply(categorize)
        if explain:
            explanations = df["description"].apply(explain_category)
            df["matching_categories"] = explanations.map(lambda item: "; ".join(item["matching_categories"]))
            df["needs_review"] = explanations.map(lambda item: item["needs_review"])
        amount_totals = summarize_category_amounts(df, amount_column) if amount_column else []
        if output_csv is not None:
            source_path = Path(csv_file).expanduser().resolve()
            output_path = Path(output_csv).expanduser().resolve()
            same_file = source_path == output_path
            if not same_file and output_path.exists():
                try:
                    same_file = source_path.samefile(output_path)
                except OSError:
                    # Fail closed when an existing destination cannot be checked.
                    same_file = True
            if same_file:
                print("❌ Output CSV must be different from the source file.")
                return 1
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                _write_csv_atomically(df, output_path)
            except OSError as exc:
                print(f"❌ Could not write categorized CSV: {exc}")
                return 1

        print("\n===== Invoice Categorization Report =====")
        print(df[["description", "category"]].to_string(index=False))
        print("\nCategory totals:")
        for category, count in summarize_categories(df).items():
            print(f"  {category}: {count}")
        for total in amount_totals:
            print(f"  {total['category']} [{total['currency']}]: {total['total_amount']:.2f}")
        print("=========================================\n")
        return 0
    except (OSError, pd.errors.ParserError, ValueError) as exc:
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
    parser.add_argument("--amount-column", help="Report category amount totals, separated by currency when present")
    parser.add_argument("--explain", action="store_true", help="Include matching categories and ambiguity flags in the export")
    args = parser.parse_args(argv)
    options = {"amount_column": args.amount_column} if args.amount_column else {}
    if args.explain:
        options["explain"] = True
    return process_invoice_file(args.csv_file, output_csv=args.output, **options)


if __name__ == "__main__":
    raise SystemExit(main())
