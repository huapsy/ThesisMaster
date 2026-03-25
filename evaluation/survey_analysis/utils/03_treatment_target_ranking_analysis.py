from __future__ import annotations

from ranking_study import RankingStudyConfig, run_ranking_study


if __name__ == "__main__":
    run_ranking_study(
        RankingStudyConfig(
            study_slug="study_03_treatment_target",
            title="Study 03 — Personalized Treatment-Target Identification: PHOENIX vs Human",
            report_name="study_03_report.txt",
            data_filename="study_03_treatment_target.csv",
            task_col="task_ID",
            footrule_col="footrule_vs_gold",
            comparator_label="Human",
            lower_is_better=True,
        )
    )
