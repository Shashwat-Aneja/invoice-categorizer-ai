import pandas as pd
import pytest
from categorize_invoices import summarize_category_amounts
@pytest.mark.parametrize("df", [pd.DataFrame({'amount':[1]}), pd.DataFrame({'category':[None], 'amount':[1]}), pd.DataFrame({'category':[' '], 'amount':[1]}), pd.DataFrame([[1,2,'Rent']],columns=['amount','amount','category'])])
def test_invalid_categories_fail_explicitly(df):
    with pytest.raises(ValueError): summarize_category_amounts(df)
