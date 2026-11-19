from categorize_invoices import process_invoice_file
def test_console_does_not_round_away_small_amounts(tmp_path,capsys):
    source=tmp_path/'invoice.csv';source.write_text('description,amount\nrent,0.001\nrent,0.002\n')
    assert process_invoice_file(source,amount_column='amount')==0
    assert '0.003' in capsys.readouterr().out
