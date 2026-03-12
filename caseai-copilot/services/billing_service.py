"""
BillingService — CaseAI Copilot
Computes billing summaries for cases based on case age and configurable rate tiers.

Billing tiers (configurable via environment variables):
    0–30 days  : BILLING_RATE_0_30   (default $150/month)
    31–60 days : BILLING_RATE_31_60  (default $200/month)
    61–90 days : BILLING_RATE_61_90  (default $300/month)
    >90 days   : BILLING_RATE_GT_90  (default $450/month, flat rate until closed)

The service is purely computational — it derives billing from case metadata
and does not require a separate billing table.
"""
from __future__ import annotations

import os
from datetime import date, datetime
from typing import List, Optional, Tuple

from models.schemas import CaseMetadata, BillingSummary
from utils.logger import get_logger

_logger = get_logger("caseai.billing_service")

# Tier boundaries in days
_TIER_BOUNDARIES = (30, 60, 90)  # Upper bounds for tier 1, 2, 3


def _load_rates() -> Tuple[float, float, float, float]:
    """Loads billing rates from environment variables with sensible defaults."""
    def _env_float(key: str, default: float) -> float:
        try:
            return float(os.getenv(key, str(default)))
        except (ValueError, TypeError):
            return default

    rate_0_30  = _env_float("BILLING_RATE_0_30",  150.0)
    rate_31_60 = _env_float("BILLING_RATE_31_60", 200.0)
    rate_61_90 = _env_float("BILLING_RATE_61_90", 300.0)
    rate_gt_90 = _env_float("BILLING_RATE_GT_90", 450.0)
    return rate_0_30, rate_31_60, rate_61_90, rate_gt_90


def _case_age_days(open_date: str, discharge_date: Optional[str] = None) -> int:
    """
    Returns the age of a case in days.
    Uses discharge_date as the end date for closed cases, otherwise uses today.
    """
    formats = ["%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"]

    def _parse(s: str) -> Optional[date]:
        if not s or str(s).strip().lower() in ("nan", "none", "null", "nat", ""):
            return None
        for fmt in formats:
            try:
                return datetime.strptime(str(s).strip(), fmt).date()
            except ValueError:
                continue
        return None

    start = _parse(open_date)
    if start is None:
        return 0

    end = _parse(discharge_date) if discharge_date else None
    if end is None:
        end = date.today()

    return max(0, (end - start).days)


def _compute_total_billed(
    age_days: int,
    rate_0_30: float,
    rate_31_60: float,
    rate_61_90: float,
    rate_gt_90: float,
) -> float:
    """
    Computes the total billing amount for a case of given age,
    applying each rate tier to the appropriate portion of time.

    Example for a 75-day case:
        Days  1-30 : 1 month  × $150 = $150
        Days 31-60 : 1 month  × $200 = $200
        Days 61-75 : 0.5 month × $300 = $150
        Total = $500
    """
    if age_days <= 0:
        return 0.0

    total = 0.0

    # Tier 1: days 1–30
    tier1_days = min(age_days, 30)
    total += (tier1_days / 30.0) * rate_0_30

    if age_days > 30:
        tier2_days = min(age_days - 30, 30)
        total += (tier2_days / 30.0) * rate_31_60

    if age_days > 60:
        tier3_days = min(age_days - 60, 30)
        total += (tier3_days / 30.0) * rate_61_90

    if age_days > 90:
        gt90_days = age_days - 90
        total += (gt90_days / 30.0) * rate_gt_90

    return round(total, 2)


def _current_tier(age_days: int) -> str:
    if age_days <= 30:
        return "0-30"
    elif age_days <= 60:
        return "31-60"
    elif age_days <= 90:
        return "61-90"
    else:
        return ">90"


def _current_rate(
    age_days: int,
    rate_0_30: float,
    rate_31_60: float,
    rate_61_90: float,
    rate_gt_90: float,
) -> float:
    tier = _current_tier(age_days)
    return {
        "0-30":  rate_0_30,
        "31-60": rate_31_60,
        "61-90": rate_61_90,
        ">90":   rate_gt_90,
    }[tier]


def _approaching_next_tier(age_days: int, window: int = 5) -> Tuple[bool, Optional[int]]:
    """
    Returns (approaching, days_until_next_tier).
    'approaching' is True if within `window` days of crossing a tier boundary.
    Returns (False, None) if already at the max (>90) tier.
    """
    for boundary in _TIER_BOUNDARIES:
        days_until = boundary - age_days
        if 0 < days_until <= window:
            return True, days_until
    return False, None


class BillingService:
    """
    Computes billing summaries from case metadata.

    No database connection required — billing is derived entirely from
    case open/discharge dates and configurable rate tiers.
    """

    def __init__(self):
        self._rates = _load_rates()

    def compute_summary(self, case: CaseMetadata) -> BillingSummary:
        """
        Computes a BillingSummary for a single case.

        Args:
            case: CaseMetadata object.

        Returns:
            BillingSummary with computed billing amounts and tier information.
        """
        r0, r31, r61, r91 = self._rates

        age_days = _case_age_days(case.open_date, case.discharge_date)
        total_billed = _compute_total_billed(age_days, r0, r31, r61, r91)
        tier = _current_tier(age_days)
        monthly_rate = _current_rate(age_days, r0, r31, r61, r91)
        approaching, next_tier_days = _approaching_next_tier(age_days)

        return BillingSummary(
            case_id=case.case_id,
            member_name=case.member_name,
            case_manager=case.assigned_nurse or "Unassigned",
            open_date=case.open_date,
            case_age_days=age_days,
            billing_tier=tier,
            monthly_rate=monthly_rate,
            total_billed=total_billed,
            months_active=round(age_days / 30.0, 1),
            approaching_next_tier=approaching,
            next_tier_days=next_tier_days,
        )

    def compute_all(self, cases: List[CaseMetadata]) -> List[BillingSummary]:
        """
        Computes billing summaries for a list of cases, sorted by total_billed descending.

        Args:
            cases: List of CaseMetadata objects.

        Returns:
            List of BillingSummary, sorted by total_billed descending.
        """
        summaries = [self.compute_summary(c) for c in cases]
        return sorted(summaries, key=lambda s: s.total_billed, reverse=True)

    def get_billing_by_manager(
        self, summaries: List[BillingSummary]
    ) -> dict:
        """
        Aggregates total billed amount per case manager.

        Returns:
            Dict mapping case_manager name → total billed (float).
        """
        by_manager: dict = {}
        for s in summaries:
            by_manager[s.case_manager] = round(
                by_manager.get(s.case_manager, 0.0) + s.total_billed, 2
            )
        return dict(sorted(by_manager.items(), key=lambda x: x[1], reverse=True))

    def get_by_tier(self, summaries: List[BillingSummary]) -> dict:
        """
        Groups cases by billing tier.

        Returns:
            Dict mapping tier label → list of BillingSummary.
        """
        tiers: dict = {"0-30": [], "31-60": [], "61-90": [], ">90": []}
        for s in summaries:
            tiers.setdefault(s.billing_tier, []).append(s)
        return tiers

    def get_approaching_tier_change(
        self, summaries: List[BillingSummary]
    ) -> List[BillingSummary]:
        """Returns cases that are within 5 days of crossing into a higher billing tier."""
        return [s for s in summaries if s.approaching_next_tier]

    def get_rates(self) -> dict:
        """Returns the currently loaded billing rates."""
        r0, r31, r61, r91 = self._rates
        return {
            "0-30 days":  r0,
            "31-60 days": r31,
            "61-90 days": r61,
            ">90 days":   r91,
        }
