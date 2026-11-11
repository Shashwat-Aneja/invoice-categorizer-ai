from pathlib import Path

from categorize_invoices import process_invoice_file


def test_export_directory_creation_failure_returns_error(tmp_path, capsys):
    source = tmp_path / "invoices.csv"
    source.write_text("description\nOffice rent\n", encoding="utf-8")
    blocking_file = tmp_path / "not-a-directory"
    blocking_file.write_text("existing content", encoding="utf-8")
    output = blocking_file / "export.csv"

    assert process_invoice_file(str(source), output_csv=str(output)) == 1
    assert blocking_file.read_text(encoding="utf-8") == "existing content"
    assert "Could not write categorized CSV" in capsys.readouterr().out
