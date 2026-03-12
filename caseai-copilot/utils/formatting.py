"""
Output formatting utilities for CaseAI Copilot.
Provides Streamlit-friendly markdown formatters and safe JSON parsing.
"""
import json
import re
import logging
from typing import List, Union, Optional

from utils.logger import get_logger

_logger = get_logger("caseai.formatting")


# ---------------------------------------------------------------------------
# Severity badge helper
# ---------------------------------------------------------------------------

def severity_badge(severity: str) -> str:
    """
    Returns a colored emoji badge string for a given severity level.

    Severity levels:
        Critical -> black circle
        High     -> red circle
        Medium   -> yellow circle
        Low      -> green circle
        Info     -> blue circle
    """
    mapping = {
        "critical": "⚫ Critical",
        "high":     "🔴 High",
        "medium":   "🟡 Medium",
        "low":      "🟢 Low",
        "info":     "🔵 Info",
    }
    return mapping.get(severity.lower(), f"⬜ {severity}")


# ---------------------------------------------------------------------------
# Risk flags formatter
# ---------------------------------------------------------------------------

def format_risk_flags(risks: list) -> str:
    """
    Formats a list of risk flag dicts (or RiskFlag objects) into markdown.

    Expected keys per item: risk_name, severity, evidence, source, explanation
    """
    if not risks:
        return "_No risk flags identified for this case._"

    lines = ["### Risk Flags\n"]
    for i, risk in enumerate(risks, start=1):
        name = _get(risk, "risk_name", f"Risk {i}")
        severity = _get(risk, "severity", "Unknown")
        evidence = _get(risk, "evidence", "No evidence provided.")
        source = _get(risk, "source", "unknown")
        explanation = _get(risk, "explanation", "")

        badge = severity_badge(severity)
        lines.append(f"**{i}. {name}** {badge}")
        lines.append(f"> **Evidence:** {evidence}")
        if explanation:
            lines.append(f"> **Explanation:** {explanation}")
        lines.append(f"> **Source:** `{source}`")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Timeline formatter
# ---------------------------------------------------------------------------

def format_timeline(timeline: list) -> str:
    """
    Formats a list of timeline entry dicts (or TimelineEntry objects) into markdown.

    Expected keys per item: date, event, source, confidence
    """
    if not timeline:
        return "_No timeline events could be extracted for this case._"

    lines = ["### Case Timeline\n"]
    for entry in timeline:
        date = _get(entry, "date", "Unknown date")
        event = _get(entry, "event", "No description.")
        source = _get(entry, "source", "unknown")
        confidence = _get(entry, "confidence", "low")

        conf_icon = {"high": "✅", "medium": "⚠️", "low": "❓"}.get(
            confidence.lower(), "❓"
        )
        lines.append(f"**{date}** {conf_icon}")
        lines.append(f"- {event}")
        lines.append(f"  _(Source: `{source}` | Confidence: `{confidence}`)_")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Documentation gaps formatter
# ---------------------------------------------------------------------------

def format_gaps(gaps: list) -> str:
    """
    Formats a list of documentation gap dicts into markdown.

    Expected keys per item: gap_type, description, severity, recommendation
    """
    if not gaps:
        return "_No documentation or follow-up gaps identified for this case._"

    lines = ["### Documentation & Follow-up Gaps\n"]
    for i, gap in enumerate(gaps, start=1):
        gap_type = _get(gap, "gap_type", f"Gap {i}")
        description = _get(gap, "description", "No description.")
        severity = _get(gap, "severity", "Unknown")
        recommendation = _get(gap, "recommendation", "No recommendation provided.")

        badge = severity_badge(severity)
        lines.append(f"**{i}. {gap_type}** {badge}")
        lines.append(f"> {description}")
        lines.append(f"> **Recommendation:** {recommendation}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Validation observations formatter
# ---------------------------------------------------------------------------

def format_validation(observations: list) -> str:
    """
    Formats a list of validation observation dicts into markdown.

    Expected keys per item: observation, notes_suggest, data_shows, severity
    """
    if not observations:
        return "_No validation observations available. Ensure the case has both notes and structured data._"

    lines = ["### Data Validation Observations\n"]
    for i, obs in enumerate(observations, start=1):
        label = _get(obs, "observation", f"Observation {i}")
        notes_suggest = _get(obs, "notes_suggest", "Not documented in notes.")
        data_shows = _get(obs, "data_shows", "Not present in structured data.")
        severity = _get(obs, "severity", "Info")

        badge = severity_badge(severity)
        lines.append(f"**{i}. {label}** {badge}")
        lines.append(f"> **Notes say:** {notes_suggest}")
        lines.append(f"> **Data shows:** {data_shows}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Priority score formatter
# ---------------------------------------------------------------------------

def format_priority_score(score_obj) -> str:
    """
    Formats a PriorityScore object or dict into a markdown display string.
    """
    if score_obj is None:
        return "_Priority score has not been calculated._"

    score = _get(score_obj, "score", 0)
    urgency = _get(score_obj, "urgency_label", "Unknown")
    explanation = _get(score_obj, "explanation", "")
    factors = _get(score_obj, "factors", [])

    badge = severity_badge(urgency)
    lines = [
        f"### Priority Score: **{score}/100** {badge}",
        "",
    ]

    if explanation:
        lines.append(f"_{explanation}_")
        lines.append("")

    if factors:
        lines.append("**Contributing Factors:**")
        for f in factors:
            lines.append(f"- {f}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Safe JSON parser
# ---------------------------------------------------------------------------

def parse_ai_json(response_text: str) -> Union[list, dict]:
    """
    Safely parses JSON from an AI response string.

    Handles:
    - Raw JSON arrays or objects
    - JSON wrapped in markdown code fences (```json ... ``` or ``` ... ```)
    - Leading/trailing whitespace

    Returns:
        Parsed list or dict on success.
        Empty list on failure (with a logged warning).
    """
    if not response_text or not response_text.strip():
        _logger.warning("parse_ai_json: received empty response text; returning []")
        return []

    text = response_text.strip()

    # Strip markdown code fences if present
    # Handles ```json\n...\n``` or ```\n...\n```
    fenced = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```$", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()

    try:
        result = json.loads(text)
        return result
    except json.JSONDecodeError as exc:
        _logger.warning(
            f"parse_ai_json: JSON decode failed ({exc}). "
            f"Attempting to extract embedded JSON..."
        )

    # Attempt to find the first JSON array or object within the text
    # Try array first, then object
    for pattern in (r"(\[.*\])", r"(\{.*\})"):
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(1))
                _logger.info("parse_ai_json: successfully extracted embedded JSON.")
                return result
            except json.JSONDecodeError:
                continue

    _logger.warning(
        "parse_ai_json: could not parse JSON from AI response. Returning empty list. "
        f"Response preview: {text[:200]!r}"
    )
    return []


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _get(obj, key: str, default=None):
    """Safely get a value from a dict or dataclass-like object."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)
