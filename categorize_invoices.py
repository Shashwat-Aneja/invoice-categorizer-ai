import pandas as pd
import sys

def categorize(description):
    desc = description.lower()

    if any(word in desc for word in ["rent", "lease"]):
        return "Rent"
    if any(word in desc for word in ["electricity", "water", "utility", "bill"]):
        return "Utilities"
    if any(word in desc for word in ["sensor", "laptop", "hardware", "equipment"]):
        return "Equipment"
    if "invoice" in desc or "vendor" in desc:
        return "Vendor Payment"

    return "Miscellaneous"

def process_invoice_file(csv_file):
    try:
        df = pd.read_csv(csv_file)
        if "description" not in df.columns:
            print("❌ CSV must contain a 'description' column.")
            return

        df["category"] = df["description"].apply(categorize)
        print("\n===== Invoice Categorization Report =====")
        print(df[["description", "category"]])
        print("=========================================\n")

    except Exception as e:
        print(f"❌ Error reading file: {e}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python categorize_invoices.py <csv_file>")
        return

    process_invoice_file(sys.argv[1])

if __name__ == "__main__":
    main()
