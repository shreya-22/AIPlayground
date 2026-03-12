"""
Data Transfer Objects and text-formatting functions for CaseAI Copilot.
These functions convert domain objects into readable text suitable for
inclusion in AI prompts.
"""
from typing import List, Dict, Any, Optional
from models.schemas import (
    CaseContext,
    CaseMetadata,
    CaseNote,
    PatientVisit,
    CaseActivity,
    MedicationEvent,
)


# ---------------------------------------------------------------------------
# Individual formatter functions
# ---------------------------------------------------------------------------

def metadata_to_text(metadata: CaseMetadata) -> str:
    """Format case metadata as clean readable text for AI prompts."""
    lines = [
        f"Case ID:          {metadata.case_id}",
        f"Member Name:      {metadata.member_name}",
        f"Status:           {metadata.status}",
        f"Case Type:        {metadata.case_type or 'Not specified'}",
        f"Priority Label:   {metadata.priority_label or 'Not specified'}",
        f"Open Date:        {metadata.open_date or 'Not recorded'}",
        f"Discharge Date:   {metadata.discharge_date or 'Not discharged / Not recorded'}",
        f"Assigned Nurse:   {metadata.assigned_nurse or 'NOT ASSIGNED'}",
        f"Last Contact:     {metadata.last_contact_date or 'Not recorded'}",
    ]
    return "\n".join(lines)


def notes_to_text(notes: List[CaseNote]) -> str:
    """Format a list of case notes as clean readable text for AI prompts."""
    if not notes:
        return "No clinical or operational notes are documented for this case."

    sorted_notes = sorted(notes, key=lambda n: n.note_date)
    parts = []
    for note in sorted_notes:
        header = f"[NOTE {note.note_id}] Date: {note.note_date} | Author: {note.note_author}"
        parts.append(f"{header}\n{note.note_text.strip()}")

    return "\n\n---\n\n".join(parts)


def visits_to_text(visits: List[PatientVisit]) -> str:
    """Format a list of patient visits as clean readable text for AI prompts."""
    if not visits:
        return "No visit records documented for this case."

    sorted_visits = sorted(visits, key=lambda v: v.visit_date)
    lines = []
    for v in sorted_visits:
        lines.append(
            f"Visit {v.visit_id} | {v.visit_date} | {v.visit_type} | "
            f"Provider: {v.provider_name} | Outcome: {v.outcome}"
        )

    return "\n".join(lines)


def activity_to_text(activities: List[CaseActivity]) -> str:
    """Format a list of case activities as clean readable text for AI prompts."""
    if not activities:
        return "No activity records documented for this case."

    sorted_activities = sorted(activities, key=lambda a: a.activity_date)
    lines = []
    for a in sorted_activities:
        lines.append(
            f"Activity {a.activity_id} | {a.activity_date} | {a.activity_type.upper()} | "
            f"Status: {a.activity_status} | {a.details}"
        )

    return "\n".join(lines)


def medication_to_text(events: List[MedicationEvent]) -> str:
    """Format a list of medication events as clean readable text for AI prompts."""
    if not events:
        return "No medication events documented for this case."

    sorted_events = sorted(events, key=lambda e: e.event_date)
    lines = []
    for e in sorted_events:
        lines.append(
            f"Med Event {e.med_event_id} | {e.event_date} | {e.medication_name} | "
            f"Event: {e.event_type.upper()} | {e.details}"
        )

    return "\n".join(lines)


def case_context_to_text(context: CaseContext) -> str:
    """
    Format the full CaseContext as a single comprehensive text block
    suitable for inclusion in AI prompts.
    """
    sections = [
        "=== CASE METADATA ===",
        metadata_to_text(context.case_metadata),
        "",
        "=== CLINICAL / OPERATIONAL NOTES ===",
        notes_to_text(context.notes),
        "",
        "=== VISIT RECORDS ===",
        visits_to_text(context.visits),
        "",
        "=== CASE ACTIVITIES ===",
        activity_to_text(context.activities),
        "",
        "=== MEDICATION EVENTS ===",
        medication_to_text(context.medication_events),
    ]
    return "\n".join(sections)


# ---------------------------------------------------------------------------
# DTO class for dict-serializable representation
# ---------------------------------------------------------------------------

class CaseContextDTO:
    """
    A dict-serializable representation of CaseContext for passing
    to external systems, logging, or caching.
    """

    def __init__(self, context: CaseContext):
        self._context = context

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the full case context to a plain dictionary."""
        meta = self._context.case_metadata
        return {
            "case_metadata": {
                "case_id": meta.case_id,
                "member_name": meta.member_name,
                "status": meta.status,
                "open_date": meta.open_date,
                "discharge_date": meta.discharge_date,
                "assigned_nurse": meta.assigned_nurse,
                "last_contact_date": meta.last_contact_date,
                "case_type": meta.case_type,
                "priority_label": meta.priority_label,
            },
            "notes": [
                {
                    "note_id": n.note_id,
                    "case_id": n.case_id,
                    "note_date": n.note_date,
                    "note_author": n.note_author,
                    "note_text": n.note_text,
                }
                for n in self._context.notes
            ],
            "visits": [
                {
                    "visit_id": v.visit_id,
                    "case_id": v.case_id,
                    "visit_date": v.visit_date,
                    "visit_type": v.visit_type,
                    "provider_name": v.provider_name,
                    "outcome": v.outcome,
                }
                for v in self._context.visits
            ],
            "activities": [
                {
                    "activity_id": a.activity_id,
                    "case_id": a.case_id,
                    "activity_date": a.activity_date,
                    "activity_type": a.activity_type,
                    "activity_status": a.activity_status,
                    "details": a.details,
                }
                for a in self._context.activities
            ],
            "medication_events": [
                {
                    "med_event_id": e.med_event_id,
                    "case_id": e.case_id,
                    "event_date": e.event_date,
                    "medication_name": e.medication_name,
                    "event_type": e.event_type,
                    "details": e.details,
                }
                for e in self._context.medication_events
            ],
        }

    def to_text(self) -> str:
        """Return the full context as formatted text for prompt injection."""
        return case_context_to_text(self._context)
