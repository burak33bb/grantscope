# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
import typing

from genlayer import *

READY = "READY"
NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"
CATEGORY_RISK = "CATEGORY_RISK"
WEAK_PROOF = "WEAK_PROOF"
VALID_RESULTS = [READY, NEEDS_MORE_EVIDENCE, CATEGORY_RISK, WEAK_PROOF]
VALID_CATEGORIES = ["PROJECT", "INTELLIGENT_CONTRACT", "MILESTONE"]


class GrantScopeVerifier(gl.Contract):
    latest_report: str
    report_count: u256

    def __init__(self):
        self.latest_report = ""
        self.report_count = u256(0)

    @gl.public.write
    def review_submission(
        self,
        category: str,
        project_name: str,
        summary: str,
        github_url: str,
        contract_url: str,
        demo_url: str,
        website_url: str,
    ) -> typing.Any:
        category = category.strip().upper()
        project_name = project_name.strip()
        summary = summary.strip()
        github_url = github_url.strip()
        contract_url = contract_url.strip()
        demo_url = demo_url.strip()
        website_url = website_url.strip()
        _validate_inputs(
            category,
            project_name,
            summary,
            github_url,
            contract_url,
            demo_url,
            website_url,
        )

        proof_score = _proof_score(github_url, contract_url, demo_url, website_url)

        result = gl.exec_prompt(f"""
Review this GenLayer submission for readiness.

Category: {category}
Project: {project_name}
Summary: {summary}
GitHub: {github_url}
Contract: {contract_url}
Demo: {demo_url}
Website: {website_url}

Return only JSON:
{{
  "result": "READY | NEEDS_MORE_EVIDENCE | CATEGORY_RISK | WEAK_PROOF",
  "score": 0,
  "missing": ["short missing item"],
  "reason": "short practical reason"
}}

Rules:
- READY means category, source, contract proof, and demo evidence are enough to review.
- NEEDS_MORE_EVIDENCE means useful proof is missing.
- CATEGORY_RISK means the category appears mismatched.
- WEAK_PROOF means links exist but do not clearly prove GenLayer usage.
- score must be an integer from 0 to 100.
            """)
        report = _parse_json_dict(result)
        _validate_report(report)

        if proof_score < 3 and report["result"] == READY:
            raise ValueError("READY requires stronger deterministic proof coverage.")
        if category == "PROJECT" and not website_url and report["result"] == READY:
            raise ValueError("READY project requires a website.")
        if contract_url and "explorer-studio.genlayer.com/address/" not in contract_url:
            if report["result"] == READY:
                raise ValueError("READY requires a GenLayer explorer contract URL.")

        next_count = int(self.report_count) + 1
        record = {
            "id": next_count,
            "category": category,
            "project_name": project_name,
            "proof_score": proof_score,
            "github_url": github_url,
            "contract_url": contract_url,
            "demo_url": demo_url,
            "website_url": website_url,
            "report": report,
        }
        self.latest_report = _canonical_json(record)
        self.report_count = u256(next_count)
        return record

    @gl.public.view
    def get_latest_report(self) -> typing.Any:
        if not self.latest_report:
            return {}
        return json.loads(self.latest_report)

    @gl.public.view
    def get_report_count(self) -> int:
        return int(self.report_count)

    @gl.public.view
    def get_report(self, report_id: int) -> typing.Any:
        if report_id != int(self.report_count) or not self.latest_report:
            raise ValueError("Only the latest report is stored.")
        return json.loads(self.latest_report)


def _validate_inputs(
    category: str,
    project_name: str,
    summary: str,
    github_url: str,
    contract_url: str,
    demo_url: str,
    website_url: str,
) -> None:
    if category not in VALID_CATEGORIES:
        raise ValueError("Invalid category.")
    if len(project_name) < 3:
        raise ValueError("Project name is too short.")
    if len(summary) < 40:
        raise ValueError("Summary is too short.")
    if not _looks_like_url(github_url) or "github.com" not in github_url.lower():
        raise ValueError("GitHub repository is required.")
    if category == "PROJECT" and not _looks_like_url(website_url):
        raise ValueError("Project submissions require a website URL.")
    if not _looks_like_url(contract_url):
        raise ValueError("GenLayer contract URL is required.")
    if demo_url and not _looks_like_url(demo_url):
        raise ValueError("Demo URL is invalid.")


def _validate_report(value: dict) -> None:
    if value.get("result") not in VALID_RESULTS:
        raise ValueError("Invalid readiness result.")
    score = value.get("score")
    if not isinstance(score, int) or score < 0 or score > 100:
        raise ValueError("Invalid score.")
    if not isinstance(value.get("missing"), list):
        raise ValueError("Missing must be a list.")
    if not isinstance(value.get("reason"), str) or not value.get("reason").strip():
        raise ValueError("Reason is required.")


def _proof_score(
    github_url: str,
    contract_url: str,
    demo_url: str,
    website_url: str,
) -> int:
    score = 0
    for url in [github_url, contract_url, demo_url, website_url]:
        if _looks_like_url(url):
            score += 1
    return score


def _looks_like_url(value: str) -> bool:
    return value.startswith("https://") and "." in value


def _parse_json_dict(json_str: str) -> dict:
    first_brace = json_str.find("{")
    last_brace = json_str.rfind("}")
    if first_brace == -1 or last_brace == -1 or last_brace < first_brace:
        raise ValueError("No JSON object found.")
    return json.loads(json_str[first_brace : last_brace + 1])


def _canonical_json(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))
