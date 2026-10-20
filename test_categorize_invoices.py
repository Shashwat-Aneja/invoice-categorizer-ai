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


if __name__ == "__main__":
    unittest.main()
