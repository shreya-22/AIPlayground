"""
Timeline generation service for CaseAI Copilot.
Uses AI to extract and organize chronological case events.
"""
from datetime import datetime
from typing import List

from models.schemas import CaseContext, TimelineEntry
from models.dto import metadata_to_text, notes_to_text, visits_to_text, activity_to_text, medication_to_text
from config.prompts import SYSTEM_PROMPT_BASE, build_timeline_prompt
from services.ai_service import AIService
from utils.logger import get_logger
from utils.helpers import safe_get

_logger = get_logger("caseai.timeline_service")

_VALID_SOURCES = {"notes", "structured", "both"}
_VALID_CONFIDENCE = {"high", "medium", "low"}


class TimelineService:
    """
    Service for generating a chronological case timeline using AI.
    """

    def __init__(self, ai_service: AIService):
        """
        Initialize TimelineService.

        Args:
            ai_service: An initialized AIService instance.
        """
        self.ai_service = ai_service

    def generate_timeline(self, context: CaseContext) -> List[TimelineEntry]:
        """
        Generate a chronological timeline for a case.

        Args:
            context: The full CaseContext to analyze.

        Returns:
            List of TimelineEntry objects sorted by date (oldest first).
            Returns empty list on failure.
        """
        try:
            metadata_text = metadata_to_text(context.case_metadata)
            notes_text = notes_to_text(context.notes)
            structured_text = (
                "=== VISITS ===\n" + visits_to_text(context.visits) + "\n\n"
                "=== ACTIVITIES ===\n" + activity_to_text(context.activities) + "\n\n"
                "=== MEDICATIONS ===\n" + medication_to_text(context.medication_events)
            )

            user_prompt = build_timeline_prompt(metadata_text, notes_text, structured_text)

            raw_data = self.ai_service.call_claude_for_json(
                system_prompt=SYSTEM_PROMPT_BASE,
                user_prompt=user_prompt,
                feature_name="timeline_generation",
            )

            if not isinstance(raw_data, list):
                _logger.warning(
                    f"TimelineService: expected list, got {type(raw_data)}. "
                    "Wrapping or clearing."
                )
                raw_data = [raw_data] if isinstance(raw_data, dict) else []

            entries = self._parse_timeline_entries(raw_data)
            sorted_entries = self._sort_timeline(entries)

            _logger.info(
                f"TimelineService: generated {len(sorted_entries)} timeline entries "
                f"for case {context.case_metadata.case_id}."
            )
            return sorted_entries

        except Exception as exc:
            _logger.error(
                f"TimelineService.generate_timeline: failed for case "
                f"{context.case_metadata.case_id}: {exc}"
            )
            return []

    def _parse_timeline_entries(self, raw_data: list) -> List[TimelineEntry]:
        """Convert raw AI JSON output to TimelineEntry objects."""
        entries = []
        for i, item in enumerate(raw_data):
            if not isinstance(item, dict):
                continue

            source = safe_get(item, "source", default="notes")
            if source not in _VALID_SOURCES:
                source = "notes"

            confidence = safe_get(item, "confidence", default="medium")
            if confidence.lower() not in _VALID_CONFIDENCE:
                confidence = "medium"

            entries.append(
                TimelineEntry(
                    date=safe_get(item, "date", default="Unknown"),
                    event=safe_get(item, "event", default="No description."),
                    source=source,
                    confidence=confidence.lower(),
                )
            )

        return entries

    def _sort_timeline(self, entries: List[TimelineEntry]) -> List[TimelineEntry]:
        """
        Sort timeline entries by date ascending.
        Entries with unparseable dates are appended at the end.
        """
        date_formats = ["%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y", "%Y/%m/%d"]

        def parse_date(entry: TimelineEntry):
            date_str = entry.date
            if not date_str or date_str.lower() in ("unknown", "not documented", ""):
                return datetime.max  # push unknowns to end

            for fmt in date_formats:
                try:
                    return datetime.strptime(date_str.strip(), fmt)
                except ValueError:
                    continue

            # Try partial match (e.g., "Early 2024", "February 2024")
            try:
                # Try just year-month
                partial_fmt = "%B %Y"
                return datetime.strptime(date_str.strip(), partial_fmt)
            except ValueError:
                pass

            return datetime.max  # fallback: unknown dates at end

        try:
            return sorted(entries, key=parse_date)
        except Exception as exc:
            _logger.warning(f"TimelineService._sort_timeline: sort failed: {exc}")
            return entries
