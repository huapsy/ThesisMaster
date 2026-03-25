from __future__ import annotations

from comparison_study import ComparisonStudyConfig, run_comparison_study


if __name__ == "__main__":
    run_comparison_study(
        ComparisonStudyConfig(
            study_slug="study_05_intervention",
            title="Study 05 — Tailored Intervention Message: PHOENIX vs Healthcare Expert",
            report_name="study_05_report.txt",
            data_filename="study_05_intervention.csv",
            item_col="intervention_ID",
            dimension_order=[
                "overall_congruence",
                "depth_of_tailoring",
                "actionability",
                "professional_tone",
                "predicted_effectiveness",
            ],
        )
    )
