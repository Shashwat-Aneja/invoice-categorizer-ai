import pandas as pd
from categorize_invoices import process_invoice_file


def test_bounded_invoice_preview_retains_complete_exports(tmp_path, capsys):
    source = tmp_path / "invoices.csv"
    output = tmp_path / "result.csv"
    pd.DataFrame({"description": [f"rent {i}" for i in range(30)]}).to_csv(source, index=False)
    assert process_invoice_file(source, output, max_display_rows=3) == 0
    text = capsys.readouterr().out
    assert "Showing 3 of 30" in text
    assert "rent 29" not in text
    assert len(pd.read_csv(output)) == 30
