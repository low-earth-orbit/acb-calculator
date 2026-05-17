# Personal Finance Tools

Small Python tools for personal finance analysis.

## ACB Calculator

Location: `acb-calculator/`

Calculates adjusted cost base (ACB) for Wealthsimple activity exports.

```bash
cd acb-calculator
python acb-wealthsimple.py
```

See `acb-calculator/README.md` for details.

## Credit Card Statement Analyzer

Location: `credit-card-statement-analyzer/`

Summarizes Visa credit card statement CSV expenses by editable categories.

```bash
cd credit-card-statement-analyzer
python credit-card.py
```

Useful options:

```bash
python credit-card.py --details
python credit-card.py --uncategorized
python credit-card.py --output output/category-totals.csv
```

Categories are controlled by `credit-card-statement-analyzer/category_rules.json`.

See `credit-card-statement-analyzer/README.md` for details.
