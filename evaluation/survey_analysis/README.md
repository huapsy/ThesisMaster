# PHOENIX Survey Analysis

This folder contains the modular survey-analysis stack for the PHOENIX evaluation framework: pseudodata generation, shared statistics utilities, study runners, and publication-oriented outputs.

## Purpose

The goal of this folder is not only to generate plots, but to implement a defensible statistical comparison between PHOENIX and its human comparators at each decision point of the pipeline.

The current implementation covers:

- `study_00`: momentary-impact quantification versus a simpler non-LLM estimator
- `study_01`: operationalization quality, PHOENIX versus healthcare expert
- `study_02`: initial observational model quality, PHOENIX versus healthcare expert
- `study_03`: treatment-target ranking, PHOENIX versus non-expert users
- `study_04`: updated observational model quality, PHOENIX versus healthcare expert
- `study_05`: tailored intervention-message quality, PHOENIX versus healthcare expert outputs rated by lay users
- `study_06`: holistic PHOENIX-versus-healthcare-expert synthesis across studies `01`, `02`, `04`, and `05`

Studies `00` and `03` are intentionally excluded from the holistic PHOENIX-versus-HCP model because those studies do not compare PHOENIX directly against healthcare professionals.

## Folder Structure

- [data](/Users/stijnvanseveren/PythonProjects/MASTERPROEF/evaluation/survey_analysis/data): pseudodata entrypoint and generated CSV files
- [utils](/Users/stijnvanseveren/PythonProjects/MASTERPROEF/evaluation/survey_analysis/utils): shared statistics modules and thin study wrappers
- [results](/Users/stijnvanseveren/PythonProjects/MASTERPROEF/evaluation/survey_analysis/results): generated reports and figures
- [run_all_studies.sh](/Users/stijnvanseveren/PythonProjects/MASTERPROEF/evaluation/survey_analysis/run_all_studies.sh): end-to-end runner for all studies

## Statistical Principles

The implementation follows the thesis protocol closely, but makes the dependence structure more explicit so the analysis is closer to a research-grade repeated-measures design.

### Why mixed-effects models are the default

Across the survey studies, observations are not independent:

- the same participant rates multiple items
- the same item is rated by multiple participants
- in comparative studies, the same participant often rates both PHOENIX and the comparison output

For that reason, the primary analysis is based on linear mixed-effects models instead of simple rank tests or independent-group tests. Nonparametric tests remain only as fallbacks when a richer model does not converge.

### Why Likert ratings are analyzed with linear mixed models

The outcomes in studies `01`, `02`, `04`, and `05` are ordinal 1 to 9 ratings. In a strict psychometric sense, ordinal mixed models are possible. In this repository, linear mixed models are used as the primary analysis because they:

- support the crossed random-effects structure needed here
- keep coefficients directly comparable across studies and dimensions
- work well for bounded Likert outcomes when the main target is comparative mean performance rather than latent-threshold estimation

This is a pragmatic modelling choice, not a claim that the scale is interval-perfect.

## Study Families

### Ranking studies: `00` and `03`

These studies use Spearman footrule distance as the dependent variable, where lower values indicate better agreement with the latent gold ranking.

Primary model:

- fixed effect for `estimator`
- fixed effect for `shift_regime` when present
- participant-level random intercept
- participant-level random slope for estimator when estimable
- crossed task or network random intercept

Why this structure:

- the repeated comparison is within participant
- tasks vary in intrinsic difficulty
- some participants may consistently prefer or misunderstand one estimator more than another

### Expert-comparison Likert studies: `01`, `02`, `04`, `05`

These studies are run per dimension, not pooled across dimensions inside the same model.

Primary model per dimension:

- fixed effect for `source` (`PHOENIX` vs `HCP`)
- fixed effect for `shift_regime` when present
- participant-level random intercept
- participant-level random slope for source when estimable
- one study-specific item-level random intercept

Item-level random factors are:

- `text_ID` in study `01`
- `item_ID` in study `02`
- `task_ID` in study `04`
- `intervention_ID` in study `05`

These are not four random effects inside a single model. Each study uses exactly one item-level clustering variable, chosen to match the unit being rated in that study.

Multiplicity control:

- Bonferroni correction is applied within each study across the rated dimensions, in line with the thesis protocol

Interpretation target:

- the coefficient of `source` estimates the average PHOENIX-versus-HCP difference after accounting for participant severity and task difficulty

### Holistic study: `06`

Study `06` is the most important model from a validation perspective. It pools normalized trial-level scores from studies `01`, `02`, `04`, and `05` to ask whether PHOENIX performs better than healthcare-expert outputs overall.

Primary fixed effects:

- `reasoner_group`
- `study_id`
- `dimension`
- `shift_regime` when available

Primary random structure:

- participant-level random intercept
- participant-level random slope for `reasoner_group` when estimable
- crossed `task_key` random intercept
- crossed `response_run_id` random intercept

Why `response_run_id` is included:

- each participant rates a PHOENIX or HCP output on several dimensions within the same answer block
- those dimension ratings are not independent
- `response_run_id` captures the local clustering of repeated answers within the same participant-task-source block

In practical terms, the holistic model adjusts for three distinct sources of dependence:

- stable leniency or severity differences between raters
- some tasks being intrinsically easier or harder to rate well
- repeated dimension-level scores coming from the same answer block

Secondary follow-up models:

- stratified study-specific PHOENIX-versus-HCP models are reported after the unified model
- those follow-up p-values are Holm-adjusted across studies

This makes the unified model the primary inferential target, while keeping study-specific effects interpretable without overclaiming.

## Pseudodata Design

The pseudodata generator is structured to stress-test the analysis pipeline rather than produce trivial synthetic wins.

It explicitly encodes:

- participant heterogeneity
- task heterogeneity
- dimension-specific advantages and disadvantages for PHOENIX and HCP
- distribution shift through `standard`, `ambiguous`, `implementation_shift`, and `context_shift`
- a study-06 answer-block identifier (`response_run_id`) so the holistic model can represent repeated dimension scoring properly

This is useful because a realistic evaluation pipeline should still behave sensibly when performance varies by domain, regime, or rater population.

## Visual Outputs

The figures are meant for research communication and diagnostic interpretation.

Current output types include:

- violin plots for distributional comparison
- forest plots for effect sizes and confidence intervals
- shift-regime plots for robustness checks
- holistic heatmaps to inspect PHOENIX-minus-HCP patterns across studies and dimensions

## Running The Full Pipeline

From the repository root:

```bash
bash evaluation/survey_analysis/run_all_studies.sh
```

This will:

1. regenerate survey pseudodata
2. run studies `00` through `06`
3. write updated reports and figures into `evaluation/survey_analysis/results`

## Tracked Artifacts

Generated survey CSV files and result directories are intentionally excluded from version control.

The repository `.gitignore` ignores:

- `evaluation/survey_analysis/data/study_*.csv`
- `evaluation/survey_analysis/results/`
- large PHOENIX run outputs such as `evaluation/integrated_pipeline/runs/` and `evaluation/sequential/**/outputs/`

That keeps commits focused on code and documentation rather than reproducible heavy artifacts.
