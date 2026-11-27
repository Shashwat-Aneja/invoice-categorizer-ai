from categorize_invoices import explain_category, process_invoice_file

def test_review_reasons():
    assert explain_category("unmatched xyz")["review_reason"]=="unmatched"
    assert explain_category("rent and laptop")["review_reason"]=="multiple_categories"
    assert explain_category("rent")["review_reason"]=="none"

def test_diagnostics_do_not_overwrite_source(tmp_path):
    src=tmp_path/"a.csv";out=tmp_path/"out.csv"
    src.write_text("description,review_reason\nrent,original\n")
    assert process_invoice_file(src,output_csv=out,explain=True)==1
    assert not out.exists()
