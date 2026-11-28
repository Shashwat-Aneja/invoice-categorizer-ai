import zlib
import gzip
import bz2
import lzma
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


def _snapshot_csv_input(csv_file, max_bytes, encoding):
    """Snapshot bounded decompressed CSV bytes without consuming caller streams."""
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or not 1 <= max_bytes <= 64 * 1024 * 1024:
        raise ValueError("max_bytes must be an integer from 1 to 67108864.")
    def read_complete(source):
        chunks = []
        units = 0
        kind = None
        while units <= max_bytes:
            chunk = source.read(min(65536, max_bytes + 1 - units))
            if not isinstance(chunk, (str, bytes)):
                raise ValueError("CSV stream read must return bytes or text.")
            if kind is not None and type(chunk) is not kind:
                raise ValueError("CSV stream read type must be consistent.")
            kind = type(chunk)
            if not chunk:
                break
            chunks.append(chunk)
            units += len(chunk)
        # Encode text once so codecs with BOMs do not insert one per chunk.
        raw = ("".join(chunks).encode(encoding) if kind is str else b"".join(chunks))
        return raw
    if isinstance(csv_file, (str, os.PathLike)):
        path = Path(csv_file)
        if not path.is_file():
            raise ValueError("Bounded CSV input must be a local regular file or seekable stream.")
        opener = {".gz": gzip.open, ".bz2": bz2.open, ".xz": lzma.open}.get(path.suffix.lower(), open)
        try:
            with opener(path, "rb") as source:
                raw = read_complete(source)
        except (EOFError, lzma.LZMAError, zlib.error) as exc:
            raise ValueError("CSV input is corrupt or incomplete.") from exc
    else:
        if not all(hasattr(csv_file, name) for name in ("read", "seek", "tell")) or (hasattr(csv_file, "seekable") and not csv_file.seekable()):
            raise ValueError("Bounded CSV streams must be seekable.")
        position = csv_file.tell()
        try:
            raw = read_complete(csv_file)
        except (EOFError, lzma.LZMAError, zlib.error) as exc:
            raise ValueError("CSV input is corrupt or incomplete.") from exc
        finally:
            csv_file.seek(position)
        if isinstance(raw, str):
            raw = raw.encode(encoding)
        if not isinstance(raw, bytes):
            raise ValueError("CSV stream read must return bytes or text.")
    if len(raw) > max_bytes:
        raise ValueError("CSV input exceeds the configured decompressed byte limit.")
    return io.BytesIO(raw)


def _read_csv_input(csv_file, delimiter=",", max_rows=None, encoding="utf-8", max_bytes=None, **options):
    if encoding not in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        raise ValueError("Unsupported input encoding.")
    if max_rows is not None and (isinstance(max_rows, bool) or not isinstance(max_rows, int) or not 1 <= max_rows <= 10_000_000):
        raise ValueError("max_rows must be an integer from 1 to 10000000.")
    if delimiter not in (",", ";", "\t", "|"):
        raise ValueError("Unsupported input delimiter.")
    if max_rows is not None:
        if "nrows" in options:
            raise ValueError("Do not combine nrows and max_rows.")
        options["nrows"] = max_rows + 1
    if max_bytes is not None:
        csv_file = _snapshot_csv_input(csv_file, max_bytes, encoding)
    _reject_duplicate_headers(csv_file, delimiter, encoding=encoding)
    try:
        frame = pd.read_csv(csv_file, **({"encoding": encoding} if encoding != "utf-8" else {}), **options, **({"sep": delimiter} if delimiter != "," else {}))
    except (EOFError, lzma.LZMAError, zlib.error, csv.Error) as exc:
        raise ValueError("CSV input is corrupt or incomplete, or its header exceeds parser limits.") from exc
    if max_rows is not None and len(frame) > max_rows:
        raise ValueError("CSV input exceeds the configured row limit.")
    return frame


def escape_csv_formulas(frame):
    """Escape formula-like text in a copy; leave numeric cells unchanged."""
    def escape(value):
        if isinstance(value, str) and value.lstrip(" \t\r\n").startswith(("=", "+", "-", "@")):
            return "'" + value
        return value
    return frame.apply(lambda column: column.map(escape))


def _reject_duplicate_headers(csv_file, delimiter=",", encoding="utf-8"):
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
        opener = {".gz": gzip.open, ".bz2": bz2.open, ".xz": lzma.open}.get(Path(csv_file).suffix, open)
        try:
            with opener(csv_file, mode="rt", encoding=encoding, newline="") as source:
                headers = next(csv.reader(header_lines(source), delimiter=delimiter), [])
        except (EOFError, lzma.LZMAError, zlib.error, csv.Error) as exc:
            raise ValueError("CSV input is corrupt or incomplete, or its header exceeds parser limits.") from exc
    else:
        if not all(hasattr(csv_file, name) for name in ("read", "seek", "tell")) or (hasattr(csv_file, "seekable") and not csv_file.seekable()):
            raise ValueError("CSV streams must be seekable for header validation.")
        position = csv_file.tell()
        binary = isinstance(csv_file.read(0), bytes)
        source = io.TextIOWrapper(csv_file, encoding=encoding, newline="") if binary else csv_file
        try:
            headers = next(csv.reader(header_lines(source), delimiter=delimiter), [])
        except (EOFError, lzma.LZMAError, zlib.error, csv.Error) as exc:
            raise ValueError("CSV input is corrupt or incomplete, or its header exceeds parser limits.") from exc
        finally:
            if binary:
                source.detach()
            csv_file.seek(position)
    if len(headers) != len(set(headers)):
        raise ValueError("CSV column names must be unique; duplicate headers are ambiguous.")


def build_category_rules(custom_rules=None, include_defaults=True):
    if not isinstance(include_defaults, bool):
        raise ValueError("include_defaults must be a boolean.")
    if not include_defaults and not custom_rules:
        raise ValueError("Custom-only categorization requires non-empty custom rules.")
    if custom_rules is None:
        return CATEGORY_RULES
    if not isinstance(custom_rules, dict) or len(custom_rules) > 100:
        raise ValueError("Custom rules must be an object with at most 100 categories.")
    compiled = []
    count = 0
    for category, keywords in custom_rules.items():
        if not isinstance(category, str) or not category.strip() or len(category) > 100 or not isinstance(keywords, list) or not keywords:
            raise ValueError("Custom categories need a non-empty name and keyword list.")
        if any(not isinstance(word, str) or not word.strip() or len(word) > 100 for word in keywords):
            raise ValueError("Custom keywords must be non-empty strings of at most 100 characters.")
        count += len(keywords)
        if count > 1000:
            raise ValueError("Custom rules cannot exceed 1000 keywords.")
        pattern = r"(?<!\w)(?:" + "|".join(re.escape(word.strip()) for word in keywords) + r")(?!\w)"
        compiled.append((category.strip(), re.compile(pattern, re.IGNORECASE)))
    return tuple(compiled) + (CATEGORY_RULES if include_defaults else ())


def load_custom_rules(path):
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Custom rule JSON contains a duplicate category.")
            result[key] = value
        return result
    with Path(path).expanduser().open(encoding="utf-8") as source:
        rules = json.load(source, object_pairs_hook=unique_object)
    build_category_rules(rules)
    return rules


def categorize(description, rules=None):
    """Map an invoice description to a stable business expense category."""
    if pd.isna(description):
        return "Miscellaneous"
    desc = str(description).strip()
    if not desc:
        return "Miscellaneous"

    for category, pattern in (CATEGORY_RULES if rules is None else rules):
        if pattern.search(desc):
            return category
    return "Miscellaneous"


def explain_category(description, rules=None):
    """Expose all matching categories so ambiguous rules can be reviewed."""
    text = "" if pd.isna(description) else str(description).strip()
    matches = list(dict.fromkeys(category for category, pattern in (CATEGORY_RULES if rules is None else rules) if pattern.search(text)))
    return {"category": matches[0] if matches else "Miscellaneous",
            "matching_categories": matches,
            "needs_review": len(matches) != 1,
            "review_reason": "unmatched" if not matches else ("multiple_categories" if len(matches) > 1 else "none")}


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


def process_invoice_file(csv_file, output_csv=None, amount_column=None, explain=False, max_display_rows=20, json_output=False, escape_formulas=False, delimiter=",", date_column=None, start_date=None, end_date=None, review_csv=None, custom_rules=None, id_column=None, custom_rules_only=False, max_rows=None, categories=None, encoding="utf-8", max_bytes=None):
    try:
        if not isinstance(custom_rules_only, bool):
            raise ValueError("custom_rules_only must be a boolean.")
        if categories is not None and (not isinstance(categories, (list, tuple)) or not categories or any(not isinstance(c, str) or not c.strip() for c in categories)):
            raise ValueError("categories must be a non-empty list of category names.")
        rules = build_category_rules(custom_rules, include_defaults=not custom_rules_only)
        if not isinstance(max_display_rows, int) or isinstance(max_display_rows, bool) or max_display_rows < 1:
            raise ValueError("max_display_rows must be a positive integer.")
        if id_column is not None and (not isinstance(id_column, str) or not id_column.strip() or id_column in {amount_column, "category", "matching_categories", "needs_review", "review_reason"}):
            raise ValueError("Invoice ID column must be a distinct source identifier column.")
        dtypes = {amount_column: "string"} if amount_column else {}
        converters = {id_column: lambda value: "__id__" + value} if id_column is not None else None
        df = _read_csv_input(csv_file, delimiter, **({"max_bytes": max_bytes} if max_bytes is not None else {}), **({"encoding": encoding} if encoding != "utf-8" else {}), **({"max_rows": max_rows} if max_rows is not None else {}), dtype=dtypes or None, converters=converters)
        if id_column is not None and id_column in df.columns:
            # Some pandas versions recognize NA after applying converters.
            # A temporary prefix protects literal IDs; it never leaves parsing.
            df[id_column] = df[id_column].astype("string").str.slice(6)
        if "description" not in df.columns:
            print("❌ CSV must contain a 'description' column.")
            return 1

        if df.empty:
            print("❌ CSV contains no invoice rows.")
            return 1
        df = filter_invoice_dates(df, date_column, start_date, end_date)
        if id_column is not None:
            if id_column not in df.columns:
                raise ValueError("Invoice ID column was not found.")
            identifiers = df[id_column].str.strip()
            if identifiers.isna().any() or identifiers.eq("").any() or identifiers.duplicated().any():
                raise ValueError("Selected invoice IDs must be non-empty and unique.")
        if amount_column in {"category", "matching_categories", "needs_review", "review_reason"}:
            raise ValueError("Amount column cannot use a generated categorization column name.")
        df = df.copy()
        df["category"] = df["description"].apply(lambda description: categorize(description, rules))
        if explain or review_csv is not None:
            if "review_reason" in df.columns:
                raise ValueError("review_reason is reserved for generated diagnostics.")
            explanations = df["description"].apply(lambda description: explain_category(description, rules))
            df["matching_categories"] = explanations.map(lambda item: "; ".join(item["matching_categories"]))
            df["needs_review"] = explanations.map(lambda item: item["needs_review"])
            df["review_reason"] = explanations.map(lambda item: item["review_reason"])
        categorized_count = len(df)
        if categories is not None:
            known = {name.casefold(): name for name, _ in rules}
            known["miscellaneous"] = "Miscellaneous"
            requested = {c.strip().casefold() for c in categories}
            if not requested.issubset(known):
                raise ValueError("Unknown category filter.")
            df = df.loc[df["category"].str.casefold().isin(requested)].copy()
            if df.empty:
                raise ValueError("No invoices match the selected categories.")
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
            print(json.dumps({**({"categorized_invoice_count": categorized_count} if categories is not None else {}), "invoice_count": len(df), "category_counts": summarize_categories(df), "amount_totals": totals}, allow_nan=False))
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
    parser.add_argument("--rules-json", help="JSON object mapping custom category names to literal keyword lists; custom rules precede built-ins")
    parser.add_argument("--id-column", help="Validate unique non-empty identifiers in selected invoices and preserve leading zeros")
    parser.add_argument("--custom-rules-only", action="store_true", help="Use only the categories from --rules-json, with unmatched descriptions Miscellaneous")
    parser.add_argument("--max-input-rows", type=int, help="Reject CSV files exceeding this raw row budget (1..10000000)")
    parser.add_argument("--category", action="append", help="Select an assigned category; repeat for several")
    parser.add_argument("--encoding", choices=("utf-8", "utf-8-sig", "cp1252", "latin-1"), default="utf-8", help="Input CSV text encoding; output encoding remains UTF-8")
    parser.add_argument("--max-input-bytes", type=int, help="Snapshot and bound each decompressed CSV input (1..67108864 bytes)")
    args = parser.parse_args(argv)
    if args.max_input_bytes is not None and not 1 <= args.max_input_bytes <= 64 * 1024 * 1024:
        parser.error("--max-input-bytes must be from 1 to 67108864")
    if args.max_input_rows is not None and not 1 <= args.max_input_rows <= 10_000_000:
        parser.error("--max-input-rows must be from 1 to 10000000")
    if args.custom_rules_only and not args.rules_json:
        parser.error("--custom-rules-only requires --rules-json")
    delimiter = "\t" if args.delimiter == "tab" else args.delimiter
    options = {"amount_column": args.amount_column} if args.amount_column else {}
    options["max_display_rows"] = args.max_display_rows
    if args.custom_rules_only:
        options["custom_rules_only"] = True
    if args.id_column is not None:
        options["id_column"] = args.id_column
    if args.rules_json:
        try:
            options["custom_rules"] = load_custom_rules(args.rules_json)
        except (OSError, ValueError) as exc:
            parser.error(f"Invalid custom rule file: {exc}")
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
    if args.category is not None:
        options["categories"] = args.category
    if args.encoding != "utf-8":
        options["encoding"] = args.encoding
    if args.max_input_bytes is not None:
        options["max_bytes"] = args.max_input_bytes
    if args.max_input_rows is not None:
        options["max_rows"] = args.max_input_rows
    if delimiter != ",":
        options["delimiter"] = delimiter
    return process_invoice_file(args.csv_file, output_csv=args.output, **options)


if __name__ == "__main__":
    raise SystemExit(main())
