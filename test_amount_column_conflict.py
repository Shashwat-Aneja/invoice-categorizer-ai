from categorize_invoices import process_invoice_file
def test_generated_amount_column_cannot_silently_change_values(tmp_path):
    source=tmp_path/'invoice.csv'; source.write_text('description,needs_review\nrent,123\n')
    output=tmp_path/'out.csv'; output.write_text('keep')
    assert process_invoice_file(source,output,amount_column='needs_review',explain=True)==1
    assert output.read_text()=='keep'
