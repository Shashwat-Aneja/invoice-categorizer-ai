import json,pandas as pd,pytest
from categorize_invoices import main,filter_invoice_dates
def test_inclusive_local_calendar_filter_controls_json_and_export(tmp_path,capsys):
    source=tmp_path/'in.csv';pd.DataFrame({'description':['rent','software'],'date':['2026-01-01T23:30:00-05:00','2026-01-02T00:00:00+05:30'],'amount':[10,20]}).to_csv(source,index=False)
    out=tmp_path/'out.csv'
    assert main([str(source),'--date-column','date','--start-date','2026-01-01','--end-date','2026-01-01','--amount-column','amount','--output',str(out),'--json'])==0
    result=json.loads(capsys.readouterr().out)
    assert result['invoice_count']==1 and result['amount_totals'][0]['total_amount']=='10'
    assert len(pd.read_csv(out))==1 and len(pd.read_csv(source))==2
def test_date_filters_require_a_named_column():
    with pytest.raises(ValueError,match='date_column'):filter_invoice_dates(pd.DataFrame({'x':[1]}),start_date='2026-01-01')
