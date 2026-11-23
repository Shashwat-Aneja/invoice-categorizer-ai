import pandas as pd
from categorize_invoices import process_invoice_file
def test_identifier_validation_preserves_leading_zeros(tmp_path):
    source=tmp_path/'in.csv';source.write_text('invoice_id,description\n001,rent\n002,software\n');out=tmp_path/'out.csv'
    assert process_invoice_file(source,out,id_column='invoice_id')==0
    assert pd.read_csv(out,dtype={'invoice_id':str})['invoice_id'].tolist()==['001','002']
def test_duplicate_selected_ids_stop_before_export(tmp_path):
    source=tmp_path/'in.csv';source.write_text('id,description\nA,rent\nA,software\n');out=tmp_path/'out.csv';out.write_text('keep')
    assert process_invoice_file(source,out,id_column='id')==1
    assert out.read_text()=='keep'

def test_literal_na_identifiers_survive_csv_parsing(tmp_path):
    source=tmp_path/'in.csv';source.write_text('id,description\nNA,rent\nNULL,software\nN/A,coffee\n');out=tmp_path/'out.csv'
    assert process_invoice_file(source,out,id_column='id')==0
    assert pd.read_csv(out,keep_default_na=False)['id'].tolist()==['NA','NULL','N/A']

def test_whitespace_id_still_rejected(tmp_path):
    source=tmp_path/'in.csv';source.write_text('id,description\n" ",rent\n')
    assert process_invoice_file(source,id_column='id')==1
