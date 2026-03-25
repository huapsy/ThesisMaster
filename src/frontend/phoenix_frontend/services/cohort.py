from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


_VARIANTS: List[Dict[str, str]] = [
    {
        "label": "sleep_fragmentation",
        "complaint_suffix": "Sleep has been broken and my mood swings are sharper in the evening.",
        "person_suffix": "Often pushes through fatigue at work and skips recovery time.",
        "context_suffix": "High workload during weekdays with limited evening downtime.",
    },
    {
        "label": "social_friction",
        "complaint_suffix": "Mood changes are causing frequent friction with friends and family.",
        "person_suffix": "Strong social orientation and high sensitivity to peer feedback.",
        "context_suffix": "Recent conflicts in close relationships and reduced social support.",
    },
    {
        "label": "irregular_routine",
        "complaint_suffix": "I feel unstable when my daily routine changes suddenly.",
        "person_suffix": "Needs structure but currently has inconsistent daily habits.",
        "context_suffix": "Variable schedule with frequent transitions across tasks.",
    },
    {
        "label": "work_pressure",
        "complaint_suffix": "Stress from deadlines seems to amplify both low and high mood periods.",
        "person_suffix": "Perfectionistic work style and strong achievement pressure.",
        "context_suffix": "Sustained performance pressure and little buffer between commitments.",
    },
    {
        "label": "isolation_cycles",
        "complaint_suffix": "I withdraw for days and then suddenly become very active and social.",
        "person_suffix": "Alternates between social avoidance and high social drive.",
        "context_suffix": "Limited routine check-ins from close contacts.",
    },
    {
        "label": "energy_instability",
        "complaint_suffix": "Energy fluctuates heavily and makes planning difficult.",
        "person_suffix": "High variability in motivation across the day.",
        "context_suffix": "Demanding schedule with variable start and end times.",
    },
    {
        "label": "self_regulation",
        "complaint_suffix": "I recognize patterns but struggle to regulate reactions when they start.",
        "person_suffix": "Good insight into symptoms but inconsistent coping execution.",
        "context_suffix": "Few external reminders or prompts for coping routines.",
    },
    {
        "label": "family_context",
        "complaint_suffix": "Family members notice abrupt shifts and say I am hard to read.",
        "person_suffix": "Values family feedback but feels misunderstood during high-intensity periods.",
        "context_suffix": "Home environment has frequent emotionally charged interactions.",
    },
    {
        "label": "academic_pressure",
        "complaint_suffix": "Academic pressure makes my lows longer and my highs more impulsive.",
        "person_suffix": "Strong performance orientation and fear of falling behind.",
        "context_suffix": "Upcoming exams and unstable sleep schedule.",
    },
    {
        "label": "digital_overload",
        "complaint_suffix": "Too much late-night screen time seems to worsen mood unpredictability.",
        "person_suffix": "Heavy device use and difficulty disengaging before sleep.",
        "context_suffix": "High notification load and frequent nighttime interruptions.",
    },
    {
        "label": "activity_bursts",
        "complaint_suffix": "I overcommit during energetic phases and crash afterwards.",
        "person_suffix": "Tends to plan aggressively during elevated mood states.",
        "context_suffix": "Low guardrails around pacing and recovery.",
    },
    {
        "label": "coping_gaps",
        "complaint_suffix": "I know some coping tools but I do not apply them consistently.",
        "person_suffix": "Partial coping literacy with inconsistent self-monitoring.",
        "context_suffix": "No fixed daily slot for reflection or symptom logging.",
    },
]


@dataclass
class CohortCaseInput:
    index: int
    variant_label: str
    complaint_text: str
    person_text: str
    context_text: str



def _append_text(base: str, suffix: str) -> str:
    left = str(base or "").strip()
    right = str(suffix or "").strip()
    if not left:
        return right
    if not right:
        return left
    return f"{left} {right}".strip()



def build_cohort_cases(
    *,
    base_complaint: str,
    base_person: str,
    base_context: str,
    patient_count: int,
) -> List[CohortCaseInput]:
    count = max(1, int(patient_count))
    cases: List[CohortCaseInput] = []
    for idx in range(count):
        variant = _VARIANTS[idx % len(_VARIANTS)]
        complaint = _append_text(base_complaint, variant["complaint_suffix"])
        person = _append_text(base_person, variant["person_suffix"])
        context = _append_text(base_context, variant["context_suffix"])
        cases.append(
            CohortCaseInput(
                index=idx,
                variant_label=f"{variant['label']}_{idx + 1:02d}",
                complaint_text=complaint,
                person_text=person,
                context_text=context,
            )
        )
    return cases



def new_manifest(
    *,
    run_id: str,
    cohort_root: Path,
    seed_session_id: str,
    patient_count: int,
    parallel_patients: int,
    options: Dict[str, Any],
) -> Dict[str, Any]:
    now = datetime.now().isoformat(timespec="seconds")
    return {
        "run_id": run_id,
        "seed_session_id": seed_session_id,
        "status": "running",
        "created_at": now,
        "updated_at": now,
        "patient_count": int(patient_count),
        "parallel_patients": int(parallel_patients),
        "cohort_root": str(cohort_root),
        "options": dict(options),
        "patients": [],
        "summary": {
            "created_sessions": 0,
            "completed": 0,
            "failed": 0,
        },
    }



def update_manifest(path: Path, payload: Dict[str, Any]) -> None:
    payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
