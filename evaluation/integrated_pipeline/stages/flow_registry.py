from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


@dataclass(frozen=True)
class FlowStage:
    stage_id: str
    label: str
    source_stage: str
    category: str
    description: str
    depends_on: tuple[str, ...] = ()


ENGINE_FLOW: tuple[FlowStage, ...] = (
    FlowStage(
        stage_id="operationalization",
        label="00 Operationalization",
        source_stage="operationalization",
        category="engine",
        description="Free-text complaint operationalization into criteria mappings.",
    ),
    FlowStage(
        stage_id="initial_observation_model",
        label="01 Initial Observation Model",
        source_stage="initial_model",
        category="engine",
        description="Initial observation model construction from operationalized criteria.",
        depends_on=("operationalization",),
    ),
    FlowStage(
        stage_id="pseudodata_generation",
        label="02 Pseudodata Generation",
        source_stage="pseudodata",
        category="engine",
        description="Time-series pseudodata generation from the initial observation model.",
        depends_on=("initial_observation_model",),
    ),
    FlowStage(
        stage_id="readiness_check",
        label="03 Readiness Check",
        source_stage="readiness",
        category="engine",
        description="Data sufficiency and method gating.",
        depends_on=("pseudodata_generation",),
    ),
    FlowStage(
        stage_id="network_time_series_analysis",
        label="04 Network Time-Series Analysis",
        source_stage="network",
        category="engine",
        description="tv-gVAR / stationary / baseline network estimation.",
        depends_on=("readiness_check",),
    ),
    FlowStage(
        stage_id="momentary_impact_quantification",
        label="05 Momentary Impact Quantification",
        source_stage="impact",
        category="engine",
        description="Predictor-level impact quantification.",
        depends_on=("network_time_series_analysis",),
    ),
    FlowStage(
        stage_id="treatment_target_identification",
        label="06 Treatment Target Identification",
        source_stage="handoff",
        category="engine",
        description="Agentic Step-03 target ranking and guardrails.",
        depends_on=("momentary_impact_quantification",),
    ),
    FlowStage(
        stage_id="updated_observation_model",
        label="07 Updated Observation Model",
        source_stage="handoff",
        category="engine",
        description="Agentic Step-04 observation-model update.",
        depends_on=("treatment_target_identification",),
    ),
    FlowStage(
        stage_id="digital_intervention_translation",
        label="08 Digital Intervention Translation",
        source_stage="intervention",
        category="engine",
        description="Agentic Step-05 HAPA intervention translation.",
        depends_on=("updated_observation_model",),
    ),
    FlowStage(
        stage_id="treatment_translation_communication",
        label="09 Treatment Translation Communication",
        source_stage="translation_communication",
        category="engine",
        description="End-stage user/research communication from Step-04/05 outputs.",
        depends_on=("digital_intervention_translation",),
    ),
    FlowStage(
        stage_id="iterative_model_update",
        label="10 Iterative Model Update (Next Cycle Input)",
        source_stage="iterative_update",
        category="engine",
        description="Cycle-memory packaging from Step-04/Step-05 outputs to seed the next cycle.",
        depends_on=("treatment_translation_communication",),
    ),
)


SUPPORT_FLOW: tuple[FlowStage, ...] = (
    FlowStage(
        stage_id="impact_visualization_support",
        label="S1 Impact Visualization (Support)",
        source_stage="visualization",
        category="quality_and_research",
        description="Research-grade static visual exports.",
        depends_on=("momentary_impact_quantification",),
    ),
    FlowStage(
        stage_id="research_reporting_support",
        label="S2 Research Reporting (Support)",
        source_stage="reporting",
        category="quality_and_research",
        description="Run-level report generation for evaluation communication.",
        depends_on=("impact_visualization_support",),
    ),
)


def _as_mapping(result: Any) -> Dict[str, Any]:
    if isinstance(result, Mapping):
        return dict(result)
    return {
        "stage": str(getattr(result, "stage", "")),
        "return_code": int(getattr(result, "return_code", -1)),
        "duration_seconds": float(getattr(result, "duration_seconds", 0.0)),
        "log_path": str(getattr(result, "log_path", "")),
    }


def _result_index(stage_results: Iterable[Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for raw in stage_results:
        row = _as_mapping(raw)
        stage = str(row.get("stage") or "").strip()
        if not stage:
            continue
        out[stage] = row
    return out


def _status_from_result(result: Optional[Mapping[str, Any]]) -> str:
    if not result:
        return "skipped"
    return "succeeded" if int(result.get("return_code", 1)) == 0 else "failed"


def _flow_row(
    stage: FlowStage,
    *,
    stage_results: Mapping[str, Mapping[str, Any]],
    explicit_status: Optional[str] = None,
) -> Dict[str, Any]:
    source_result = stage_results.get(stage.source_stage)
    status = explicit_status or _status_from_result(source_result)
    duration = 0.0
    command: List[str] = []
    log_path = ""
    return_code: Optional[int] = None
    if source_result:
        duration = float(source_result.get("duration_seconds", 0.0) or 0.0)
        command = [str(x) for x in (source_result.get("command") or [])]
        log_path = str(source_result.get("log_path") or "")
        if source_result.get("return_code") is not None:
            return_code = int(source_result.get("return_code"))

    return {
        "stage_id": stage.stage_id,
        "label": stage.label,
        "category": stage.category,
        "description": stage.description,
        "depends_on": list(stage.depends_on),
        "source_stage": stage.source_stage,
        "status": status,
        "return_code": return_code,
        "duration_seconds": round(float(duration), 3),
        "command": command,
        "log_path": log_path,
    }


def build_flow_summary(
    *,
    stage_results: Sequence[Any],
    step03_generated: bool,
    step04_generated: bool,
    step05_generated: bool,
    translation_generated: bool,
    pseudodata_ready: bool = False,
    iterative_update_generated: bool = False,
) -> Dict[str, Any]:
    indexed = _result_index(stage_results)

    engine_rows: List[Dict[str, Any]] = []
    for stage in ENGINE_FLOW:
        forced_status: Optional[str] = None
        if stage.stage_id == "pseudodata_generation":
            forced_status = "succeeded" if pseudodata_ready else "failed"
        elif stage.stage_id == "treatment_target_identification":
            forced_status = "succeeded" if step03_generated else "skipped"
            if indexed.get(stage.source_stage) and _status_from_result(indexed.get(stage.source_stage)) == "failed":
                forced_status = "failed"
        elif stage.stage_id == "updated_observation_model":
            forced_status = "succeeded" if step04_generated else "skipped"
            if indexed.get(stage.source_stage) and _status_from_result(indexed.get(stage.source_stage)) == "failed":
                forced_status = "failed"
        elif stage.stage_id == "digital_intervention_translation":
            forced_status = "succeeded" if step05_generated else "skipped"
            if indexed.get(stage.source_stage) and _status_from_result(indexed.get(stage.source_stage)) == "failed":
                forced_status = "failed"
        elif stage.stage_id == "treatment_translation_communication":
            forced_status = "succeeded" if translation_generated else "skipped"
            if indexed.get(stage.source_stage) and _status_from_result(indexed.get(stage.source_stage)) == "failed":
                forced_status = "failed"
        elif stage.stage_id == "iterative_model_update":
            forced_status = "succeeded" if iterative_update_generated else "skipped"
            if indexed.get(stage.source_stage) and _status_from_result(indexed.get(stage.source_stage)) == "failed":
                forced_status = "failed"

        engine_rows.append(
            _flow_row(
                stage,
                stage_results=indexed,
                explicit_status=forced_status,
            )
        )

    support_rows = [
        _flow_row(stage, stage_results=indexed)
        for stage in SUPPORT_FLOW
    ]

    return {
        "flow_version": "2.0.0",
        "engine_stage_flow": engine_rows,
        "quality_and_research_flow": support_rows,
    }
