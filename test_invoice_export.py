import pandas as pd

from categorize_invoices import process_invoice_file


def test_process_invoice_file_exports_categories_without_losing_source_columns(tmp_path):
    source = tmp_path / "invoices.csv"
    output = tmp_path / "exports" / "categorized.csv"
    source.write_text(
        "description,amount\nOffice rent,1200\nElectricity bill,300\nTeam lunch,150\n",
        encoding="utf-8",
    )

    assert process_invoice_file(str(source), output_csv=str(output)) == 0

    exported = pd.read_csv(output)
    assert exported["category"].tolist() == ["Rent", "Utilities", "Miscellaneous"]
    assert exported["amount"].tolist() == [1200, 300, 150]
    assert list(pd.read_csv(source).columns) == ["description", "amount"]


def test_export_refuses_to_overwrite_the_input_file(tmp_path, capsys):
    source = tmp_path / "invoices.csv"
    original = "description,amount\nOffice rent,1200\n"
    source.write_text(original, encoding="utf-8")

    assert process_invoice_file(str(source), output_csv=str(source)) == 1

    assert source.read_text(encoding="utf-8") == original
    assert "different from the source file" in capsys.readouterr().out
