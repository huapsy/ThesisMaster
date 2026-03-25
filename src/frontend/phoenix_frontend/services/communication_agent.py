from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _fallback_summary(stage: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
    if stage == "initial_model":
        criteria = int(evidence.get("criteria_count") or 0)
        predictors = int(evidence.get("predictor_count") or 0)
        line = (
            f"Initial model is available with {criteria} criteria and {predictors} predictors. "
            "Next PHOENIX step is data collection followed by readiness/network analysis."
        )
        return {
            "headline": "Initial model generated",
            "summary_markdown": line,
            "key_points": [
                f"Criteria selected: {criteria}",
                f"Predictors selected: {predictors}",
                "Proceed to data collection and then run the iterative cycle.",
            ],
            "risks": [],
            "recommended_next_actions": [
                "Review variable list and measurement prompts.",
                "Synthesize or upload time-series data.",
                "Run next PHOENIX cycle.",
            ],
        }

    readiness = evidence.get("readiness", {}) if isinstance(evidence.get("readiness"), dict) else {}
    impact = evidence.get("impact", {}) if isinstance(evidence.get("impact"), dict) else {}
    label = str(readiness.get("label") or readiness.get("readiness_label") or "unknown")
    score = readiness.get("score_0_100")
    if score is None:
        score = readiness.get("readiness_score_0_100")
    top_predictors = impact.get("top_predictors", []) if isinstance(impact.get("top_predictors"), list) else []
    predictor_names_list: List[str] = []
    for item in top_predictors[:4]:
        if isinstance(item, dict):
            predictor = str(item.get("predictor") or "").strip()
            if predictor:
                predictor_names_list.append(predictor)
        else:
            text = str(item).strip()
            if text:
                predictor_names_list.append(text)
    predictor_names = ", ".join(predictor_names_list) if predictor_names_list else "none identified"
    line = (
        f"Cycle completed with readiness {label} (score={score}). "
        f"Highest impact predictors: {predictor_names}."
    )
    return {
        "headline": "Cycle analysis summary",
        "summary_markdown": line,
        "key_points": [
            f"Readiness label: {label}",
            f"Top predictors: {predictor_names}",
            "Updated model and HAPA intervention artifacts were generated.",
        ],
        "risks": [],
        "recommended_next_actions": [
            "Inspect step-level diagnostics and visualizations.",
            "Review selected barriers and coping strategies.",
            "Collect next data window and iterate.",
        ],
    }


def _resolve_provider_config() -> tuple[str, str, str]:
    openrouter_api_key = str(os.environ.get("OPENROUTER_API_KEY") or "").strip()
    openai_api_key = str(os.environ.get("OPENAI_API_KEY") or "").strip()
    openai_base_url = str(os.environ.get("OPENAI_BASE_URL") or "").strip()
    if openrouter_api_key:
        return openrouter_api_key, (openai_base_url or "https://openrouter.ai/api/v1"), "openrouter_responses_api"
    if openai_api_key:
        return openai_api_key, openai_base_url, "openai_responses_api"
    return "", "", ""


def _resolve_model(provider: str, model: str) -> str:
    token = str(model).strip() or "gpt-5-nano"
    if provider == "openrouter_responses_api" and "/" not in token and token.startswith("gpt-"):
        return f"openai/{token}"
    return token


def _extract_response_text(resp: Any) -> str:
    text = getattr(resp, "output_text", "") or ""
    if text:
        return str(text).strip()
    chunks: List[str] = []
    try:
        for item in getattr(resp, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                if getattr(content, "type", None) == "output_text":
                    chunks.append(str(getattr(content, "text", "")))
    except Exception:
        return ""
    return "".join(chunks).strip()


def generate_communication_summary(
    *,
    stage: str,
    evidence: Dict[str, Any],
    llm_model: str = "gpt-5-nano",
    disable_llm: bool = False,
) -> Dict[str, Any]:
    payload = {
        "generated_at": _now(),
        "stage": stage,
        "llm_enabled": bool(not disable_llm),
        "llm_model": llm_model,
        "summary": {},
        "llm_error": "",
    }
    if disable_llm:
        payload["summary"] = _fallback_summary(stage, evidence)
        payload["llm_enabled"] = False
        return payload

    api_key, base_url, provider = _resolve_provider_config()
    if not api_key:
        payload["summary"] = _fallback_summary(stage, evidence)
        payload["llm_enabled"] = False
        payload["llm_error"] = "OPENROUTER_API_KEY missing (fallback OPENAI_API_KEY also not set)."
        return payload

    system_prompt = (
        "You are the PHOENIX communication agent inside a multi-agent engine. "
        "Summarize outputs clearly for researchers and users. Be precise, non-diagnostic, and action-oriented."
    )
    user_prompt = (
        "Return strict JSON with keys:\n"
        "{\n"
        '  "headline": string,\n'
        '  "summary_markdown": string,\n'
        '  "key_points": [string],\n'
        '  "risks": [string],\n'
        '  "recommended_next_actions": [string]\n'
        "}\n\n"
        f"stage={stage}\n"
        "evidence_json:\n"
        f"{json.dumps(evidence, ensure_ascii=False, indent=2)}"
    )

    try:
        from openai import OpenAI  # type: ignore

        kwargs: Dict[str, Any] = {"api_key": api_key}
        if str(base_url).strip():
            kwargs["base_url"] = str(base_url).strip()
        client = OpenAI(**kwargs)
        resolved_model = _resolve_model(provider, llm_model)
        create_kwargs = {
            "model": resolved_model,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        try:
            resp = client.responses.create(
                **create_kwargs,
                text={"format": {"type": "json_object"}},
            )
        except TypeError:
            resp = client.responses.create(
                **create_kwargs,
            )
        text = _extract_response_text(resp)
        parsed = json.loads(text)
        payload["summary"] = {
            "headline": str(parsed.get("headline") or ""),
            "summary_markdown": str(parsed.get("summary_markdown") or ""),
            "key_points": [str(item) for item in (parsed.get("key_points") or [])[:8]],
            "risks": [str(item) for item in (parsed.get("risks") or [])[:8]],
            "recommended_next_actions": [str(item) for item in (parsed.get("recommended_next_actions") or [])[:8]],
        }
        payload["provider"] = provider
        payload["llm_model"] = resolved_model
        return payload
    except Exception as exc:
        payload["summary"] = _fallback_summary(stage, evidence)
        payload["llm_enabled"] = False
        payload["llm_error"] = f"{type(exc).__name__}: {exc}"
        return payload
