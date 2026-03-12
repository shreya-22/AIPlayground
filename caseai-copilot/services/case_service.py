"""
Case service for CaseAI Copilot.
Orchestrates data retrieval and assembles CaseContext objects.
"""
from typing import List, Union

from models.schemas import CaseContext, CaseMetadata
from models.dto import notes_to_text
from services.sql_service import MockDataSource, SQLDataSource
from utils.logger import get_logger

_logger = get_logger("caseai.case_service")


class CaseService:
    """
    High-level service for retrieving case data and assembling CaseContext objects.
    Data-source agnostic — works with both MockDataSource and SQLDataSource.
    """

    def __init__(self, data_source: Union[MockDataSource, SQLDataSource]):
        """
        Initialize CaseService with a data source.

        Args:
            data_source: An instance of MockDataSource or SQLDataSource.
        """
        self._data_source = data_source

    def get_case_list(self) -> List[CaseMetadata]:
        """
        Return a list of all available cases.

        Returns:
            List of CaseMetadata objects, sorted by open_date descending.
        """
        try:
            cases = self._data_source.get_case_list()
            _logger.info(f"CaseService.get_case_list: returned {len(cases)} cases.")
            return cases
        except Exception as exc:
            _logger.error(f"CaseService.get_case_list: failed with error: {exc}")
            return []

    def get_case_context(self, case_id: str) -> CaseContext:
        """
        Assemble and return the full CaseContext for a given case ID.

        Args:
            case_id: The unique case identifier.

        Returns:
            A fully populated CaseContext object.

        Raises:
            ValueError: If the case_id is not found in the data source.
        """
        if not case_id or not case_id.strip():
            raise ValueError("case_id cannot be empty.")

        case_id = case_id.strip()

        metadata = self._data_source.get_case_metadata(case_id)
        if metadata is None:
            raise ValueError(
                f"Case '{case_id}' was not found in the data source. "
                "Please verify the case ID and try again."
            )

        notes = self._data_source.get_case_notes(case_id)
        visits = self._data_source.get_case_visits(case_id)
        activities = self._data_source.get_case_activities(case_id)
        medication_events = self._data_source.get_medication_events(case_id)

        _logger.info(
            f"CaseService.get_case_context: assembled context for {case_id} | "
            f"notes={len(notes)}, visits={len(visits)}, "
            f"activities={len(activities)}, med_events={len(medication_events)}"
        )

        return CaseContext(
            case_metadata=metadata,
            notes=notes,
            visits=visits,
            activities=activities,
            medication_events=medication_events,
        )

    def get_notes_summary_text(self, case_id: str) -> str:
        """
        Return all notes for a case as formatted text.

        Args:
            case_id: The unique case identifier.

        Returns:
            Formatted string of all notes, suitable for display or prompt injection.
        """
        try:
            notes = self._data_source.get_case_notes(case_id)
            return notes_to_text(notes)
        except Exception as exc:
            _logger.error(
                f"CaseService.get_notes_summary_text: failed for {case_id}: {exc}"
            )
            return "Notes could not be retrieved."
