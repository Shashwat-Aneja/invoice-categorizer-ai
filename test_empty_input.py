from categorize_invoices import process_invoice_file


def test_empty_csv_returns_failure_without_touching_export(tmp_path, capsys):
    source = tmp_path / "empty.csv"
    source.write_text("")
    output = tmp_path / "report.csv"
    output.write_text("previous report")
    assert process_invoice_file(source, output) == 1
    assert output.read_text() == "previous report"
    assert "Error reading file" in capsys.readouterr().out
