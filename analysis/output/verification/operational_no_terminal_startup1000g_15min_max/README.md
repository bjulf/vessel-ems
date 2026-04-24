# Operational No-Terminal Startup-1000g 15-Minute Max Verification Package

This package is a copied-input bundle for the April 24, 2026 operational-profile comparison using a 15-minute max-hold load profile.
The final comparison figure in this directory was generated from the copied data in `milp/` and `rule_based/`, not by reading the original `runs/` directories directly.

## Original run directories

- MILP run:
  `C:\Users\bulve\OneDrive\master\model\runs\2026-04-24_141044_operational_model_soc60_no_terminal_cstart_1000g_15min_max`
- Rule-based run:
  `C:\Users\bulve\OneDrive\master\model\runs\2026-04-24_141149_operational_model_soc60_no_terminal_cstart_1000g_15min_max_rule_based`

## Copied raw inputs in this package

- Shared top-level load profile copy:
  `C:\Users\bulve\OneDrive\master\model\analysis\output\verification\operational_no_terminal_startup1000g_15min_max\load_profile.csv`
- MILP copied raw data:
  `C:\Users\bulve\OneDrive\master\model\analysis\output\verification\operational_no_terminal_startup1000g_15min_max\milp\params.toml`
  `C:\Users\bulve\OneDrive\master\model\analysis\output\verification\operational_no_terminal_startup1000g_15min_max\milp\dispatch_results.csv`
  `C:\Users\bulve\OneDrive\master\model\analysis\output\verification\operational_no_terminal_startup1000g_15min_max\milp\load_profile.csv`
- Rule-based copied raw data:
  `C:\Users\bulve\OneDrive\master\model\analysis\output\verification\operational_no_terminal_startup1000g_15min_max\rule_based\params.toml`
  `C:\Users\bulve\OneDrive\master\model\analysis\output\verification\operational_no_terminal_startup1000g_15min_max\rule_based\dispatch_results.csv`
  `C:\Users\bulve\OneDrive\master\model\analysis\output\verification\operational_no_terminal_startup1000g_15min_max\rule_based\load_profile.csv`

## Final comparison command

```powershell
python analysis\figure_scripts\plot_synthetic_dispatch_comparison.py `
  --milp-data-dir C:\Users\bulve\OneDrive\master\model\analysis\output\verification\operational_no_terminal_startup1000g_15min_max\milp `
  --rule-data-dir C:\Users\bulve\OneDrive\master\model\analysis\output\verification\operational_no_terminal_startup1000g_15min_max\rule_based `
  --output-dir C:\Users\bulve\OneDrive\master\model\analysis\output\verification\operational_no_terminal_startup1000g_15min_max `
  --output-stem operational_dispatch_comparison_no_terminal_startup1000g_15min_max `
  --power-y-min -350 `
  --power-y-max 350 `
  --soc-power-ref-kw 250
```
