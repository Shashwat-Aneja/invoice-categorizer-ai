from decimal import Decimal
import pandas as pd
from categorize_invoices import summarize_category_amounts, process_invoice_file


def test_decimal_totals_preserve_fractions_and_large_integer_amounts():
    frame = pd.DataFrame({"category": ["Rent"] * 3, "amount": ["9007199254740993", "0.1", "0.2"]})
    assert summarize_category_amounts(frame)[0]["total_amount"] == Decimal("9007199254740993.3")


def test_csv_amounts_are_read_without_float_precision_loss(tmp_path, capsys):
    source = tmp_path / "invoices.csv"
    source.write_text("description,amount\nrent,9007199254740993.01\n")
    assert process_invoice_file(source, amount_column="amount") == 0
    assert "9007199254740993.01" in capsys.readouterr().out


def test_mixed_exponents_preserve_tiny_fraction_next_to_large_amount():
    frame = pd.DataFrame({"category": ["Rent", "Rent"], "amount": ["1e20", "1e-10"]})
    assert summarize_category_amounts(frame)[0]["total_amount"] == Decimal("100000000000000000000.0000000001")
