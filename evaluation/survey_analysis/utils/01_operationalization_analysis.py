from __future__ import annotations

from comparison_study import ComparisonStudyConfig, run_comparison_study


if __name__ == "__main__":
    run_comparison_study(
        ComparisonStudyConfig(
            study_slug="study_01_operationalization",
            title="Study 01 — Operationalization: PHOENIX vs Healthcare Expert",
            report_name="study_01_report.txt",
            data_filename="study_01_operationalization.csv",
            item_col="text_ID",
            dimension_order=[
                "accurate_depiction",
                "mathematical_suitability",
                "data_collection_feasibility",
            ],
        )
    )
