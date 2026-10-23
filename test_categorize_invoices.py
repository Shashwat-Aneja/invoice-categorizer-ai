import unittest

import pandas as pd

from categorize_invoices import categorize


class InvoiceCategorizationTests(unittest.TestCase):
    def test_known_categories_are_case_insensitive(self):
        self.assertEqual(categorize("OFFICE RENT for October"), "Rent")
        self.assertEqual(categorize("Electricity bill"), "Utilities")
        self.assertEqual(categorize("New laptop"), "Equipment")
        self.assertEqual(categorize("Vendor invoice 42"), "Vendor Payment")

    def test_missing_and_blank_descriptions_are_miscellaneous(self):
        self.assertEqual(categorize(None), "Miscellaneous")
        self.assertEqual(categorize(float("nan")), "Miscellaneous")
        self.assertEqual(categorize("   "), "Miscellaneous")

    def test_substring_inside_unrelated_word_does_not_match(self):
        self.assertEqual(categorize("rebilling workflow"), "Miscellaneous")

    def test_unknown_description_is_miscellaneous(self):
        self.assertEqual(categorize("team lunch"), "Miscellaneous")


    def test_category_summary_counts_each_category(self):
        from categorize_invoices import summarize_categories

        frame = pd.DataFrame({"category": ["Rent", "Utilities", "Rent", "Miscellaneous"]})
        self.assertEqual(
            summarize_categories(frame),
            {"Rent": 2, "Utilities": 1, "Miscellaneous": 1},
        )

    def test_invoice_report_prints_category_totals(self):
        import tempfile
        from pathlib import Path
        from contextlib import redirect_stdout
        from io import StringIO
        from categorize_invoices import process_invoice_file

        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        handle.write("description\nOffice rent\nElectricity bill\nOffice rent\n")
        handle.close()
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(process_invoice_file(handle.name), 0)
        self.assertIn("Rent: 2", output.getvalue())
        self.assertIn("Utilities: 1", output.getvalue())

    def test_category_summary_requires_category_column(self):
        from categorize_invoices import summarize_categories

        with self.assertRaisesRegex(ValueError, "category"):
            summarize_categories(pd.DataFrame({"description": ["Office rent"]}))

if __name__ == "__main__":
    unittest.main()
