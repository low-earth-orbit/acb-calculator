# ACB Calculator

## Wealthsimple

Calculates the adjusted cost base (ACB) for securities from Wealthsimple activity exports.

### Usage

```bash
python acb-wealthsimple.py
```

### Process

1. Select one or more CSV files from the `data/` folder by index, or press Enter to use all available CSV files.
2. Select a security symbol from the aggregated file set.
3. Enter T3 box 21 and box 42 amounts by year, starting with the earliest tax year.
4. Get results: adjusted ACB and ACB per share.

### Notes

- This tool is Wealthsimple-specific and reads Wealthsimple activity export CSVs.
- Default behavior uses all CSV files in `data/` for multi-year aggregation.
