from __future__ import annotations


def test_pipeline_cli_accepts_frontend_root_overrides(module_loader, repo_root):
    module = module_loader(
        str(repo_root / "evaluation/integrated_pipeline/run_engine_pipeline.py"),
        "pipeline_cli_override_test_module",
    )

    args = module.parse_args(
        [
            "--initial-model-runs-root",
            "/tmp/custom_model_runs",
            "--free-text-root",
            "/tmp/custom_free_text",
        ]
    )
    assert args.initial_model_runs_root == "/tmp/custom_model_runs"
    assert args.free_text_root == "/tmp/custom_free_text"


def test_pipeline_cli_accepts_disable_llm_alias(module_loader, repo_root):
    module = module_loader(
        str(repo_root / "evaluation/integrated_pipeline/run_engine_pipeline.py"),
        "pipeline_cli_override_disable_llm_test_module",
    )
    args = module.parse_args(["--disable_LLM"])
    assert args.disable_llm is True


def test_pipeline_cli_accepts_parallel_branch_toggle(module_loader, repo_root):
    module = module_loader(
        str(repo_root / "evaluation/integrated_pipeline/run_engine_pipeline.py"),
        "pipeline_cli_parallel_branch_toggle_test_module",
    )
    args = module.parse_args(["--no-parallel-branches"])
    assert args.parallel_branches is False


def test_pipeline_cli_accepts_treatment_communication_toggle(module_loader, repo_root):
    module = module_loader(
        str(repo_root / "evaluation/integrated_pipeline/run_engine_pipeline.py"),
        "pipeline_cli_treatment_comm_toggle_test_module",
    )
    args = module.parse_args(["--no-run-treatment-communication"])
    assert args.run_treatment_communication is False


def test_pipeline_cli_accepts_llm_health_check_toggles(module_loader, repo_root):
    module = module_loader(
        str(repo_root / "evaluation/integrated_pipeline/run_engine_pipeline.py"),
        "pipeline_cli_llm_health_toggle_test_module",
    )
    args = module.parse_args(
        [
            "--no-startup-llm-health-check",
            "--fail-on-llm-health-check",
            "--llm-health-model",
            "openai/gpt-5-nano",
            "--llm-health-timeout-seconds",
            "9.5",
        ]
    )
    assert args.startup_llm_health_check is False
    assert args.fail_on_llm_health_check is True
    assert args.llm_health_model == "openai/gpt-5-nano"
    assert args.llm_health_timeout_seconds == 9.5


def test_launcher_cli_accepts_disable_llm_alias(module_loader, repo_root):
    module = module_loader(
        str(repo_root / "evaluation/integrated_pipeline/run_pipeline.py"),
        "pipeline_launcher_disable_llm_alias_test_module",
    )
    args, passthrough = module.parse_args(["--disable_LLM", "--mode", "synthetic_v1"])
    assert args.disable_llm is True
    assert passthrough == []
