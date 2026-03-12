"""
Priority scoring service for CaseAI Copilot.
Heuristic-based case urgency scoring — no AI call required.
"""
from typing import List

from models.schemas import CaseContext, PriorityScore
from utils.helpers import days_since
from utils.logger import get_logger

_logger = get_logger("caseai.priority_service")

# Urgency label thresholds
_URGENCY_CRITICAL = 76
_URGENCY_HIGH = 51
_URGENCY_MEDIUM = 26


def _urgency_label(score: int) -> str:
    if score >= _URGENCY_CRITICAL:
        return "Critical"
    elif score >= _URGENCY_HIGH:
        return "High"
    elif score >= _URGENCY_MEDIUM:
        return "Medium"
    else:
        return "Low"


class PriorityService:
    """
    Heuristic-based case priority scoring engine.
    Scores cases from 0-100 based on engagement risk, clinical flags,
    documentation gaps, and caregiver concerns.
    """

    def __init__(self):
        pass

    def score_case(self, context: CaseContext) -> PriorityScore:
        """
        Calculate a priority score for a single case.

        Scoring factors (max 100 points):
        - Days since last contact > 14:              +20 points
        - Days since last contact > 30:              +10 additional points (total +30)
        - No post-discharge follow-up visit:         +25 points
        - Failed outreach activities:                +5 per failed (max +20)
        - Critical priority_label in metadata:       +15 points
        - No assigned nurse:                         +10 points
        - Note keywords (worsening/declined/missed): +5 per match (max +15)
        - Medication adherence concern in records:   +15 points

        Args:
            context: Full CaseContext to score.

        Returns:
            PriorityScore with score, urgency_label, explanation, and factors.
        """
        meta = context.case_metadata
        score = 0
        factors = []

        # ---- Factor 1: Days since last contact ----
        last_contact_days = days_since(meta.last_contact_date) if meta.last_contact_date else None

        if last_contact_days is not None:
            if last_contact_days > 30:
                score += 30
                factors.append(
                    f"No contact in {last_contact_days} days (>30 days: +30 points)"
                )
            elif last_contact_days > 14:
                score += 20
                factors.append(
                    f"No contact in {last_contact_days} days (>14 days: +20 points)"
                )
        else:
            score += 10
            factors.append("Last contact date not recorded (+10 points)")

        # ---- Factor 2: No post-discharge follow-up ----
        if meta.discharge_date and meta.discharge_date.strip():
            discharge_days = days_since(meta.discharge_date)
            if discharge_days is not None and discharge_days > 0:
                # Check if any visit occurred AFTER discharge
                post_discharge_visits = [
                    v for v in context.visits
                    if v.visit_date and v.visit_date > meta.discharge_date
                ]
                post_discharge_activities = [
                    a for a in context.activities
                    if a.activity_date and a.activity_date > meta.discharge_date
                    and a.activity_status.lower() == "completed"
                ]

                if not post_discharge_visits and not post_discharge_activities:
                    score += 25
                    factors.append(
                        "Case is discharged with no documented post-discharge follow-up (+25 points)"
                    )

        # ---- Factor 3: Failed outreach activities ----
        failed_outreach = [
            a for a in context.activities
            if a.activity_status.lower() in ("failed", "no_contact", "no-contact")
            or (
                "failed" in a.activity_status.lower()
                or "no answer" in a.details.lower()
                or "no contact" in a.details.lower()
            )
        ]
        failed_count = len(failed_outreach)
        if failed_count > 0:
            outreach_points = min(failed_count * 5, 20)
            score += outreach_points
            factors.append(
                f"{failed_count} failed outreach attempt(s) documented "
                f"(+{outreach_points} points, max 20)"
            )

        # ---- Factor 4: Critical priority label ----
        if meta.priority_label and meta.priority_label.lower() == "critical":
            score += 15
            factors.append("Case flagged as 'Critical' priority in metadata (+15 points)")

        # ---- Factor 5: No assigned nurse ----
        if not meta.assigned_nurse or not meta.assigned_nurse.strip():
            score += 10
            factors.append("No assigned nurse/coordinator on record (+10 points)")

        # ---- Factor 6: Note keyword analysis ----
        concern_keywords = ["worsening", "declined", "missed", "non-compliant",
                            "non-adherent", "unreachable", "critical", "urgent"]
        note_keyword_hits = 0
        for note in context.notes:
            note_lower = note.note_text.lower()
            for kw in concern_keywords:
                if kw in note_lower:
                    note_keyword_hits += 1
                    break  # Count each note only once per keyword scan

        if note_keyword_hits > 0:
            note_points = min(note_keyword_hits * 5, 15)
            score += note_points
            factors.append(
                f"{note_keyword_hits} note(s) contain concern indicators "
                f"(worsening/declined/missed/etc.) (+{note_points} points, max 15)"
            )

        # ---- Factor 7: Medication adherence concerns ----
        adherence_events = [
            e for e in context.medication_events
            if "adherence_concern" in e.event_type.lower()
            or "missed" in e.event_type.lower()
            or "refill_missed" in e.event_type.lower()
        ]
        if adherence_events:
            score += 15
            factors.append(
                f"{len(adherence_events)} medication adherence concern(s) documented (+15 points)"
            )

        # ---- Cap score at 100 ----
        score = min(score, 100)

        urgency = _urgency_label(score)

        # ---- Build explanation ----
        if factors:
            explanation = (
                f"Priority score of {score}/100 ({urgency}) based on {len(factors)} "
                f"contributing factor(s): "
                + "; ".join(factors[:3])  # Top 3 in explanation
                + ("." if len(factors) <= 3 else f"; and {len(factors) - 3} more factor(s).")
            )
        else:
            explanation = (
                f"Priority score of {score}/100 ({urgency}). "
                "No significant risk factors identified in available data."
            )

        _logger.info(
            f"PriorityService.score_case: {meta.case_id} scored {score}/100 ({urgency})"
        )

        return PriorityScore(
            case_id=meta.case_id,
            member_name=meta.member_name,
            score=score,
            urgency_label=urgency,
            explanation=explanation,
            factors=factors,
        )

    def rank_cases(self, contexts: List[CaseContext]) -> List[PriorityScore]:
        """
        Score all cases and return them sorted by priority (highest first).

        Args:
            contexts: List of CaseContext objects to score.

        Returns:
            List of PriorityScore objects sorted by score descending.
        """
        scores = []
        for context in contexts:
            try:
                priority = self.score_case(context)
                scores.append(priority)
            except Exception as exc:
                _logger.error(
                    f"PriorityService.rank_cases: failed to score case "
                    f"{context.case_metadata.case_id}: {exc}"
                )

        scores.sort(key=lambda s: s.score, reverse=True)
        _logger.info(f"PriorityService.rank_cases: ranked {len(scores)} cases.")
        return scores
