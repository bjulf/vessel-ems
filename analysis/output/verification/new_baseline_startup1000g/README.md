# New Baseline Startup-1000g Verification Package

This package is a copied-input bundle for the April 24, 2026 synthetic baseline comparison.
The final comparison figure in this directory was generated from the copied data in `milp/` and `rule_based/`, not by reading the original `runs/` directories directly.

## Original run directories

- MILP run:
  `C:\Users\bulve\OneDrive\master\model\runs\2026-04-24_102335_baseline_model_no_terminal_soc_cstart_1000g`
- Rule-based run:
  `C:\Users\bulve\OneDrive\master\model\runs\2026-04-24_102351_baseline_model_no_terminal_soc_cstart_1000g_rule_based`

## Copied raw inputs in this package

- Shared top-level load profile copy:
  `C:\Users\bulve\OneDrive\master\model\analysis\output\verification\new_baseline_startup1000g\load_profile.csv`
- MILP copied raw data:
  `C:\Users\bulve\OneDrive\master\model\analysis\output\verification\new_baseline_startup1000g\milp\params.toml`
  `C:\Users\bulve\OneDrive\master\model\analysis\output\verification\new_baseline_startup1000g\milp\dispatch_results.csv`
  `C:\Users\bulve\OneDrive\master\model\analysis\output\verification\new_baseline_startup1000g\milp\load_profile.csv`
- Rule-based copied raw data:
  `C:\Users\bulve\OneDrive\master\model\analysis\output\verification\new_baseline_startup1000g\rule_based\params.toml`
  `C:\Users\bulve\OneDrive\master\model\analysis\output\verification\new_baseline_startup1000g\rule_based\dispatch_results.csv`
  `C:\Users\bulve\OneDrive\master\model\analysis\output\verification\new_baseline_startup1000g\rule_based\load_profile.csv`

## Copied verification plots

- `milp_verification_overview.png`
- `milp_verification_stress_window.png`
- `rule_based_verification_overview.png`
- `rule_based_verification_stress_window.png`

## Final comparison command

```powershell
python analysis\figure_scripts\plot_synthetic_dispatch_comparison.py `
  --milp-data-dir C:\Users\bulve\OneDrive\master\model\analysis\output\verification\new_baseline_startup1000g\milp `
  --rule-data-dir C:\Users\bulve\OneDrive\master\model\analysis\output\verification\new_baseline_startup1000g\rule_based `
  --output-dir C:\Users\bulve\OneDrive\master\model\analysis\output\verification\new_baseline_startup1000g `
  --output-stem synthetic_dispatch_comparison_new_baseline_startup1000g
```
