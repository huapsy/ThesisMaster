"""DAG-based pipeline orchestrator for the PHOENIX mental health multi-agent system.

Replaces sequential subprocess calls with a directed acyclic graph execution
engine that supports parallel execution, critic-actor revision loops, and
real-time event streaming for UI integration.
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Callable, Optional

__all__ = [
    "StageStatus",
    "StageCategory",
    "StageNode",
    "StageResult",
    "CriticVerdict",
    "PipelineEvent",
    "PipelineResult",
    "PipelineDAG",
    "CriticActorLoop",
    "PipelineOrchestrator",
    "build_phoenix_dag",
    "format_pipeline_summary",
    "PHOENIX_DAG",
]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class StageStatus(Enum):
    """Lifecycle states for a pipeline stage."""
    PENDING = auto()
    READY = auto()
    RUNNING = auto()
    PASSED = auto()
    REVISING = auto()
    FAILED = auto()
    SKIPPED = auto()


class StageCategory(Enum):
    """Functional category of a pipeline stage."""
    CORE = auto()
    ANALYSIS = auto()
    SUPPORT = auto()


class EventType(Enum):
    """Types of events emitted during pipeline execution."""
    STARTED = auto()
    COMPLETED = auto()
    FAILED = auto()
    REVISING = auto()
    SKIPPED = auto()
    PROGRESS = auto()


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class StageResult:
    """Outcome produced by a single stage executor."""
    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    critic_feedback: Optional[str] = None
    artifacts: dict[str, Any] = field(default_factory=dict)
    token_usage: dict[str, int] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class CriticVerdict:
    """Decision returned by the critic-actor loop evaluator."""
    passed: bool
    score: float
    feedback: str
    should_continue: bool = True


@dataclass
class PipelineEvent:
    """Real-time event emitted during pipeline execution."""
    timestamp: datetime
    stage_id: str
    event_type: EventType
    message: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class StageNode:
    """Single vertex in the pipeline DAG."""
    id: str
    name: str
    dependencies: list[str] = field(default_factory=list)
    is_critic_gated: bool = False
    max_revisions: int = 2
    pass_threshold: float = 0.74
    category: StageCategory = StageCategory.CORE
    executor: Optional[Callable[..., StageResult]] = None

    # Mutable runtime state
    status: StageStatus = StageStatus.PENDING
    result: Optional[StageResult] = None
    score: float = 0.0
    revision_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0


@dataclass
class PipelineResult:
    """Aggregate outcome of a full pipeline run."""
    success: bool
    stages: dict[str, StageResult] = field(default_factory=dict)
    total_duration: float = 0.0
    total_tokens: dict[str, int] = field(default_factory=dict)
    events: list[PipelineEvent] = field(default_factory=list)
    dag_snapshot: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# PipelineDAG
# ---------------------------------------------------------------------------

class PipelineDAG:
    """Directed acyclic graph representing pipeline stages and their deps."""

    def __init__(self) -> None:
        self._stages: dict[str, StageNode] = {}
        self._lock = threading.Lock()

    # -- construction -------------------------------------------------------

    def add_stage(self, stage: StageNode) -> None:
        """Register a stage in the DAG."""
        self._stages[stage.id] = stage

    def add_edge(self, from_id: str, to_id: str) -> None:
        """Declare that *to_id* depends on *from_id*."""
        if from_id not in self._stages or to_id not in self._stages:
            raise ValueError(f"Unknown stage in edge {from_id} -> {to_id}")
        stage = self._stages[to_id]
        if from_id not in stage.dependencies:
            stage.dependencies.append(from_id)

    # -- queries ------------------------------------------------------------

    def __getitem__(self, stage_id: str) -> StageNode:
        return self._stages[stage_id]

    def __contains__(self, stage_id: str) -> bool:
        return stage_id in self._stages

    @property
    def stages(self) -> dict[str, StageNode]:
        return dict(self._stages)

    def ready_stages(self) -> list[StageNode]:
        """Return stages whose dependencies have all PASSED."""
        with self._lock:
            return [
                s for s in self._stages.values()
                if s.status == StageStatus.PENDING
                and all(
                    self._stages[d].status == StageStatus.PASSED
                    for d in s.dependencies
                )
            ]

    def advance(self, stage_id: str, result: StageResult) -> None:
        """Update a stage based on its execution result and critic verdict."""
        with self._lock:
            stage = self._stages[stage_id]
            stage.result = result
            stage.score = result.score
            stage.completed_at = datetime.now(timezone.utc)
            if stage.started_at:
                stage.duration_seconds = (
                    stage.completed_at - stage.started_at
                ).total_seconds()

            if result.success:
                stage.status = StageStatus.PASSED
            else:
                stage.status = StageStatus.FAILED

    def execution_plan(self) -> list[str]:
        """Return a topologically sorted list of stage IDs."""
        visited: set[str] = set()
        order: list[str] = []

        def _visit(sid: str) -> None:
            if sid in visited:
                return
            visited.add(sid)
            for dep in self._stages[sid].dependencies:
                _visit(dep)
            order.append(sid)

        for sid in self._stages:
            _visit(sid)
        return order

    def parallel_groups(self) -> list[list[str]]:
        """Return groups of stages that can execute simultaneously.

        Each group contains stages whose dependencies are fully satisfied by
        all preceding groups.
        """
        remaining = set(self._stages.keys())
        completed: set[str] = set()
        groups: list[list[str]] = []

        while remaining:
            group = [
                sid for sid in remaining
                if all(d in completed for d in self._stages[sid].dependencies)
            ]
            if not group:
                raise RuntimeError("Cycle detected in pipeline DAG")
            groups.append(sorted(group))
            completed.update(group)
            remaining -= set(group)
        return groups

    def reset(self) -> None:
        """Reset all stages to PENDING."""
        with self._lock:
            for stage in self._stages.values():
                stage.status = StageStatus.PENDING
                stage.result = None
                stage.score = 0.0
                stage.revision_count = 0
                stage.started_at = None
                stage.completed_at = None
                stage.duration_seconds = 0.0

    def state_snapshot(self) -> dict[str, Any]:
        """Return a serialisable dict of all stage states."""
        with self._lock:
            return {
                sid: {
                    "name": s.name,
                    "status": s.status.name,
                    "category": s.category.name,
                    "score": s.score,
                    "revision_count": s.revision_count,
                    "duration_seconds": s.duration_seconds,
                    "dependencies": list(s.dependencies),
                }
                for sid, s in self._stages.items()
            }

    def to_mermaid(self) -> str:
        """Return a Mermaid flowchart with status-based node colours."""
        status_styles: dict[StageStatus, str] = {
            StageStatus.PENDING: "fill:#e0e0e0,color:#333",
            StageStatus.READY: "fill:#fff3cd,color:#856404",
            StageStatus.RUNNING: "fill:#cce5ff,color:#004085",
            StageStatus.PASSED: "fill:#d4edda,color:#155724",
            StageStatus.REVISING: "fill:#fff3cd,color:#856404",
            StageStatus.FAILED: "fill:#f8d7da,color:#721c24",
            StageStatus.SKIPPED: "fill:#d6d8db,color:#383d41",
        }
        lines: list[str] = ["graph TD"]
        for sid, stage in self._stages.items():
            label = f"{sid}[{stage.name}]"
            lines.append(f"    {label}")
        for sid, stage in self._stages.items():
            for dep in stage.dependencies:
                lines.append(f"    {dep} --> {sid}")
        # Style classes
        for status, css in status_styles.items():
            members = [
                sid for sid, s in self._stages.items() if s.status == status
            ]
            if members:
                lines.append(
                    f"    style {','.join(members)} {css}"
                )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# CriticActorLoop
# ---------------------------------------------------------------------------

class CriticActorLoop:
    """Manages the critic-gated revision cycle for quality assurance."""

    def __init__(
        self,
        max_revisions: int = 2,
        pass_threshold: float = 0.74,
        score_weights: Optional[dict[str, float]] = None,
    ) -> None:
        self.max_revisions = max_revisions
        self.pass_threshold = pass_threshold
        self.score_weights = score_weights or {}
        self._previous_score: Optional[float] = None

    def evaluate(self, stage_result: StageResult) -> CriticVerdict:
        """Determine whether the stage output meets quality requirements."""
        score = stage_result.score
        passed = score >= self.pass_threshold
        feedback = stage_result.critic_feedback or (
            "Stage passed quality threshold."
            if passed
            else f"Score {score:.2f} below threshold {self.pass_threshold:.2f}."
        )
        return CriticVerdict(
            passed=passed,
            score=score,
            feedback=feedback,
            should_continue=not passed,
        )

    def adaptive_threshold(
        self, revision_count: int, base_threshold: float,
    ) -> float:
        """Relax threshold slightly per revision to prevent infinite loops.

        Reduces the threshold by 0.02 for each revision attempt.
        """
        return max(0.0, base_threshold - 0.02 * revision_count)

    def should_continue(self, score: float, revision_count: int) -> bool:
        """Check whether another revision is warranted.

        Stops if the maximum number of revisions is reached or when the score
        improvement between revisions is negligible (< 0.02).
        """
        if revision_count >= self.max_revisions:
            return False
        if self._previous_score is not None:
            delta = score - self._previous_score
            if delta < 0.02:
                return False
        self._previous_score = score
        return True


# ---------------------------------------------------------------------------
# PipelineOrchestrator
# ---------------------------------------------------------------------------

class PipelineOrchestrator:
    """Executes a PipelineDAG with parallel scheduling and critic loops."""

    def __init__(
        self,
        dag: PipelineDAG,
        event_callback: Optional[Callable[[PipelineEvent], None]] = None,
        max_parallel: int = 4,
    ) -> None:
        self.dag = dag
        self._event_callback = event_callback or (lambda _e: None)
        self._max_parallel = max_parallel
        self._cancelled = threading.Event()
        self._lock = threading.Lock()
        self._events: list[PipelineEvent] = []

    # -- public API ---------------------------------------------------------

    def execute(self, context: dict[str, Any]) -> PipelineResult:
        """Run the full pipeline respecting DAG dependencies.

        Uses a ThreadPoolExecutor to process independent stages in parallel.
        Stages gated by a critic loop will be revised up to their configured
        maximum before being marked PASSED or FAILED.
        """
        start = time.monotonic()
        self._cancelled.clear()
        self._events.clear()
        all_results: dict[str, StageResult] = {}

        with ThreadPoolExecutor(max_workers=self._max_parallel) as pool:
            futures: dict[str, Future[StageResult]] = {}

            while True:
                if self._cancelled.is_set():
                    break

                # Collect completed futures
                done_ids = [
                    sid for sid, fut in futures.items() if fut.done()
                ]
                for sid in done_ids:
                    fut = futures.pop(sid)
                    try:
                        result = fut.result()
                    except Exception as exc:
                        result = StageResult(
                            success=False, error=str(exc),
                        )
                    all_results[sid] = result
                    self._finish_stage(sid, result)

                # Submit newly ready stages
                for stage in self.dag.ready_stages():
                    if stage.id not in futures:
                        stage.status = StageStatus.RUNNING
                        stage.started_at = datetime.now(timezone.utc)
                        self._emit(stage.id, EventType.STARTED, "Stage started")
                        futures[stage.id] = pool.submit(
                            self.execute_stage, stage, context,
                        )

                # Termination: nothing running and nothing ready
                if not futures and not self.dag.ready_stages():
                    break

                time.sleep(0.05)

        total_duration = time.monotonic() - start
        total_tokens: dict[str, int] = {}
        for res in all_results.values():
            for key, val in res.token_usage.items():
                total_tokens[key] = total_tokens.get(key, 0) + val

        success = all(
            s.status in (StageStatus.PASSED, StageStatus.SKIPPED)
            for s in self.dag.stages.values()
        )

        return PipelineResult(
            success=success,
            stages=all_results,
            total_duration=total_duration,
            total_tokens=total_tokens,
            events=list(self._events),
            dag_snapshot=self.dag.state_snapshot(),
        )

    def execute_stage(
        self, stage: StageNode, context: dict[str, Any],
    ) -> StageResult:
        """Run a single stage, handling critic-gated revision loops."""
        if stage.executor is None:
            return StageResult(success=False, error="No executor configured")

        critic = CriticActorLoop(
            max_revisions=stage.max_revisions,
            pass_threshold=stage.pass_threshold,
        ) if stage.is_critic_gated else None

        result = stage.executor(context)

        if critic is not None:
            while True:
                threshold = critic.adaptive_threshold(
                    stage.revision_count, stage.pass_threshold,
                )
                critic.pass_threshold = threshold
                verdict = critic.evaluate(result)

                if verdict.passed:
                    break
                if not critic.should_continue(
                    verdict.score, stage.revision_count,
                ):
                    break

                stage.revision_count += 1
                stage.status = StageStatus.REVISING
                self._emit(
                    stage.id,
                    EventType.REVISING,
                    f"Revision {stage.revision_count}: {verdict.feedback}",
                )
                context["_critic_feedback"] = verdict.feedback
                result = stage.executor(context)

        return result

    def status(self) -> dict[str, Any]:
        """Return the current pipeline state for UI consumption."""
        return self.dag.state_snapshot()

    def cancel(self) -> None:
        """Signal graceful cancellation of the running pipeline."""
        self._cancelled.set()

    # -- internals ----------------------------------------------------------

    def _finish_stage(self, stage_id: str, result: StageResult) -> None:
        self.dag.advance(stage_id, result)
        event_type = EventType.COMPLETED if result.success else EventType.FAILED
        self._emit(
            stage_id,
            event_type,
            f"Stage {'completed' if result.success else 'failed'}"
            f" (score={result.score:.2f})",
        )

    def _emit(
        self, stage_id: str, event_type: EventType, message: str,
        data: Optional[dict[str, Any]] = None,
    ) -> None:
        event = PipelineEvent(
            timestamp=datetime.now(timezone.utc),
            stage_id=stage_id,
            event_type=event_type,
            message=message,
            data=data or {},
        )
        with self._lock:
            self._events.append(event)
        self._event_callback(event)


# ---------------------------------------------------------------------------
# PHOENIX DAG builder
# ---------------------------------------------------------------------------

def _noop_executor(context: dict[str, Any]) -> StageResult:
    """Placeholder executor for stages without a configured callable."""
    return StageResult(success=True, score=1.0)


def build_phoenix_dag() -> PipelineDAG:
    """Construct the default PHOENIX pipeline DAG.

    Stages
    ------
    01  Complaint Operationalization       (no deps)
    02  Initial Observation Model           (01)
    03  Pseudodata Generation               (02)
    04a Readiness Check                     (03)
    04b Network Time-Series Analysis        (04a)
    04c Momentary Impact Quantification     (04b)
    05  Treatment Target Identification     (04c, 02)
    06  Updated Observation Model           (05)
    07  HAPA Digital Intervention           (06)
    08  Treatment Communication             (07)          SUPPORT
    09  Impact Visualization                (04c)         SUPPORT
    10  Research Reporting                  (07, 09)      SUPPORT
    """
    dag = PipelineDAG()

    stages = [
        StageNode("01", "Complaint Operationalization",
                  category=StageCategory.CORE, is_critic_gated=True,
                  executor=_noop_executor),
        StageNode("02", "Initial Observation Model",
                  dependencies=["01"], category=StageCategory.CORE,
                  is_critic_gated=True, executor=_noop_executor),
        StageNode("03", "Pseudodata Generation",
                  dependencies=["02"], category=StageCategory.CORE,
                  executor=_noop_executor),
        StageNode("04a", "Readiness Check",
                  dependencies=["03"], category=StageCategory.ANALYSIS,
                  is_critic_gated=True, executor=_noop_executor),
        StageNode("04b", "Network Time-Series Analysis",
                  dependencies=["04a"], category=StageCategory.ANALYSIS,
                  is_critic_gated=True, executor=_noop_executor),
        StageNode("04c", "Momentary Impact Quantification",
                  dependencies=["04b"], category=StageCategory.ANALYSIS,
                  is_critic_gated=True, executor=_noop_executor),
        StageNode("05", "Treatment Target Identification",
                  dependencies=["04c", "02"], category=StageCategory.CORE,
                  is_critic_gated=True, executor=_noop_executor),
        StageNode("06", "Updated Observation Model",
                  dependencies=["05"], category=StageCategory.CORE,
                  is_critic_gated=True, executor=_noop_executor),
        StageNode("07", "HAPA Digital Intervention",
                  dependencies=["06"], category=StageCategory.CORE,
                  is_critic_gated=True, executor=_noop_executor),
        StageNode("08", "Treatment Communication",
                  dependencies=["07"], category=StageCategory.SUPPORT,
                  executor=_noop_executor),
        StageNode("09", "Impact Visualization",
                  dependencies=["04c"], category=StageCategory.SUPPORT,
                  executor=_noop_executor),
        StageNode("10", "Research Reporting",
                  dependencies=["07", "09"], category=StageCategory.SUPPORT,
                  executor=_noop_executor),
    ]

    for stage in stages:
        dag.add_stage(stage)

    return dag


def format_pipeline_summary(result: PipelineResult) -> str:
    """Return a human-readable summary of a completed pipeline run."""
    lines: list[str] = []
    status_icon = "OK" if result.success else "FAIL"
    lines.append(f"Pipeline {status_icon}  ({result.total_duration:.1f}s)")
    lines.append("-" * 50)

    for sid, snap in sorted(result.dag_snapshot.items()):
        stage_res = result.stages.get(sid)
        score_str = f"{stage_res.score:.2f}" if stage_res else "-.--"
        rev = snap.get("revision_count", 0)
        rev_str = f" (rev {rev})" if rev else ""
        dur = snap.get("duration_seconds", 0.0)
        lines.append(
            f"  {sid:>4}  {snap['status']:<8}  score={score_str}"
            f"  {dur:>6.1f}s{rev_str}  {snap['name']}"
        )

    if result.total_tokens:
        lines.append("-" * 50)
        for key, val in sorted(result.total_tokens.items()):
            lines.append(f"  tokens.{key}: {val:,}")

    return "\n".join(lines)


# Pre-built DAG instance for convenience
PHOENIX_DAG: PipelineDAG = build_phoenix_dag()
