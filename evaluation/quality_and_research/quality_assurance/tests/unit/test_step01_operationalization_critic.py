from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def _load_step01_module(repo_root, module_loader):
    target = (
        repo_root
        / "src/backend/SystemComponents/Agentic_Framework/01_OperationalizationMentalHealthProblem/utils/02_operationalize_freetext_complaints.py"
    )
    return module_loader(str(target), "phoenix_step01_operationalization_runtime")


def test_step01_local_critic_prefers_llm_review(repo_root, module_loader, monkeypatch):
    module = _load_step01_module(repo_root, module_loader)
    llm_review = module.DecompositionCriticReview(
        decision="PASS",
        composite_score_0_1=0.91,
        pass_threshold_0_1=0.78,
        dimension_scores={
            "schema_validity": 0.9,
            "coverage_grounding": 0.9,
            "atomicity_nonoverlap": 0.9,
            "granularity_fit": 0.9,
            "current_actionability": 0.9,
        },
        complaint_structure={"segments": ["sleep", "fog"]},
        issues=[],
        actionable_feedback=[],
        rationale="Structured LLM critic accepted the decomposition.",
        critic_mode="llm_structured",
        critic_trace={"provider": "test"},
    )

    monkeypatch.setattr(
        module,
        "run_llm_decomposition_critic",
        lambda complaint, decomposition, structure: (llm_review, {"provider": "test"}),
    )

    def _unexpected_fallback(*args, **kwargs):  # noqa: ANN001
        raise AssertionError("Heuristic fallback should not run when the LLM critic succeeds.")

    monkeypatch.setattr(module, "_run_heuristic_decomposition_critic", _unexpected_fallback)

    result = module.run_local_decomposition_critic(
        "I feel exhausted and mentally foggy most mornings.",
        {"variables": [{"id": "C01", "label": "Fatigue"}]},
    )

    assert result.decision == "PASS"
    assert result.critic_mode == "llm_structured"
    assert result.critic_trace == {"provider": "test"}


def test_step01_local_critic_falls_back_when_llm_review_fails(repo_root, module_loader, monkeypatch):
    module = _load_step01_module(repo_root, module_loader)
    fallback_review = module.DecompositionCriticReview(
        decision="REVISE",
        composite_score_0_1=0.42,
        pass_threshold_0_1=0.78,
        dimension_scores={
            "schema_validity": 0.5,
            "coverage_grounding": 0.4,
            "atomicity_nonoverlap": 0.5,
            "granularity_fit": 0.3,
            "current_actionability": 0.4,
        },
        complaint_structure={"segments": ["panic", "escape"]},
        issues=["Coverage is incomplete."],
        actionable_feedback=["Split the panic state from the safety behaviour."],
        rationale="Heuristic fallback critic requested revision.",
        critic_mode="heuristic_fallback",
        critic_trace=None,
    )

    monkeypatch.setattr(
        module,
        "run_llm_decomposition_critic",
        lambda complaint, decomposition, structure: (None, {"failure_reason": "mock_transport_error"}),
    )
    monkeypatch.setattr(
        module,
        "_run_heuristic_decomposition_critic",
        lambda complaint, decomposition, structure=None: fallback_review,
    )

    result = module.run_local_decomposition_critic(
        "My chest tightens, I check exits, and I plan how to escape.",
        {"variables": [{"id": "C01", "label": "panic state"}]},
    )

    assert result.decision == "REVISE"
    assert result.critic_mode == "heuristic_fallback"
    assert result.critic_trace == {"failure_reason": "mock_transport_error"}
    assert any("LLM critic fallback activated" in issue for issue in result.issues)
