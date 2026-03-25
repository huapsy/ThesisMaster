from __future__ import annotations

from shared.ranking_study import RankingStudyConfig, run_ranking_study


if __name__ == "__main__":
    run_ranking_study(
        RankingStudyConfig(
            study_slug="study_00_momentary_impact",
            title="Study 00 — Momentary Impact Quantification: PHOENIX vs Static Estimator",
            report_name="study_00_report.txt",
            data_filename="study_00_momentary_impact.csv",
            task_col="network_ID",
            footrule_col="footrule_distance",
            comparator_label="Static Estimator",
            lower_is_better=True,
        )
    )
