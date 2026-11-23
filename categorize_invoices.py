import io
import csv
import argparse
from numbers import Number
import json
import math
from decimal import Context, Decimal, InvalidOperation, localcontext
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


def _read_csv_input(csv_file, delimiter=",", **options):
    if delimiter not in (",", ";", "\t", "|"):
        raise ValueError("Unsupported input delimiter.")
    _reject_duplicate_headers(csv_file, delimiter)
    frame = pd.read_csv(csv_file, **options, **({"sep": delimiter} if delimiter != "," else {}))
    return frame


def escape_csv_formulas(frame):
    """Escape formula-like text in a copy; leave numeric cells unchanged."""
    def escape(value):
        if isinstance(value, str) and value.lstrip(" \t\r\n").startswith(("=", "+", "-", "@")):
            return "'" + value
        return value
    return frame.apply(lambda column: column.map(escape))


def _reject_duplicate_headers(csv_file, delimiter=","):
    """Inspect original UTF-8 CSV headers without taking ownership of streams."""
    def header_lines(source):
        # csv.reader needs physical lines even for StringIO objects whose default
        # iterator does not recognize CR-only records. Preserve quoted newlines.
        pending = ""
        first = True
        started = False
        while True:
            chars = []
            while True:
                char = pending or source.read(1)
                pending = ""
                if not char:
                    break
                if first:
                    first = False
                    if char == "\ufeff":
                        continue
                chars.append(char)
                if char == "\r":
                    following = source.read(1)
                    if following == "\n":
                        chars.append(following)
                    else:
                        pending = following
                    break
                if char == "\n":
                    break
            if not chars:
                return
            line = "".join(chars)
            if not started and not line.strip():
                continue
            started = True
            yield line

    if isinstance(csv_file, (str, os.PathLike)):
        if not Path(csv_file).is_file():
            return
        with open(csv_file, encoding="utf-8-sig", newline="") as source:
            headers = next(csv.reader(header_lines(source), delimiter=delimiter), [])
    else:
        if not all(hasattr(csv_file, name) for name in ("read", "seek", "tell")) or (hasattr(csv_file, "seekable") and not csv_file.seekable()):
            raise ValueError("CSV streams must be seekable for header validation.")
        position = csv_file.tell()
        binary = isinstance(csv_file.read(0), bytes)
        source = io.TextIOWrapper(csv_file, encoding="utf-8-sig", newline="") if binary else csv_file
        try:
            headers = next(csv.reader(header_lines(source), delimiter=delimiter), [])
        finally:
            if binary:
                source.detach()
            csv_file.seek(position)
    if len(headers) != len(set(headers)):
        raise ValueError("CSV column names must be unique; duplicate headers are ambiguous.")


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
    if "category" not in df.columns or df.columns.duplicated().any():
        raise ValueError("Amount totals require unique columns and a category column.")
    if df["category"].isna().any() or df["category"].astype(str).str.strip().eq("").any():
        raise ValueError("Invoice categories cannot be blank when totals are requested.")
    if amount_column not in df.columns:
        raise ValueError(f"Amount column {amount_column!r} was not found.")
    if df[amount_column].map(lambda value: isinstance(value, bool)).any():
        raise ValueError("Invoice amounts must be numeric, not booleans.")
    try:
        amounts = df[amount_column].map(lambda value: Decimal(str(value)))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Invoice amounts must be finite numeric values.") from exc
    if not amounts.map(lambda value: value.is_finite() and abs(value.as_tuple().exponent) <= 1000 and len(value.as_tuple().digits) <= 1000 and value.adjusted() <= 308).all():
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
        # Preserve every input decimal place, including large integer amounts.
        values = group["_amount"].tolist()
        precision = max(value.adjusted() for value in values) - min(value.as_tuple().exponent for value in values) + len(str(len(values))) + 3
        with localcontext(Context(prec=max(28, precision), Emin=-999999, Emax=999999)) as context:
            total = sum(values, Decimal(0))
        totals.append({"category": category, "currency": currency, "invoice_count": len(group), "total_amount": total})
    return totals


def filter_invoice_dates(frame, date_column=None, start_date=None, end_date=None):
    if date_column is None:
        if start_date is not None or end_date is not None:
            raise ValueError("A date_column is required for invoice date filters.")
        return frame
    if date_column not in frame.columns:
        raise ValueError("Invoice date column was not found.")
    if frame[date_column].map(lambda value: isinstance(value, Number)).any():
        raise ValueError("Invoice dates must be calendar dates, not numeric offsets.")
    parsed = frame[date_column].map(lambda value: pd.to_datetime(value, errors="coerce"))
    if parsed.isna().any():
        raise ValueError("Invoice dates must be valid calendar dates.")
    dates = parsed.map(lambda value: value.date())
    bounds = []
    for value in (start_date, end_date):
        if value is None:
            bounds.append(None)
            continue
        if isinstance(value, Number):
            raise ValueError("Invoice date bounds must be calendar dates.")
        try:
            bound = pd.Timestamp(value)
            if pd.isna(bound):
                raise ValueError("Missing date bound")
            bounds.append(bound.date())
        except (ValueError, TypeError) as exc:
            raise ValueError("Invoice date bounds must be valid calendar dates.") from exc
    start, end = bounds
    if start is not None and end is not None and start > end:
        raise ValueError("Invoice start date must not follow the end date.")
    mask = pd.Series(True, index=frame.index)
    if start is not None:
        mask &= dates >= start
    if end is not None:
        mask &= dates <= end
    result = frame.loc[mask].copy()
    if result.empty:
        raise ValueError("No invoices fall within the selected calendar dates.")
    return result


def process_invoice_file(csv_file, output_csv=None, amount_column=None, explain=False, max_display_rows=20, json_output=False, escape_formulas=False, delimiter=",", date_column=None, start_date=None, end_date=None, review_csv=None):
    try:
        if not isinstance(max_display_rows, int) or isinstance(max_display_rows, bool) or max_display_rows < 1:
            raise ValueError("max_display_rows must be a positive integer.")
        df = _read_csv_input(csv_file, delimiter, dtype={amount_column: "string"} if amount_column else None)
        if "description" not in df.columns:
            print("❌ CSV must contain a 'description' column.")
            return 1

        if df.empty:
            print("❌ CSV contains no invoice rows.")
            return 1
        df = filter_invoice_dates(df, date_column, start_date, end_date)
        if amount_column in {"category", "matching_categories", "needs_review"}:
            raise ValueError("Amount column cannot use a generated categorization column name.")
        df = df.copy()
        df["category"] = df["description"].apply(categorize)
        if explain or review_csv is not None:
            explanations = df["description"].apply(explain_category)
            df["matching_categories"] = explanations.map(lambda item: "; ".join(item["matching_categories"]))
            df["needs_review"] = explanations.map(lambda item: item["needs_review"])
        amount_totals = summarize_category_amounts(df, amount_column) if amount_column else []
        review_path = Path(review_csv).expanduser().resolve() if review_csv is not None else None
        if review_path is not None:
            protected = [Path(csv_file).expanduser().resolve()] + ([Path(output_csv).expanduser().resolve()] if output_csv is not None else [])
            if any(review_path == path or (review_path.exists() and path.exists() and review_path.samefile(path)) for path in protected):
                raise ValueError("Review CSV must differ from the source and complete export.")
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
                _write_csv_atomically(escape_csv_formulas(df) if escape_formulas else df, output_path)
            except OSError as exc:
                print(f"❌ Could not write categorized CSV: {exc}")
                return 1

        if review_path is not None:
            review_path.parent.mkdir(parents=True, exist_ok=True)
            review = df.loc[df["needs_review"]].copy()
            _write_csv_atomically(escape_csv_formulas(review) if escape_formulas else review, review_path)

        if json_output:
            totals = [{**item, "total_amount": format(item["total_amount"], "f")} for item in amount_totals]
            print(json.dumps({"invoice_count": len(df), "category_counts": summarize_categories(df), "amount_totals": totals}, allow_nan=False))
            return 0

        print("\n===== Invoice Categorization Report =====")
        print(df[["description", "category"]].head(max_display_rows).to_string(index=False))
        if len(df) > max_display_rows:
            print(f"Showing {max_display_rows} of {len(df)} invoices; exports and totals include every row.")
        print("\nCategory totals:")
        for category, count in summarize_categories(df).items():
            print(f"  {category}: {count}")
        for total in amount_totals:
            print(f"  {total['category']} [{total['currency']}]: {total['total_amount']:f}")
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
    parser.add_argument("--max-display-rows", type=int, default=20, help="Maximum invoice rows printed; exports remain complete")
    parser.add_argument("--json", action="store_true", help="Print counts and exact decimal total strings as JSON on success")
    parser.add_argument("--escape-formulas", action="store_true", help="Prefix formula-like text with an apostrophe in CSV exports; calculations remain unchanged")
    parser.add_argument("--delimiter", choices=(",", ";", "tab", "|"), default=",", help="Input CSV delimiter; exports remain comma-separated")
    parser.add_argument("--date-column", help="Source calendar-date column for optional inclusive date filters")
    parser.add_argument("--start-date", help="Inclusive starting calendar date")
    parser.add_argument("--end-date", help="Inclusive ending calendar date")
    parser.add_argument("--review-output", help="Atomically export only ambiguous or unmatched invoices for manual review")
    args = parser.parse_args(argv)
    delimiter = "\t" if args.delimiter == "tab" else args.delimiter
    options = {"amount_column": args.amount_column} if args.amount_column else {}
    options["max_display_rows"] = args.max_display_rows
    if args.review_output is not None:
        options["review_csv"] = args.review_output
    for key in ("date_column", "start_date", "end_date"):
        if getattr(args, key) is not None:
            options[key] = getattr(args, key)
    if args.explain:
        options["explain"] = True
    if args.json:
        options["json_output"] = True
    if args.escape_formulas:
        options["escape_formulas"] = True
    if delimiter != ",":
        options["delimiter"] = delimiter
    return process_invoice_file(args.csv_file, output_csv=args.output, **options)


if __name__ == "__main__":
    raise SystemExit(main())
