from categorize_invoices import _reject_duplicate_headers
import pytest
def test_duplicate_headers_are_rejected_instead_of_renamed(tmp_path):
    p=tmp_path/'data.csv';p.write_text('value,value\n1,2\n')
    with pytest.raises(ValueError,match='unique'):_reject_duplicate_headers(p)
def test_bom_header_and_distinct_names_are_supported(tmp_path):
    p=tmp_path/'data.csv';p.write_text('\ufeffvalue,other\n1,2\n',encoding='utf-8')
    _reject_duplicate_headers(p)

def test_duplicate_amounts_cannot_silently_select_first_column(tmp_path):
    from categorize_invoices import process_invoice_file
    p=tmp_path/'data.csv';p.write_text('description,amount,amount\nrent,1,999\n')
    assert process_invoice_file(p,amount_column='amount')==1
