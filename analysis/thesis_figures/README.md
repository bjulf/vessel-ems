# Thesis Figures

This folder is the curated shortlist of figure files currently considered thesis-ready or close to thesis-ready.

The rest of `analysis/` remains the working archive and reproducibility trail.

A packaged snapshot for report assembly is also available under [Thesis_ready/](./Thesis_ready/).

## Current Figure Candidates

### Methods

- [methods/operational_load_validation.png](./methods/operational_load_validation.png)
- [methods/validation_profile_bars.png](./methods/validation_profile_bars.png)

Supporting note:

- [methods/operational_load_validation.md](./methods/operational_load_validation.md)

Intended use:

- general operational data validation or operational load validation in the Methods chapter
- synthetic validation-case design figure showing the staged 24 h load profile used for internal verification

### Results

- [results/sfoc_regime_thesis_scatter.png](./results/sfoc_regime_thesis_scatter.png)
- [results/synthetic_verification_overview_soc70.png](./results/synthetic_verification_overview_soc70.png)
- [results/synthetic_verification_overview_cstart700.png](./results/synthetic_verification_overview_cstart700.png)

Intended use:

- Results subsection for telemetry-based assessment of generator operating regimes and SFOC behavior
- Results subsection for synthetic-case verification of dispatch behavior with 70% initial SOC
- Results subsection or sensitivity appendix figure for the synthetic validation case with `700 g/start` startup penalty

## Related Handoffs

Related notes are grouped under:

- [../handoffs/operational_data_validation_handoff.md](../handoffs/operational_data_validation_handoff.md)
- [../handoffs/report_writing_handoff.md](../handoffs/report_writing_handoff.md)

## Workflow

Recommended workflow:

1. Generate or revise figures in the working analysis scripts and output folders.
2. Copy the current candidate figure into this curated folder when it is ready for thesis consideration.
3. When the figure is accepted, copy it into the report repository under the appropriate `Images/` location.
