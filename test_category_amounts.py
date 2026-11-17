import pandas as pd
import pytest
from categorize_invoices import summarize_category_amounts


def test_category_totals_never_combine_different_currencies():
    frame = pd.DataFrame({"category": ["Rent", "Rent", "Rent"], "amount": [100, -10, 5], "currency": ["INR", "inr", "USD"]})
    totals = summarize_category_amounts(frame)
    assert totals == [
        {"category": "Rent", "currency": "INR", "invoice_count": 2, "total_amount": 90},
        {"category": "Rent", "currency": "USD", "invoice_count": 1, "total_amount": 5},
    ]


def test_invalid_amount_totals_fail_before_report_export():
    with pytest.raises(ValueError, match="finite"):
        summarize_category_amounts(pd.DataFrame({"category": ["Rent"], "amount": [float("inf")]}))


def test_boolean_amounts_are_not_silently_counted_as_money():
    with pytest.raises(ValueError, match="booleans"):
        summarize_category_amounts(pd.DataFrame({"category": ["Rent"], "amount": [True]}))
