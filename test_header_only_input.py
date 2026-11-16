from categorize_invoices import process_invoice_file


def test_header_only_input_preserves_previous_report(tmp_path, capsys):
    source = tmp_path / "invoices.csv"
    source.write_text("description,amount\n")
    output = tmp_path / "report.csv"
    output.write_text("previous report")
    assert process_invoice_file(source, output) == 1
    assert output.read_text() == "previous report"
    assert "no invoice rows" in capsys.readouterr().out
