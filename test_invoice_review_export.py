import pandas as pd
from categorize_invoices import process_invoice_file
def test_review_export_selects_ambiguous_and_unmatched_rows(tmp_path):
    source=tmp_path/'in.csv';pd.DataFrame({'description':['rent','rent software','unclassified item']}).to_csv(source,index=False)
    full=tmp_path/'full.csv';review=tmp_path/'review.csv'
    assert process_invoice_file(source,full,review_csv=review)==0
    assert len(pd.read_csv(full))==3
    selected=pd.read_csv(review)
    assert selected['description'].tolist()==['rent software','unclassified item']
    assert selected['needs_review'].all() and 'matching_categories' in selected
def test_review_path_cannot_replace_input_or_full_export(tmp_path):
    source=tmp_path/'in.csv';source.write_text('description\nrent\n')
    assert process_invoice_file(source,review_csv=source)==1
    assert source.read_text()=='description\nrent\n'
    full=tmp_path/'full.csv'
    assert process_invoice_file(source,full,review_csv=full)==1
    assert not full.exists()
