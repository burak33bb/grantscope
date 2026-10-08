# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
import typing

from genlayer import *

EVIDENCE_READY = "EVIDENCE_READY"
NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"
CATEGORY_RISK = "CATEGORY_RISK"
WEAK_PROOF = "WEAK_PROOF"
VALID_RESULTS = [EVIDENCE_READY, NEEDS_MORE_EVIDENCE, CATEGORY_RISK, WEAK_PROOF]
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

        report = _build_readiness_report(
            category,
            summary,
            github_url,
            contract_url,
            demo_url,
            website_url,
            proof_score,
        )

        if proof_score < 3 and report["result"] == EVIDENCE_READY:
            raise ValueError("EVIDENCE_READY requires stronger deterministic proof coverage.")
        if category == "PROJECT" and not website_url and report["result"] == EVIDENCE_READY:
            raise ValueError("EVIDENCE_READY project requires a website.")
        if contract_url and "explorer-studio.genlayer.com/address/" not in contract_url:
            if report["result"] == EVIDENCE_READY:
                raise ValueError("EVIDENCE_READY requires a GenLayer explorer contract URL.")

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
            "scope": "Evidence checklist only; external page contents are not fetched or authenticated.",
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


def _build_readiness_report(
    category: str,
    summary: str,
    github_url: str,
    contract_url: str,
    demo_url: str,
    website_url: str,
    proof_score: int,
) -> dict:
    missing = []
    score = 0

    if _looks_like_url(github_url) and "github.com" in github_url.lower():
        score += 25
    else:
        missing.append("github repository")

    if _looks_like_url(contract_url) and "explorer-studio.genlayer.com/address/" in contract_url:
        score += 30
    else:
        missing.append("genlayer explorer contract")

    if category == "PROJECT":
        if _looks_like_url(website_url):
            score += 25
        else:
            missing.append("project website")
    elif _looks_like_url(website_url):
        score += 10

    if _looks_like_url(demo_url):
        score += 15
    else:
        missing.append("working demo video")

    if len(summary) >= 90:
        score += 5

    if proof_score < 2:
        result = WEAK_PROOF
        reason = "Too few usable proof links were provided."
    elif category == "PROJECT" and not _looks_like_url(website_url):
        result = CATEGORY_RISK
        reason = "Project submissions need a live app URL."
    elif "explorer-studio.genlayer.com/address/" not in contract_url:
        result = WEAK_PROOF
        reason = "The contract proof is not a GenLayer explorer address."
    elif score >= 75:
        result = EVIDENCE_READY
        reason = "Required evidence links are present and formatted for steward review."
    else:
        result = NEEDS_MORE_EVIDENCE
        reason = "The submission is understandable but still needs stronger review evidence."

    if not missing:
        missing = ["none"]

    return {
        "result": result,
        "score": score,
        "missing": missing,
        "reason": reason,
        "scope": "Checks link presence and format only; it does not verify external page contents.",
    }


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
