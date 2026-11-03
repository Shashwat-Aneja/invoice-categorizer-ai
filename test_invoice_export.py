import pandas as pd

from categorize_invoices import categorize, process_invoice_file


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


def test_categorize_recognizes_common_operating_expense_types():
    cases = {
        "Airport taxi and hotel": "Travel",
        "Digital advertising campaign": "Marketing",
        "Cloud hosting subscription": "Software",
        "Business insurance premium": "Insurance",
        "Monthly employee salary": "Payroll",
        "Supplier invoice": "Vendor Payment",
        "Broadband internet bill": "Utilities",
    }

    for description, expected in cases.items():
        assert categorize(description) == expected

def test_export_refuses_to_overwrite_a_hard_link_to_the_source(tmp_path, capsys):
    import os

    import pytest

    source = tmp_path / "invoices.csv"
    linked_output = tmp_path / "linked-export.csv"
    original = "description,amount\nOffice rent,1200\n"
    source.write_text(original, encoding="utf-8")
    try:
        os.link(source, linked_output)
    except (OSError, NotImplementedError):
        pytest.skip("Hard links are not supported in this environment.")

    assert process_invoice_file(str(source), output_csv=str(linked_output)) == 1

    assert source.read_text(encoding="utf-8") == original
    assert linked_output.read_text(encoding="utf-8") == original
    assert "different from the source file" in capsys.readouterr().out



def test_failed_export_preserves_existing_destination_and_cleans_temporary_file(tmp_path, monkeypatch, capsys):
    source = tmp_path / "invoices.csv"
    output = tmp_path / "categorized.csv"
    source.write_text("description,amount\nOffice rent,1200\n", encoding="utf-8")
    output.write_text("previous report\n", encoding="utf-8")

    def fail_after_partial_write(_frame, path_or_buf=None, **_kwargs):
        path_or_buf.write("partial csv data")
        raise OSError("simulated disk write failure")

    monkeypatch.setattr(pd.DataFrame, "to_csv", fail_after_partial_write)

    assert process_invoice_file(str(source), output_csv=str(output)) == 1

    assert output.read_text(encoding="utf-8") == "previous report\n"
    assert list(tmp_path.glob(f".{output.name}.*.tmp")) == []
    assert "simulated disk write failure" in capsys.readouterr().out
