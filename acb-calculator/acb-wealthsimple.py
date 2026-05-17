import csv
import os
from datetime import datetime


def get_csv_files(folder="data"):
    """Get list of CSV files from the data folder."""
    if not os.path.exists(folder):
        return []
    csv_files = [f for f in os.listdir(folder) if f.endswith(".csv")]
    return sorted(csv_files)


def parse_file_selection(selection, csv_files, folder="data"):
    """Parse CSV file selection input into one or more file paths."""
    if not selection:
        return [os.path.join(folder, name) for name in csv_files]

    selected_paths = []
    for part in selection.split(","):
        part = part.strip()
        if not part:
            continue

        if part.isdigit():
            index = int(part) - 1
            if 0 <= index < len(csv_files):
                selected_paths.append(os.path.join(folder, csv_files[index]))
            else:
                raise ValueError(f"Index {part} is outside the available file range.")
        elif "-" in part and part.replace("-", "").isdigit():
            start, end = map(int, part.split("-", 1))
            if start < 1 or end < 1 or start > len(csv_files) or end > len(csv_files):
                raise ValueError(f"Range {part} is outside the available file range.")
            if start > end:
                raise ValueError(
                    f"Range start must be less than or equal to end: {part}"
                )
            for index in range(start - 1, end):
                selected_paths.append(os.path.join(folder, csv_files[index]))
        else:
            candidate = part
            if not os.path.isabs(candidate):
                candidate = os.path.join(folder, candidate)
            selected_paths.append(candidate)

    if not selected_paths:
        raise ValueError("No valid files selected.")
    return selected_paths


def safe_float(value):
    return float(value or 0.0)


def get_year_from_date(date_str):
    if not date_str:
        return "unknown"
    year = date_str.strip().split("-")[0]
    return year if year.isdigit() else "unknown"


def get_years_from_csv_paths(csv_paths):
    years = set()
    for csv_path in csv_paths:
        with open(csv_path, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                date_str = row.get("transaction_date") or row.get("settlement_date")
                if date_str and date_str.strip():
                    year = get_year_from_date(date_str)
                    if year != "unknown":
                        years.add(year)
    if not years:
        return ["unknown"]
    return sorted(years, key=lambda y: int(y) if y.isdigit() else float("inf"))


def get_symbols(csv_paths):
    """Extract unique BUY symbols from one or more CSV files."""
    symbols = set()
    for csv_path in csv_paths:
        with open(csv_path, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if (
                    row.get("activity_type") == "Trade"
                    and row.get("activity_sub_type") == "BUY"
                    and row.get("symbol")
                ):
                    symbols.add(row["symbol"].strip())
    return sorted(symbols)


def calculate_acb(csv_paths, symbol):
    total_acb = 0.0
    total_shares = 0.0
    total_interest = 0.0
    interest_by_year = {}
    capital_gains_by_year = {}

    all_rows = []
    for csv_path in csv_paths:
        with open(csv_path, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                all_rows.append(row)

    all_rows.sort(
        key=lambda r: r.get("transaction_date") or r.get("settlement_date") or ""
    )

    for row in all_rows:
        if (
            row.get("activity_type") == "Trade"
            and row.get("activity_sub_type") == "BUY"
        ):
            if row.get("symbol") == symbol:
                quantity = safe_float(row.get("quantity"))
                net_cash_amount = abs(safe_float(row.get("net_cash_amount")))
                total_acb += net_cash_amount
                total_shares += quantity
        elif (
            row.get("activity_type") == "Trade"
            and row.get("activity_sub_type") == "SELL"
        ):
            if row.get("symbol") == symbol:
                quantity = safe_float(row.get("quantity"))
                proceeds = abs(safe_float(row.get("net_cash_amount")))
                if total_shares > 0:
                    avg_cost_per_share = total_acb / total_shares
                    cost_basis = quantity * avg_cost_per_share
                    capital_gain = proceeds - cost_basis
                    total_acb -= cost_basis
                    total_shares -= quantity
                    year = get_year_from_date(
                        row.get("transaction_date") or row.get("settlement_date")
                    )
                    capital_gains_by_year[year] = (
                        capital_gains_by_year.get(year, 0.0) + capital_gain
                    )
        elif row.get("activity_type") == "InterestCharged":
            interest = safe_float(row.get("net_cash_amount"))
            total_interest += interest
            year = get_year_from_date(
                row.get("transaction_date") or row.get("settlement_date")
            )
            interest_by_year[year] = interest_by_year.get(year, 0.0) + interest

    return (
        total_acb,
        total_shares,
        total_interest,
        interest_by_year,
        capital_gains_by_year,
    )


if __name__ == "__main__":
    csv_files = get_csv_files("data")

    if csv_files:
        print("Available CSV files in data folder:")
        for i, filename in enumerate(csv_files, 1):
            print(f"  {i}. {filename}")
        print(
            "\nPress Enter to use all available files, or select one or more files by comma-separated index or range (for example: 1,3-4)."
        )
        selection = input(f"Select file(s) [default: all]: ").strip()
    else:
        print("No CSV files found in the data folder.")
        selection = input(
            "Enter one or more CSV file paths separated by commas: "
        ).strip()

    try:
        csv_paths = parse_file_selection(selection, csv_files)
    except ValueError as exc:
        print(f"Error: {exc}")
        exit(1)

    print("\nSelected files:")
    for path in csv_paths:
        print(f"  {path}")

    try:
        symbols = get_symbols(csv_paths)
        if not symbols:
            print("No BUY trades found in the selected file(s).")
            exit(1)

        print("\nAvailable symbols:")
        for i, sym in enumerate(symbols, 1):
            print(f"  {i}. {sym}")

        choice = input(f"Select a symbol (1-{len(symbols)}) [default: 1]: ").strip()
        if not choice:
            symbol = symbols[0]
        else:
            try:
                index = int(choice) - 1
                if 0 <= index < len(symbols):
                    symbol = symbols[index]
                else:
                    print(
                        f"Error: Please select a number between 1 and {len(symbols)}."
                    )
                    exit(1)
            except ValueError:
                if choice in symbols:
                    symbol = choice
                else:
                    print(
                        "Error: Invalid input. Enter a symbol index or exact symbol name."
                    )
                    exit(1)

        (
            calculated_acb,
            total_shares,
            total_interest,
            interest_by_year,
            capital_gains_by_year,
        ) = calculate_acb(csv_paths, symbol)

        print(f"\nSymbol: {symbol}")
        print(f"Book cost: {calculated_acb:.2f}")
        print(f"Total shares: {total_shares:.4f}")
        if interest_by_year:
            print("Interest charged by year:")
            for year in sorted(
                interest_by_year,
                key=lambda y: int(y) if y.isdigit() else y,
            ):
                print(f"  {year}: {interest_by_year[year]:.2f}")
        if capital_gains_by_year:
            print("Capital gains/losses by year:")
            for year in sorted(
                capital_gains_by_year,
                key=lambda y: int(y) if y.isdigit() else y,
            ):
                gain = capital_gains_by_year[year]
                label = "gain" if gain >= 0 else "loss"
                print(f"  {year}: {gain:.2f} ({label})")
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        exit(1)

    try:
        years = get_years_from_csv_paths(csv_paths)
        box21_total = 0.0
        box42_total = 0.0

        current_year = datetime.now().year
        past_years = [y for y in years if int(y) < current_year]

        if past_years:
            print("\nEnter T3 box 21 and box 42 amounts for each completed tax year.")
            for year in past_years:
                box21_input = input(
                    f"Enter box 21 amount on T3 for {symbol} in {year} [default: 0]: "
                ).strip()
                box21_year = float(box21_input) if box21_input else 0.0
                box21_total += box21_year

                box42_input = input(
                    f"Enter box 42 amount on T3 for {symbol} in {year} [default: 0]: "
                ).strip()
                box42_year = float(box42_input) if box42_input else 0.0
                box42_total += box42_year
        else:
            print(
                f"\nNo completed tax years to adjust (current year is {current_year})."
            )

        adjusted_acb = calculated_acb + box21_total - box42_total
        acb_per_share = adjusted_acb / total_shares if total_shares > 0 else 0.0

        print(f"\nACB: {adjusted_acb:.2f}")
        print(f"ACB per share: {acb_per_share:.2f}")
    except ValueError:
        print("Invalid numeric input. Please enter numbers for boxes 21 and 42.")
