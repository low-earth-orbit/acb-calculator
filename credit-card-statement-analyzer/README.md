# Credit Card Statement Analyzer

Summarizes credit card expenses from CSV files in `data/` by editable categories.

The analyzer works with Wealthsimple Credit Card Statement CSV files.

## Usage

```bash
python credit-card.py
```

Show the transactions under each category:

```bash
python credit-card.py --details
```

Show unmatched merchants that should be added to `category_rules.json`:

```bash
python credit-card.py --uncategorized
```

Write category totals to a CSV file:

```bash
python credit-card.py --output output/category-totals.csv
```

Use another data folder or category file:

```bash
python credit-card.py --data-dir data --rules category_rules.json
```

## Editing Categories

Edit `category_rules.json`. Each key is a category name, and each value is a list of keywords to match against the transaction description.

Example:

```json
{
  "Restaurants & Coffee": ["tim hortons", "restaurant", "coffee"],
  "Groceries": ["superstore", "sobeys", "costco"]
}
```

Rules are checked from top to bottom. If no keyword matches, the transaction goes under `Uncategorized`.

For best results, run `python credit-card.py --uncategorized` after adding new statements, then add recurring unmatched merchants to the most appropriate category.
