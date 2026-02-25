#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def log(message: str) -> None:
    print(f"[{_ts()}] {message}", flush=True)


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _safe_read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    for sep in [",", ";", "\t", "|"]:
        try:
            frame = pd.read_csv(path, sep=sep, engine="python")
            if frame.shape[1] > 1 or sep == ",":
                return frame
        except Exception:
            continue
    return pd.read_csv(path, engine="python")


def _discover_profiles(
    *,
    handoff_root: Path,
    intervention_root: Path,
    impact_root: Path,
    pattern: str,
    max_profiles: int,
) -> List[str]:
    discovered: set[str] = set()
    for root in [handoff_root, intervention_root, impact_root]:
        if not root.exists():
            continue
        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            pid = child.name
            if pattern and pattern not in pid:
                continue
            discovered.add(pid)
    ordered = sorted(discovered)
    if max_profiles > 0:
        ordered = ordered[:max_profiles]
    return ordered


def _build_summary_payload(
    *,
    profile_id: str,
    step03: Dict[str, Any],
    step04: Dict[str, Any],
    step05: Dict[str, Any],
    impact_df: pd.DataFrame,
) -> Dict[str, Any]:
    top_predictors: List[str] = []
    if not impact_df.empty:
        score_col = "predictor_impact"
        if score_col not in impact_df.columns and "predictor_impact_pct" in impact_df.columns:
            score_col = "predictor_impact_pct"
        if score_col in impact_df.columns:
            local = impact_df.copy()
            local["_score"] = pd.to_numeric(local[score_col], errors="coerce").fillna(0.0)
            local = local.sort_values("_score", ascending=False).head(5)
            for _, row in local.iterrows():
                pid = str(row.get("predictor") or row.get("predictor_id") or "").strip()
                if pid:
                    top_predictors.append(pid)

    step03_targets = step03.get("recommended_targets") or []
    if isinstance(step03_targets, list):
        step03_targets = [row for row in step03_targets if isinstance(row, dict)]
    else:
        step03_targets = []
    top_targets: List[str] = []
    for row in step03_targets[:5]:
        p = str(row.get("predictor") or "").strip()
        if p:
            top_targets.append(p)

    updated_predictors = [
        str(x).strip() for x in (step04.get("recommended_next_observation_predictors") or [])
        if str(x).strip()
    ]
    selected_barriers = [
        str(row.get("barrier_name") or "").strip()
        for row in (step05.get("selected_barriers") or [])
        if isinstance(row, dict) and str(row.get("barrier_name") or "").strip()
    ]
    selected_coping = [
        str(row.get("coping_name") or "").strip()
        for row in (step05.get("selected_coping_strategies") or [])
        if isinstance(row, dict) and str(row.get("coping_name") or "").strip()
    ]

    readiness_hint = "impact-constrained"
    if step05:
        readiness_hint = "full-step05"
    elif step04:
        readiness_hint = "step04-only"

    key_points: List[str] = []
    key_points.append(f"Profile: {profile_id}")
    key_points.append(f"Top impact predictors: {', '.join(top_predictors) if top_predictors else 'none'}")
    key_points.append(f"Step-03 targets: {', '.join(top_targets) if top_targets else 'none'}")
    key_points.append(
        f"Step-04 updated predictors ({len(updated_predictors)}): "
        f"{', '.join(updated_predictors[:6]) if updated_predictors else 'none'}"
    )
    key_points.append(f"Step-05 barriers ({len(selected_barriers)}): {', '.join(selected_barriers[:5]) if selected_barriers else 'none'}")
    key_points.append(f"Step-05 coping ({len(selected_coping)}): {', '.join(selected_coping[:5]) if selected_coping else 'none'}")

    next_actions = [
        "Review Step-04 predictor updates before next acquisition window.",
        "Confirm Step-05 barriers/coping strategy feasibility with participant context.",
        "Run next cycle after collecting fresh data for updated predictors.",
    ]

    risks: List[str] = []
    if not top_predictors:
        risks.append("Impact stage produced no ranked predictors.")
    if not updated_predictors:
        risks.append("Updated observation model predictors are empty.")
    if not step05:
        risks.append("Intervention translation was skipped or unavailable.")

    summary_line = (
        "Treatment translation completed with "
        f"{len(updated_predictors)} updated predictors and {len(selected_barriers)} selected barriers "
        f"(mode={readiness_hint})."
    )

    return {
        "contract_version": "1.0.0",
        "generated_at": _now_iso(),
        "stage": "translation_communication",
        "profile_id": profile_id,
        "summary": {
            "headline": f"Treatment translation summary for {profile_id}",
            "summary_markdown": summary_line,
            "key_points": key_points,
            "risks": risks,
            "recommended_next_actions": next_actions,
        },
        "evidence_status": {
            "step03_target_identification": bool(step03),
            "step04_updated_observation_model": bool(step04),
            "step05_digital_intervention": bool(step05),
            "impact_rankings": bool(top_predictors),
        },
        "counts": {
            "top_impact_predictors": len(top_predictors),
            "step03_targets": len(top_targets),
            "step04_updated_predictors": len(updated_predictors),
            "step05_barriers": len(selected_barriers),
            "step05_coping": len(selected_coping),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate final treatment-translation communication summaries.")
    parser.add_argument("--handoff-root", type=str, required=True)
    parser.add_argument("--intervention-root", type=str, required=True)
    parser.add_argument("--impact-root", type=str, required=True)
    parser.add_argument("--output-root", type=str, required=True)
    parser.add_argument("--pattern", type=str, default="")
    parser.add_argument("--max-profiles", type=int, default=0)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--llm-model", type=str, default="gpt-5-nano")
    parser.add_argument("--disable-llm", action=argparse.BooleanOptionalAction, default=False)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    handoff_root = Path(args.handoff_root).expanduser().resolve()
    intervention_root = Path(args.intervention_root).expanduser().resolve()
    impact_root = Path(args.impact_root).expanduser().resolve()
    output_root = _ensure_dir(Path(args.output_root).expanduser().resolve())

    profiles = _discover_profiles(
        handoff_root=handoff_root,
        intervention_root=intervention_root,
        impact_root=impact_root,
        pattern=str(args.pattern).strip(),
        max_profiles=int(args.max_profiles),
    )
    if not profiles:
        log("translation_communication.no_profiles: nothing to summarize.")
        run_summary = {
            "generated_at": _now_iso(),
            "profile_count": 0,
            "profiles": [],
            "status": "empty",
        }
        (output_root / "translation_communication_run_summary.json").write_text(
            json.dumps(run_summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return 0

    log(
        "translation_communication.start: "
        f"profiles={len(profiles)} max_workers={max(1, int(args.max_workers))} llm={bool(not args.disable_llm)} model={args.llm_model}"
    )

    rows: List[Dict[str, Any]] = []

    def _run_profile(profile_id: str) -> Dict[str, Any]:
        step03 = _safe_read_json(handoff_root / profile_id / "step03_target_selection.json")
        step04 = _safe_read_json(handoff_root / profile_id / "step04_updated_observation_model.json")
        step05 = _safe_read_json(intervention_root / profile_id / "step05_hapa_intervention.json")
        impact_df = _safe_read_csv(impact_root / profile_id / "predictor_composite.csv")

        payload = _build_summary_payload(
            profile_id=profile_id,
            step03=step03,
            step04=step04,
            step05=step05,
            impact_df=impact_df,
        )
        profile_out = _ensure_dir(output_root / profile_id)
        target_json = profile_out / "treatment_translation_communication.json"
        target_md = profile_out / "treatment_translation_communication.md"
        target_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
        md_lines = [
            f"# {summary.get('headline', 'Treatment Translation Summary')}",
            "",
            str(summary.get("summary_markdown") or ""),
            "",
            "## Key Points",
        ]
        for item in summary.get("key_points") or []:
            md_lines.append(f"- {item}")
        md_lines.extend(["", "## Risks"])
        risks = summary.get("risks") or []
        if risks:
            for item in risks:
                md_lines.append(f"- {item}")
        else:
            md_lines.append("- None reported.")
        md_lines.extend(["", "## Recommended Next Actions"])
        for item in summary.get("recommended_next_actions") or []:
            md_lines.append(f"- {item}")
        target_md.write_text("\n".join(md_lines).strip() + "\n", encoding="utf-8")

        log(f"translation_communication.profile_done: profile={profile_id}")
        return {
            "profile_id": profile_id,
            "json": str(target_json),
            "markdown": str(target_md),
            "counts": payload.get("counts", {}),
        }

    with ThreadPoolExecutor(max_workers=max(1, int(args.max_workers))) as pool:
        futures = {pool.submit(_run_profile, pid): pid for pid in profiles}
        for future in as_completed(futures):
            rows.append(future.result())

    rows = sorted(rows, key=lambda row: str(row.get("profile_id") or ""))
    run_summary = {
        "generated_at": _now_iso(),
        "profile_count": len(rows),
        "profiles": rows,
        "status": "ok",
        "llm_enabled": bool(not args.disable_llm),
        "llm_model": str(args.llm_model),
    }
    (output_root / "translation_communication_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    log("translation_communication.done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
