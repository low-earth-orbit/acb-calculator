import csv
import os


def get_csv_files(folder="data"):
    """Get list of CSV files from the data folder."""
    if not os.path.exists(folder):
        return []
    csv_files = [f for f in os.listdir(folder) if f.endswith(".csv")]
    return sorted(csv_files)


def get_symbols(csv_file):
    """Extract unique symbols from BUY trades in the CSV file."""
    symbols = set()
    with open(csv_file, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if (
                row["activity_type"] == "Trade"
                and row["activity_sub_type"] == "BUY"
                and row["symbol"]
            ):
                symbols.add(row["symbol"])
    return sorted(list(symbols))


def calculate_acb(csv_file, symbol):
    total_acb = 0.0
    total_shares = 0.0
    total_interest = 0.0
    with open(csv_file, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if (
                row["activity_type"] == "Trade"
                and row["activity_sub_type"] == "BUY"
                and row["symbol"] == symbol
            ):
                quantity = float(row["quantity"])
                unit_price = float(row["unit_price"])
                commission = float(row["commission"])
                cost = quantity * unit_price + commission
                total_acb += cost
                total_shares += quantity
            elif row["activity_type"] == "InterestCharged":
                total_interest += float(row["net_cash_amount"])
    return total_acb, total_shares, total_interest


if __name__ == "__main__":
    csv_files = get_csv_files("data")

    if csv_files:
        print("Available CSV files in data folder:")
        for i, f in enumerate(csv_files, 1):
            print(f"  {i}. {f}")

        choice = input(
            f"Select a file (1-{len(csv_files)}) or enter a custom path [default: 1]: "
        ).strip()
        if not choice:
            choice = "1"
        try:
            index = int(choice) - 1
            if 0 <= index < len(csv_files):
                csv_file = os.path.join("data", csv_files[index])
            else:
                print(f"Error: Please select a number between 1 and {len(csv_files)}.")
                exit(1)
        except ValueError:
            csv_file = choice
    else:
        csv_file = input(
            "No CSV files found in data folder. Enter the path to the data file: "
        ).strip()

    try:
        symbols = get_symbols(csv_file)
        if not symbols:
            print("No BUY trades found in the file.")
            exit(1)

        print("\nAvailable symbols:")
        for i, sym in enumerate(symbols, 1):
            print(f"  {i}. {sym}")

        choice = input(f"Select a symbol (1-{len(symbols)}) [default: 1]: ").strip()
        if not choice:
            choice = "1"
        try:
            index = int(choice) - 1
            if 0 <= index < len(symbols):
                symbol = symbols[index]
            else:
                print(f"Error: Please select a number between 1 and {len(symbols)}.")
                exit(1)
        except ValueError:
            print("Error: Invalid input.")
            exit(1)

        calculated_acb, total_shares, total_interest = calculate_acb(csv_file, symbol)
        print(f"\nSymbol: {symbol}")
        print(f"ACB calculated from trades: {calculated_acb:.2f}")
        print(f"Total shares: {total_shares:.4f}")
        print(f"Total interest charged (entire account): {total_interest:.2f}")
    except FileNotFoundError:
        print(f"Error: File '{csv_file}' not found.")
        exit(1)

    try:
        box21_input = input(
            f"Enter box 21 amount on T3 for {symbol} [default: 0]: "
        ).strip()
        box21 = float(box21_input) if box21_input else 0.0
        box42_input = input(
            f"Enter box 42 amount on T3 for {symbol} [default: 0]: "
        ).strip()
        box42 = float(box42_input) if box42_input else 0.0
        adjusted_acb = calculated_acb + box21 - box42
        acb_per_share = adjusted_acb / total_shares if total_shares > 0 else 0
        print(f"ACB: {adjusted_acb:.2f}")
        print(f"ACB per share: {acb_per_share:.2f}")
    except ValueError:
        print("Invalid input. Please enter numeric values.")
