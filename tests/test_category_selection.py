import json
import pandas as pd
from categorize_invoices import process_invoice_file

def test_category_selection_and_empty_output_preservation(tmp_path,capsys):
    src=tmp_path/"a.csv";out=tmp_path/"o.csv"
    src.write_text("description\nrent\nlaptop\n")
    assert process_invoice_file(src,output_csv=out,categories=["rEnT"],json_output=True)==0
    report=json.loads(capsys.readouterr().out)
    assert report["invoice_count"]==1 and report["categorized_invoice_count"]==2
    assert pd.read_csv(out).category.tolist()==["Rent"]
    previous=out.read_bytes()
    assert process_invoice_file(src,output_csv=out,categories=["Insurance"])==1
    assert out.read_bytes()==previous
