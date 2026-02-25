from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _mod(module_loader, repo_file_fn):
    return module_loader(
        str(repo_file_fn("evaluation/integrated_pipeline/run_engine_pipeline.py")),
        "phoenix_pipeline_module",
    )


def test_discover_profiles_filters_and_limits(tmp_path: Path, module_loader, repo_file_fn) -> None:
    module = _mod(module_loader, repo_file_fn)
    root = tmp_path / "pseudodata"
    (root / "pseudoprofile_A").mkdir(parents=True)
    (root / "pseudoprofile_A" / "pseudodata_wide.csv").write_text("t,P01,C01\n1,1,1\n", encoding="utf-8")
    (root / "pseudoprofile_B").mkdir(parents=True)
    (root / "pseudoprofile_B" / "pseudodata_wide.csv").write_text("t,P01,C01\n1,1,1\n", encoding="utf-8")

    profiles = module.discover_profiles(
        pseudodata_root=root,
        filename="pseudodata_wide.csv",
        pattern="pseudoprofile_A",
        max_profiles=10,
    )
    assert profiles == ["pseudoprofile_A"]

    profiles_limited = module.discover_profiles(
        pseudodata_root=root,
        filename="pseudodata_wide.csv",
        pattern="pseudoprofile_",
        max_profiles=1,
    )
    assert len(profiles_limited) == 1


def test_validate_root_outputs_success(tmp_path: Path, module_loader, repo_file_fn) -> None:
    module = _mod(module_loader, repo_file_fn)
    root = tmp_path / "report"
    root.mkdir(parents=True)
    (root / "run_report.md").write_text("# ok\n", encoding="utf-8")
    (root / "run_report.json").write_text("{}", encoding="utf-8")
    logger = module.PipelineLogger(tmp_path / "logs" / "pipeline.jsonl")

    module.validate_root_outputs(
        stage_name="reporting",
        root=root,
        required_relpaths=["run_report.md", "run_report.json"],
        logger=logger,
    )


def test_apply_openrouter_env_compat_overrides_legacy_openai_key(
    module_loader,
    repo_file_fn,
    monkeypatch,
) -> None:
    module = _mod(module_loader, repo_file_fn)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-old-openai-key")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    details = module._apply_openrouter_env_compat()
    assert details["provider"] == "openrouter"
    assert details["openai_key_set"] is True
    assert details["openai_base_url"] == "https://openrouter.ai/api/v1"
    assert module.os.environ.get("OPENAI_API_KEY") == "sk-or-v1-test"


def test_build_runtime_env_prefers_openrouter_key(module_loader, repo_file_fn, monkeypatch, tmp_path: Path) -> None:
    module = _mod(module_loader, repo_file_fn)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-legacy-test")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    env = module._build_runtime_env(tmp_path / "run")
    assert env["OPENROUTER_API_KEY"] == "sk-or-v1-test"
    assert env["OPENAI_API_KEY"] == "sk-or-v1-test"
    assert env["OPENAI_BASE_URL"] == "https://openrouter.ai/api/v1"


def test_startup_llm_health_check_missing_key(module_loader, repo_file_fn, monkeypatch) -> None:
    module = _mod(module_loader, repo_file_fn)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    result = module._run_startup_llm_health_check(model="gpt-5-nano", timeout_seconds=1.0)
    assert result["ok"] is False
    assert result["reason"] == "missing_api_key"
