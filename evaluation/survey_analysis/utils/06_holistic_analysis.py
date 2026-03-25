from __future__ import annotations

from shared.holistic_comparison import HolisticStudyConfig, run_holistic_reasoner_comparison


if __name__ == "__main__":
    run_holistic_reasoner_comparison(
        HolisticStudyConfig(
            study_slug="study_06_holistic",
            title="Study 06 — Holistic Evaluation: PHOENIX vs Healthcare Expert",
            report_name="study_06_report.txt",
            data_filename="study_06_holistic.csv",
        )
    )
