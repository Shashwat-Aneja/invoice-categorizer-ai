from decimal import Decimal,localcontext,Overflow,Underflow
import pandas as pd
from categorize_invoices import summarize_category_amounts
def test_invoice_totals_ignore_caller_exponent_limits_and_preserve_context():
    with localcontext() as context:
        context.Emax=9;context.Emin=-9;context.prec=2
        context.traps[Overflow]=True;context.traps[Underflow]=True
        result=summarize_category_amounts(pd.DataFrame({'category':['Rent','Rent'],'amount':['1e20','0.00000000000000000001']}))
        assert str(result[0]['total_amount'])=='100000000000000000000.00000000000000000001'
        assert context.Emax==9 and context.Emin==-9 and context.prec==2
