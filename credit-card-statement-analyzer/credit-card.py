#!/usr/bin/env python3
"""Analyze credit card statement CSV files by editable spending categories."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = BASE_DIR / "data"
DEFAULT_RULES_FILE = BASE_DIR / "category_rules.json"

DESCRIPTION_COLUMNS = ("details", "description", "merchant", "name", "payee")
AMOUNT_COLUMNS = ("amount", "transaction_amount", "debit", "purchase", "value")
DATE_COLUMNS = ("transaction_date", "date", "post_date", "posted_date")
TYPE_COLUMNS = ("type", "transaction_type")
CURRENCY_COLUMNS = ("currency", "currency_code")


@dataclass(frozen=True)
class Transaction:
    source_file: str
    date: str
    description: str
    amount: Decimal
    currency: str
    transaction_type: str
    category: str


def normalize_header(header: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", header.strip().lower()).strip("_")


def pick_column(row: dict[str, str], candidates: Iterable[str], fallback: str = "") -> str:
    for candidate in candidates:
        if candidate in row and row[candidate] != "":
            return row[candidate].strip()
    return fallback


def parse_amount(value: str) -> Decimal:
    cleaned = value.strip().replace("$", "").replace(",", "")
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = f"-{cleaned[1:-1]}"
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"Could not parse amount: {value!r}") from exc


def load_rules(path: Path) -> dict[str, list[str]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Category rules file not found: {path}. "
            "Create it or run from the project folder with category_rules.json present."
        )

    with path.open(encoding="utf-8") as file:
        raw_rules = json.load(file)

    if not isinstance(raw_rules, dict):
        raise ValueError("Category rules must be a JSON object of category names to keyword lists.")

    rules: dict[str, list[str]] = {}
    for category, keywords in raw_rules.items():
        if not isinstance(category, str) or not isinstance(keywords, list):
            raise ValueError("Each category rule must look like: \"Category\": [\"keyword\", ...].")
        rules[category] = [str(keyword).lower() for keyword in keywords if str(keyword).strip()]
    return rules


def categorize(description: str, rules: dict[str, list[str]]) -> str:
    normalized = description.lower()
    for category, keywords in rules.items():
        for keyword in keywords:
            pattern = re.escape(keyword.strip())
            if not pattern:
                continue
            if keyword.strip()[0].isalnum():
                pattern = rf"(?<![a-z0-9]){pattern}"
            if keyword.strip()[-1].isalnum():
                pattern = rf"{pattern}(?![a-z0-9])"
            if re.search(pattern, normalized):
                return category
    return "Uncategorized"


def iter_csv_files(data_dir: Path) -> list[Path]:
    return sorted(path for path in data_dir.glob("*.csv") if path.is_file())


def read_transactions(data_dir: Path, rules: dict[str, list[str]]) -> list[Transaction]:
    if not data_dir.exists():
        raise FileNotFoundError(f"Data folder not found: {data_dir}")

    csv_files = iter_csv_files(data_dir)
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found under: {data_dir}")

    transactions: list[Transaction] = []
    for csv_path in csv_files:
        with csv_path.open(newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            if reader.fieldnames is None:
                continue

            reader.fieldnames = [normalize_header(field) for field in reader.fieldnames]
            for row in reader:
                normalized_row = {
                    normalize_header(key): (value or "")
                    for key, value in row.items()
                    if key is not None
                }
                description = pick_column(normalized_row, DESCRIPTION_COLUMNS)
                amount_text = pick_column(normalized_row, AMOUNT_COLUMNS)
                if not description or not amount_text:
                    continue

                amount = parse_amount(amount_text)
                category = categorize(description, rules)
                transactions.append(
                    Transaction(
                        source_file=csv_path.name,
                        date=pick_column(normalized_row, DATE_COLUMNS),
                        description=description,
                        amount=amount,
                        currency=pick_column(normalized_row, CURRENCY_COLUMNS, "CAD"),
                        transaction_type=pick_column(normalized_row, TYPE_COLUMNS),
                        category=category,
                    )
                )
    return transactions


def is_expense(transaction: Transaction) -> bool:
    transaction_type = transaction.transaction_type.lower()
    if "payment" in transaction_type:
        return False
    return transaction.amount > 0


def money(value: Decimal, currency: str) -> str:
    return f"{currency} {value.quantize(Decimal('0.01'))}"


def print_report(transactions: list[Transaction], include_details: bool) -> None:
    expenses = [transaction for transaction in transactions if is_expense(transaction)]
    by_currency: dict[str, dict[str, list[Transaction]]] = defaultdict(lambda: defaultdict(list))

    for transaction in expenses:
        by_currency[transaction.currency][transaction.category].append(transaction)

    if not expenses:
        print("No expenses found.")
        return

    for currency in sorted(by_currency):
        category_map = by_currency[currency]
        grand_total = sum(
            (transaction.amount for group in category_map.values() for transaction in group),
            Decimal("0"),
        )
        print(f"\nExpenses by category ({currency})")
        print("=" * 40)

        for category, group in sorted(
            category_map.items(),
            key=lambda item: sum((transaction.amount for transaction in item[1]), Decimal("0")),
            reverse=True,
        ):
            subtotal = sum((transaction.amount for transaction in group), Decimal("0"))
            transaction_label = "transaction" if len(group) == 1 else "transactions"
            print(f"{category}: {money(subtotal, currency)} ({len(group)} {transaction_label})")

            if include_details:
                for transaction in sorted(group, key=lambda item: (item.date, item.description)):
                    date = transaction.date or "unknown date"
                    print(f"  {date} | {transaction.description} | {money(transaction.amount, currency)}")

        print("-" * 40)
        print(f"Total: {money(grand_total, currency)}")


def write_category_csv(transactions: list[Transaction], output_path: Path) -> None:
    expenses = [transaction for transaction in transactions if is_expense(transaction)]
    rows: list[tuple[str, str, Decimal, int]] = []
    category_totals: dict[tuple[str, str], list[Transaction]] = defaultdict(list)

    for transaction in expenses:
        category_totals[(transaction.currency, transaction.category)].append(transaction)

    for (currency, category), group in category_totals.items():
        subtotal = sum((transaction.amount for transaction in group), Decimal("0"))
        rows.append((currency, category, subtotal, len(group)))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["currency", "category", "total", "transaction_count"])
        for currency, category, subtotal, count in sorted(rows):
            writer.writerow([currency, category, f"{subtotal.quantize(Decimal('0.01'))}", count])


def print_uncategorized(transactions: list[Transaction]) -> None:
    uncategorized = [
        transaction
        for transaction in transactions
        if is_expense(transaction) and transaction.category == "Uncategorized"
    ]
    if not uncategorized:
        print("\nNo uncategorized expenses found.")
        return

    totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    counts: dict[str, int] = defaultdict(int)
    for transaction in uncategorized:
        totals[transaction.description] += transaction.amount
        counts[transaction.description] += 1

    print("\nUncategorized merchants")
    print("=" * 40)
    for description, total in sorted(totals.items(), key=lambda item: item[1], reverse=True):
        count = counts[description]
        transaction_label = "transaction" if count == 1 else "transactions"
        print(f"{description}: {total.quantize(Decimal('0.01'))} ({count} {transaction_label})")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize credit card CSV expenses by editable categories."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Folder containing statement CSV files. Default: {DEFAULT_DATA_DIR}",
    )
    parser.add_argument(
        "--rules",
        type=Path,
        default=DEFAULT_RULES_FILE,
        help=f"Editable JSON category dictionary. Default: {DEFAULT_RULES_FILE}",
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="Print transactions under each category.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional CSV path for category totals.",
    )
    parser.add_argument(
        "--uncategorized",
        action="store_true",
        help="Print unmatched merchants so they can be added to category_rules.json.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rules = load_rules(args.rules)
    transactions = read_transactions(args.data_dir, rules)
    print_report(transactions, include_details=args.details)

    if args.uncategorized:
        print_uncategorized(transactions)

    if args.output:
        write_category_csv(transactions, args.output)
        print(f"\nWrote category totals to: {args.output}")


if __name__ == "__main__":
    main()
