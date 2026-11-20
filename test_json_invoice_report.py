import json
from categorize_invoices import main
def test_json_preserves_decimal_totals_and_full_count(tmp_path,capsys):
    p=tmp_path/'invoices.csv';p.write_text('description,amount\nrent,9007199254740993.001\nrent,0.002\n')
    assert main([str(p),'--amount-column','amount','--json','--max-display-rows','1'])==0
    data=json.loads(capsys.readouterr().out)
    assert data['invoice_count']==2 and data['category_counts']=={'Rent':2}
    assert data['amount_totals'][0]['total_amount']=='9007199254740993.003'
