"""
Risk detection service for CaseAI Copilot.
Uses AI to identify operational and care coordination risk flags.
"""
from typing import List

from models.schemas import CaseContext, RiskFlag
from models.dto import metadata_to_text, notes_to_text, visits_to_text, activity_to_text, medication_to_text
from config.prompts import SYSTEM_PROMPT_BASE, build_risk_prompt
from services.ai_service import AIService
from utils.logger import get_logger
from utils.helpers import safe_get

_logger = get_logger("caseai.risk_service")

_VALID_SEVERITIES = {"Low", "Medium", "High"}
_VALID_SOURCES = {"notes", "structured", "both"}


class RiskService:
    """
    Service for detecting risk flags in a case using AI analysis.
    """

    def __init__(self, ai_service: AIService):
        """
        Initialize RiskService.

        Args:
            ai_service: An initialized AIService instance.
        """
        self.ai_service = ai_service

    def detect_risks(self, context: CaseContext) -> List[RiskFlag]:
        """
        Analyze a case and return a list of identified risk flags.

        Args:
            context: The full CaseContext to analyze.

        Returns:
            List of RiskFlag objects. Returns empty list on failure.
        """
        try:
            metadata_text = metadata_to_text(context.case_metadata)
            notes_text = notes_to_text(context.notes)
            structured_text = (
                "=== VISITS ===\n" + visits_to_text(context.visits) + "\n\n"
                "=== ACTIVITIES ===\n" + activity_to_text(context.activities) + "\n\n"
                "=== MEDICATIONS ===\n" + medication_to_text(context.medication_events)
            )

            user_prompt = build_risk_prompt(metadata_text, notes_text, structured_text)

            raw_data = self.ai_service.call_claude_for_json(
                system_prompt=SYSTEM_PROMPT_BASE,
                user_prompt=user_prompt,
                feature_name="risk_detection",
            )

            if not isinstance(raw_data, list):
                _logger.warning(
                    f"RiskService.detect_risks: expected list, got {type(raw_data)}. "
                    "Wrapping in list."
                )
                raw_data = [raw_data] if isinstance(raw_data, dict) else []

            risk_flags = self._parse_risk_flags(raw_data)
            _logger.info(
                f"RiskService.detect_risks: identified {len(risk_flags)} risk flags "
                f"for case {context.case_metadata.case_id}."
            )
            return risk_flags

        except Exception as exc:
            _logger.error(
                f"RiskService.detect_risks: failed for case "
                f"{context.case_metadata.case_id}: {exc}"
            )
            return []

    def _parse_risk_flags(self, raw_data: list) -> List[RiskFlag]:
        """
        Convert a list of raw dicts into RiskFlag objects.
        Uses safe access patterns to handle missing or malformed fields.

        Args:
            raw_data: List of dicts from AI JSON response.

        Returns:
            List of RiskFlag objects.
        """
        flags = []
        for i, item in enumerate(raw_data):
            if not isinstance(item, dict):
                _logger.warning(
                    f"RiskService._parse_risk_flags: item {i} is not a dict, skipping."
                )
                continue

            severity = safe_get(item, "severity", default="Medium")
            if severity not in _VALID_SEVERITIES:
                _logger.warning(
                    f"RiskService._parse_risk_flags: invalid severity '{severity}' "
                    f"at item {i}, defaulting to 'Medium'."
                )
                severity = "Medium"

            source = safe_get(item, "source", default="notes")
            if source not in _VALID_SOURCES:
                source = "notes"

            flags.append(
                RiskFlag(
                    risk_name=safe_get(item, "risk_name", default=f"Risk {i + 1}"),
                    severity=severity,
                    evidence=safe_get(item, "evidence", default="No evidence documented."),
                    source=source,
                    explanation=safe_get(item, "explanation", default=""),
                )
            )

        return flags
