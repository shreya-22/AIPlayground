"""
Validation service for CaseAI Copilot.
Cross-checks clinical notes against structured data to identify discrepancies.
"""
from typing import List

from models.schemas import CaseContext, ValidationObservation
from models.dto import metadata_to_text, notes_to_text, visits_to_text, activity_to_text, medication_to_text
from config.prompts import SYSTEM_PROMPT_BASE, build_validation_prompt
from services.ai_service import AIService
from utils.logger import get_logger
from utils.helpers import safe_get

_logger = get_logger("caseai.validation_service")

_VALID_SEVERITIES = {"Info", "Low", "Medium", "High"}


class ValidationService:
    """
    Service for performing cross-validation between notes and structured data.
    Identifies discrepancies, confirmations, and documentation gaps.
    """

    def __init__(self, ai_service: AIService):
        """
        Initialize ValidationService.

        Args:
            ai_service: An initialized AIService instance.
        """
        self.ai_service = ai_service

    def run_validation(self, context: CaseContext) -> List[ValidationObservation]:
        """
        Run validation analysis on a case, comparing notes to structured data.

        Args:
            context: The full CaseContext to validate.

        Returns:
            List of ValidationObservation objects. Returns empty list on failure.
        """
        try:
            metadata_text = metadata_to_text(context.case_metadata)
            notes_text = notes_to_text(context.notes)

            # Emphasize both sources equally for cross-comparison
            structured_text = (
                "=== VISIT RECORDS ===\n"
                + visits_to_text(context.visits)
                + "\n\n=== CASE ACTIVITIES ===\n"
                + activity_to_text(context.activities)
                + "\n\n=== MEDICATION EVENTS ===\n"
                + medication_to_text(context.medication_events)
            )

            user_prompt = build_validation_prompt(metadata_text, notes_text, structured_text)

            raw_data = self.ai_service.call_claude_for_json(
                system_prompt=SYSTEM_PROMPT_BASE,
                user_prompt=user_prompt,
                feature_name="data_validation",
            )

            if not isinstance(raw_data, list):
                _logger.warning(
                    f"ValidationService: expected list, got {type(raw_data)}."
                )
                raw_data = [raw_data] if isinstance(raw_data, dict) else []

            observations = self._parse_observations(raw_data)
            _logger.info(
                f"ValidationService: found {len(observations)} observations "
                f"for case {context.case_metadata.case_id}."
            )
            return observations

        except Exception as exc:
            _logger.error(
                f"ValidationService.run_validation: failed for case "
                f"{context.case_metadata.case_id}: {exc}"
            )
            return []

    def _parse_observations(self, raw_data: list) -> List[ValidationObservation]:
        """
        Convert raw AI JSON output to ValidationObservation objects.
        """
        observations = []
        for i, item in enumerate(raw_data):
            if not isinstance(item, dict):
                continue

            severity = safe_get(item, "severity", default="Info")
            if severity not in _VALID_SEVERITIES:
                _logger.warning(
                    f"ValidationService: invalid severity '{severity}' at item {i}, "
                    "defaulting to 'Info'."
                )
                severity = "Info"

            observations.append(
                ValidationObservation(
                    observation=safe_get(item, "observation", default=f"Observation {i + 1}"),
                    notes_suggest=safe_get(item, "notes_suggest", default="Not documented in notes."),
                    data_shows=safe_get(item, "data_shows", default="Not present in structured data."),
                    severity=severity,
                )
            )

        return observations
