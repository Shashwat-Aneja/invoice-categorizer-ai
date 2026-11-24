import pytest
from categorize_invoices import build_category_rules,categorize,main

def test_custom_only_does_not_fall_back_to_builtin_taxonomy():
    rules=build_category_rules({'Meals':['coffee']},include_defaults=False)
    assert categorize('coffee',rules)=='Meals'
    assert categorize('rent',rules)=='Miscellaneous'
    assert categorize('rent',build_category_rules({'Meals':['coffee']}))=='Rent'

def test_custom_only_requires_nonempty_rules():
    with pytest.raises(ValueError):build_category_rules({},include_defaults=False)
    with pytest.raises(SystemExit):main(['absent.csv','--custom-rules-only'])

def test_custom_only_cli_exports_only_requested_categories(tmp_path):
    import json,pandas as pd
    source=tmp_path/'in.csv';source.write_text('description\nrent\ncoffee\n')
    rules=tmp_path/'rules.json';rules.write_text(json.dumps({'Meals':['coffee']}));out=tmp_path/'out.csv'
    assert main([str(source),'--rules-json',str(rules),'--custom-rules-only','--output',str(out)])==0
    assert pd.read_csv(out)['category'].tolist()==['Miscellaneous','Meals']
