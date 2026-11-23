import pytest,pandas as pd
from categorize_invoices import build_category_rules,categorize,explain_category,process_invoice_file,load_custom_rules
def test_custom_keywords_are_literal_and_precede_builtin_fallbacks():
    rules=build_category_rules({'Development':['C++'],'Office':['rent']})
    assert categorize('C++ course',rules)=='Development'
    assert categorize('rent monthly',rules)=='Office'
    assert categorize('internet service',rules)=='Utilities'
    assert explain_category('rent monthly',rules)['matching_categories']==['Office','Rent']
def test_duplicate_category_matches_do_not_create_false_ambiguity():
    rules=build_category_rules({'Rent':['rent']})
    assert explain_category('rent',rules)['needs_review'] is False
def test_bad_custom_rules_preserve_previous_export(tmp_path):
    source=tmp_path/'in.csv';source.write_text('description\nrent\n');out=tmp_path/'out.csv';out.write_text('keep')
    assert process_invoice_file(source,out,custom_rules={'Empty':[]})==1
    assert out.read_text()=='keep'
def test_duplicate_json_categories_are_rejected(tmp_path):
    p=tmp_path/'rules.json';p.write_text('{"X":["one"],"X":["two"]}')
    with pytest.raises(ValueError,match='duplicate'):load_custom_rules(p)
