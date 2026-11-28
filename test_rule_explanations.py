import pandas as pd
from categorize_invoices import explain_category, main


def test_ambiguous_and_unmatched_descriptions_are_flagged():
    result = explain_category("rent and software subscription")
    assert result == {"category": "Rent", "matching_categories": ["Rent", "Software"], "needs_review": True, "review_reason": "multiple_categories"}
    assert explain_category("monthly salary")["needs_review"] is False
    assert explain_category(None)["needs_review"] is True


def test_explanation_columns_are_exported_only_when_requested(tmp_path):
    source = tmp_path / "invoices.csv"
    output = tmp_path / "categorized.csv"
    source.write_text("description\nrent and software subscription\n")
    assert main([str(source), "--explain", "--output", str(output)]) == 0
    result = pd.read_csv(output)
    assert result.loc[0, "matching_categories"] == "Rent; Software"
    assert bool(result.loc[0, "needs_review"])
