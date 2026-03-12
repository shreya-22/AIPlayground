"""
Data schemas for CaseAI Copilot.
All domain objects are defined here as Python dataclasses with type hints.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class CaseMetadata:
    """Represents the top-level case record."""
    case_id: str
    member_name: str
    status: str
    open_date: str
    discharge_date: Optional[str] = None
    assigned_nurse: Optional[str] = None
    last_contact_date: Optional[str] = None
    case_type: Optional[str] = None
    priority_label: Optional[str] = None


@dataclass
class CaseNote:
    """Represents a single clinical or operational note entry."""
    note_id: str
    case_id: str
    note_date: str
    note_author: str
    note_text: str


@dataclass
class PatientVisit:
    """Represents a visit record (in-person, phone, or no-show)."""
    visit_id: str
    case_id: str
    visit_date: str
    visit_type: str
    provider_name: str
    outcome: str


@dataclass
class CaseActivity:
    """Represents a case management activity record."""
    activity_id: str
    case_id: str
    activity_date: str
    activity_type: str
    activity_status: str
    details: str


@dataclass
class MedicationEvent:
    """Represents a medication-related event (prescription, refill, adherence issue, etc.)."""
    med_event_id: str
    case_id: str
    event_date: str
    medication_name: str
    event_type: str
    details: str


@dataclass
class RiskFlag:
    """Represents a single identified risk flag for a case."""
    risk_name: str
    severity: str          # "Low" | "Medium" | "High"
    evidence: str
    source: str            # "notes" | "structured" | "both"
    explanation: str


@dataclass
class TimelineEntry:
    """Represents a single chronological event in a case timeline."""
    date: str
    event: str
    source: str            # "notes" | "structured" | "both"
    confidence: str        # "high" | "medium" | "low"


@dataclass
class DocumentationGap:
    """Represents a documentation or follow-up gap identified in a case."""
    gap_type: str
    description: str
    severity: str          # "Low" | "Medium" | "High"
    recommendation: str


@dataclass
class ValidationObservation:
    """Represents a comparison observation between notes and structured data."""
    observation: str
    notes_suggest: str
    data_shows: str
    severity: str          # "Info" | "Low" | "Medium" | "High"


@dataclass
class PriorityScore:
    """Represents a calculated priority/urgency score for a case."""
    case_id: str
    member_name: str
    score: int             # 0-100
    urgency_label: str     # "Low" | "Medium" | "High" | "Critical"
    explanation: str       # Narrative explanation
    factors: List[str] = field(default_factory=list)   # List of contributing factors


@dataclass
class CaseContext:
    """
    Bundles all data for a case into a single context object.
    This is the primary input to all AI services.
    """
    case_metadata: CaseMetadata
    notes: List[CaseNote] = field(default_factory=list)
    visits: List[PatientVisit] = field(default_factory=list)
    activities: List[CaseActivity] = field(default_factory=list)
    medication_events: List[MedicationEvent] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Reporting schemas
# ---------------------------------------------------------------------------

@dataclass
class ProductivityRecord:
    """Daily productivity record for a case manager."""
    productivity_id: str
    report_date: str
    case_manager: str
    total_cases: int
    tcm_count: int             # Transitional Care Management services
    fcm_count: int             # Follow-up Care Management services
    task_count: int            # Administrative / task activities
    assessment_count: int      # Assessments performed
    phone_outreach_count: int  # Phone outreach calls
    home_visit_count: int      # Home visits
    hours_worked: float


@dataclass
class CaseStatusCounts:
    """Aggregate counts of cases by status for dashboard overview."""
    total: int
    active: int
    open: int
    closed: int
    discharged: int
    unassigned: int
    unassigned_cases: List[CaseMetadata] = field(default_factory=list)


@dataclass
class BillingSummary:
    """Billing summary for a single case, computed from case age."""
    case_id: str
    member_name: str
    case_manager: str
    open_date: str
    case_age_days: int
    billing_tier: str          # "0-30" | "31-60" | "61-90" | ">90"
    monthly_rate: float        # Current applicable monthly rate
    total_billed: float        # Total amount billed across all tiers to date
    months_active: float       # Total months the case has been open
    approaching_next_tier: bool  # True if within 5 days of crossing a tier boundary
    next_tier_days: Optional[int] = None  # Days until next tier (None if at max tier)


@dataclass
class ActivitySummary:
    """Summary of activity in the last 24 hours across all cases."""
    journal_entries: int
    progress_notes: int
    new_referrals: int
    care_plan_updates: int
    phone_outreach_count: int
    as_of: str                 # ISO datetime string of when this was computed
    is_simulated: bool = False  # True when running in demo mode


@dataclass
class DailyActivityRecord:
    """Aggregated daily activity counts, used for trend charts."""
    activity_date: str
    case_manager: str
    journal_count: int
    progress_note_count: int
    referral_count: int
    total_activities: int


@dataclass
class ReferralRecord:
    """Represents a single referral record."""
    referral_id: str
    case_id: str
    referral_date: str
    referred_by: str
    referral_type: str
    status: str                # "pending" | "completed" | "cancelled"
    details: str
