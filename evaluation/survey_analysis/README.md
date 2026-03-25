# PHOENIX Survey Analysis

This folder contains the pseudodata generator, shared analysis utilities, and study-specific runners for the survey-based evaluation framework around PHOENIX.

## Scope

The implemented study set covers:

- `study_00`: quantification of momentary impact, PHOENIX quantification versus layperson ranking
- `study_01`: operationalization quality, PHOENIX versus healthcare expert
- `study_02`: initial observational model quality, PHOENIX versus healthcare expert
- `study_03`: treatment-target identification, PHOENIX versus non-expert ranking
- `study_04`: updated observational model quality, PHOENIX versus healthcare expert
- `study_05`: tailored intervention message quality, PHOENIX versus healthcare expert outputs rated by non-expert users
- `study_06`: holistic human-in-the-loop comparison, PHOENIX versus healthcare expert aggregated over studies 01, 02, 04, and 05

Study `06` intentionally excludes studies `00` and `03` from the unified PHOENIX-vs-HCP model because those studies do not compare PHOENIX directly against healthcare professionals.

## Folder Layout

- [data](/Users/stijnvanseveren/PythonProjects/MASTERPROEF/evaluation/survey_analysis/data): pseudodata entrypoint and generated CSV inputs
- [utils](/Users/stijnvanseveren/PythonProjects/MASTERPROEF/evaluation/survey_analysis/utils): shared analysis modules plus thin study wrappers
- [results](/Users/stijnvanseveren/PythonProjects/MASTERPROEF/evaluation/survey_analysis/results): generated reports and figures
- [run_all_studies.sh](/Users/stijnvanseveren/PythonProjects/MASTERPROEF/evaluation/survey_analysis/run_all_studies.sh): full end-to-end runner

## Statistical Design

The implementation follows the thesis intent, but the model structure is made more explicit to reflect the repeated-measures nature of the survey tasks.

### Ranking studies

Studies `00` and `03` use Spearman footrule distance as the dependent variable. The primary model is a linear mixed-effects model with:

- fixed effect for `estimator`
- fixed effect for `shift_regime` when present
- participant-level grouping with a random slope for estimator when the fit is stable
- crossed task or network random intercepts

This is preferable to treating tasks alone as the main grouping factor, because the repeated pairing is observed within participant across estimators.

### Likert comparison studies

Studies `01`, `02`, `04`, and `05` are analysed per dimension using:

- fixed effect for `source` (`PHOENIX` vs `HCP`)
- fixed effect for `shift_regime` when present
- participant-level grouping with a random slope for source when estimable
- crossed item-level random intercepts (`text_ID`, `item_ID`, `task_ID`, or `intervention_ID`)

Bonferroni correction is applied within each study across the rated dimensions, matching the thesis design.

### Holistic study

Study `06` pools normalized trial-level scores from studies `01`, `02`, `04`, and `05`. The unified model includes:

- fixed effect for `reasoner_group`
- fixed effects for `study_id` and `dimension`
- fixed effect for `shift_regime` when available
- participant-level grouping with a random slope for reasoner when estimable
- crossed `task_key` random intercepts

This structure supports the central question of whether PHOENIX performs on par with or better than healthcare expert outputs after adjusting for study context and dimension.

## Pseudodata Logic

The pseudodata generator is not flat synthetic noise. It encodes expected evaluation patterns:

- different baseline strengths for PHOENIX and HCP by dimension
- task-level heterogeneity
- participant-level heterogeneity
- shift regimes such as `ambiguous`, `implementation_shift`, and `context_shift`

These regimes are meant to stress the analysis and visualization pipeline with realistic distribution shift rather than producing trivial one-sided dominance.

## Visual Outputs

The plotting stack is intended for research reporting, not only debugging. Each study produces figures that answer a specific question:

- violin plots for distributional comparison
- per-dimension or per-study forest plots for effect direction and uncertainty
- shift-regime plots to inspect robustness under distribution shift
- holistic heatmaps to show PHOENIX-minus-HCP patterns across studies and dimensions

## Running The Full Pipeline

From the repository root:

```bash
bash evaluation/survey_analysis/run_all_studies.sh
```

This will:

1. regenerate pseudodata
2. run studies `00` through `06`
3. write reports and figures into `evaluation/survey_analysis/results`

## Git Hygiene

Generated survey CSVs and result folders are intentionally excluded from version control. The repository `.gitignore` ignores:

- `evaluation/survey_analysis/data/study_*.csv`
- `evaluation/survey_analysis/results/`
- large PHOENIX run outputs such as `evaluation/integrated_pipeline/runs/` and `evaluation/sequential/**/outputs/`

This keeps the committed history focused on code, not reproducible heavy artifacts.
