Invoice category rules

The categorizer checks Rent, Utilities, Equipment, Vendor Payment, then Miscellaneous. The first matching rule wins, so descriptions with multiple keywords follow this precedence. Matching is case-insensitive and uses word boundaries. Missing or blank descriptions map to Miscellaneous.

Run `python categorize_invoices.py sample_invoices.csv`. The CSV must include `description`. This keyword-based output is only a suggestion; review ambiguous and uncategorized records against the organization's chart of accounts before posting.