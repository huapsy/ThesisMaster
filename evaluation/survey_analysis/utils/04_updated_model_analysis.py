from __future__ import annotations

from comparison_study import ComparisonStudyConfig, run_comparison_study


if __name__ == "__main__":
    run_comparison_study(
        ComparisonStudyConfig(
            study_slug="study_04_updated_model",
            title="Study 04 — Updated Observational Model: PHOENIX vs Healthcare Expert",
            report_name="study_04_report.txt",
            data_filename="study_04_updated_model.csv",
            item_col="task_ID",
            dimension_order=[
                "accurate_depiction",
                "mathematical_suitability",
                "data_collection_feasibility",
                "treatment_translation",
                "bfs_alignment",
            ],
        )
    )
