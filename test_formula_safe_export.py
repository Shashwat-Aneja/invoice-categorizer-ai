import pandas as pd
from categorize_invoices import process_invoice_file
def test_opt_in_export_escapes_formula_text_without_changing_source(tmp_path):
    source=tmp_path/'in.csv';pd.DataFrame({'description':['=2+2','plain'],'amount':[1,2]}).to_csv(source,index=False)
    out=tmp_path/'out.csv'
    assert process_invoice_file(source,out,escape_formulas=True)==0
    assert pd.read_csv(out)['description'].tolist()==["'=2+2",'plain']
    assert pd.read_csv(source)['description'].iloc[0]=='=2+2'
