"""
ActivityTrackingService — CaseAI Copilot
Tracks journal entries, progress notes, referrals, and other activity metrics.

SQL mode:  Queries case_notes, case_activity, and referrals tables directly.
Demo mode: Uses sample CSV data and simulates last-24h counts from the dataset.

This service drives the "Last 24 Hours" widget and the activity trend charts
in the Reports tab.
"""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import List, Optional

import pandas as pd

from models.schemas import ActivitySummary, DailyActivityRecord, ReferralRecord
from utils.logger import get_logger, log_sql_query

_logger = get_logger("caseai.activity_tracking_service")

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_REFERRALS_CSV  = os.path.join(_DATA_DIR, "sample_referrals.csv")
_NOTES_CSV      = os.path.join(_DATA_DIR, "sample_notes.csv")
_ACTIVITY_CSV   = os.path.join(_DATA_DIR, "sample_activity.csv")


def _safe_str(val, default: str = "") -> str:
    if val is None:
        return default
    s = str(val).strip()
    return default if s.lower() in ("nan", "none", "null") else s


def _safe_int(val, default: int = 0) -> int:
    try:
        return int(val) if val is not None and str(val).strip() not in ("", "nan", "None") else default
    except (ValueError, TypeError):
        return default


class ActivityTrackingService:
    """
    Provides activity counts and trends for the Reports dashboard.

    Note on demo mode last-24h activity:
        Since sample data dates are historical (2024), the last-24h widget
        uses a simulated snapshot based on the most recent activity in the
        dataset. The widget clearly labels this as simulated.
    """

    # Activity types that count as "journal entries" (operational notes by case managers)
    JOURNAL_TYPES = {"assessment", "care_plan_update", "medication_review"}
    # Activity types that count as "progress notes"
    PROGRESS_TYPES = {"phone_outreach", "home_visit", "follow_up_scheduled", "follow_up_completed"}

    def __init__(self, data_source=None):
        """
        Args:
            data_source: SQLDataSource or MockDataSource instance.
                         If None, always uses CSV demo data.
        """
        self._data_source = data_source

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_last_24h_summary(self) -> ActivitySummary:
        """
        Returns an ActivitySummary for the last 24 hours.
        In demo mode, returns a simulated snapshot clearly marked is_simulated=True.
        """
        from services.sql_service import SQLDataSource
        if self._data_source is not None and isinstance(self._data_source, SQLDataSource):
            try:
                return self._last_24h_from_sql()
            except Exception as exc:
                _logger.warning(f"ActivityTrackingService.get_last_24h_summary SQL failed: {exc}")

        return self._last_24h_simulated()

    def get_referrals(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[ReferralRecord]:
        """
        Returns referral records filtered by date range and optionally by status.

        Args:
            start_date: ISO date string. Defaults to first day of current month.
            end_date:   ISO date string. Defaults to today.
            status:     Filter by status ("pending", "completed", etc.). None = all.
        """
        today = date.today()
        if not start_date:
            start_date = today.replace(day=1).isoformat()
        if not end_date:
            end_date = today.isoformat()

        from services.sql_service import SQLDataSource
        if self._data_source is not None and isinstance(self._data_source, SQLDataSource):
            try:
                return self._get_referrals_sql(start_date, end_date, status)
            except Exception as exc:
                _logger.warning(f"ActivityTrackingService.get_referrals SQL failed: {exc}")

        return self._get_referrals_csv(start_date, end_date, status)

    def get_all_referrals(self) -> List[ReferralRecord]:
        """Returns all referral records regardless of date range."""
        return self.get_referrals(start_date="2000-01-01", end_date=date.today().isoformat())

    def get_activity_trend(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[DailyActivityRecord]:
        """
        Returns daily activity counts aggregated across all case managers,
        suitable for trend charts.

        Args:
            start_date: ISO date string. Defaults to 30 days ago.
            end_date:   ISO date string. Defaults to today.
        """
        today = date.today()
        if not start_date:
            start_date = (today - timedelta(days=30)).isoformat()
        if not end_date:
            end_date = today.isoformat()

        from services.sql_service import SQLDataSource
        if self._data_source is not None and isinstance(self._data_source, SQLDataSource):
            try:
                return self._get_activity_trend_sql(start_date, end_date)
            except Exception as exc:
                _logger.warning(f"ActivityTrackingService.get_activity_trend SQL failed: {exc}")

        return self._get_activity_trend_csv(start_date, end_date)

    def get_monthly_referral_counts(
        self, months: int = 6
    ) -> dict:
        """
        Returns a dict of month_label → referral_count for the past N months.
        Used for the monthly referral trend chart.
        """
        all_refs = self.get_all_referrals()
        today = date.today()
        result = {}
        for i in range(months - 1, -1, -1):
            # Build month start/end
            y = today.year
            m = today.month - i
            while m <= 0:
                m += 12
                y -= 1
            month_start = date(y, m, 1)
            if m == 12:
                month_end = date(y + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(y, m + 1, 1) - timedelta(days=1)

            label = month_start.strftime("%b %Y")
            count = sum(
                1 for r in all_refs
                if r.referral_date and month_start.isoformat() <= r.referral_date <= month_end.isoformat()
            )
            result[label] = count

        return result

    # ------------------------------------------------------------------
    # SQL implementations
    # ------------------------------------------------------------------

    def _last_24h_from_sql(self) -> ActivitySummary:
        """Queries live SQL tables for the last 24 hours of activity."""
        conn = self._data_source.connect()
        cursor = conn.cursor()
        cutoff = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
        now_str = datetime.now().isoformat(timespec="minutes")

        # Journal entries: case_notes created in last 24h
        q_notes = "SELECT COUNT(*) FROM case_notes WHERE CAST(note_date AS DATETIME) >= ?"
        log_sql_query(q_notes, "ALL")
        cursor.execute(q_notes, (cutoff,))
        journal_count = cursor.fetchone()[0] or 0

        # Progress notes: phone/home activities in last 24h
        q_progress = (
            "SELECT COUNT(*) FROM case_activity "
            "WHERE CAST(activity_date AS DATETIME) >= ? "
            "AND activity_type IN ('phone_outreach','home_visit','follow_up_completed')"
        )
        log_sql_query(q_progress, "ALL")
        cursor.execute(q_progress, (cutoff,))
        progress_count = cursor.fetchone()[0] or 0

        # New referrals in last 24h
        try:
            q_refs = "SELECT COUNT(*) FROM referrals WHERE CAST(referral_date AS DATETIME) >= ?"
            log_sql_query(q_refs, "ALL")
            cursor.execute(q_refs, (cutoff,))
            referral_count = cursor.fetchone()[0] or 0
        except Exception:
            referral_count = 0

        # Care plan updates in last 24h
        q_plans = (
            "SELECT COUNT(*) FROM case_activity "
            "WHERE CAST(activity_date AS DATETIME) >= ? "
            "AND activity_type = 'care_plan_update'"
        )
        log_sql_query(q_plans, "ALL")
        cursor.execute(q_plans, (cutoff,))
        plan_count = cursor.fetchone()[0] or 0

        # Phone outreach in last 24h
        q_phone = (
            "SELECT COUNT(*) FROM case_activity "
            "WHERE CAST(activity_date AS DATETIME) >= ? "
            "AND activity_type = 'phone_outreach'"
        )
        log_sql_query(q_phone, "ALL")
        cursor.execute(q_phone, (cutoff,))
        phone_count = cursor.fetchone()[0] or 0

        cursor.close()
        _logger.info("ActivityTrackingService: last-24h summary loaded from SQL.")
        return ActivitySummary(
            journal_entries=journal_count,
            progress_notes=progress_count,
            new_referrals=referral_count,
            care_plan_updates=plan_count,
            phone_outreach_count=phone_count,
            as_of=now_str,
            is_simulated=False,
        )

    def _get_referrals_sql(
        self,
        start_date: str,
        end_date: str,
        status: Optional[str],
    ) -> List[ReferralRecord]:
        """Queries the referrals table in SQL Server."""
        conn = self._data_source.connect()
        cursor = conn.cursor()

        if status:
            query = (
                "SELECT referral_id, case_id, referral_date, referred_by, "
                "referral_type, status, details "
                "FROM referrals "
                "WHERE referral_date BETWEEN ? AND ? AND status = ? "
                "ORDER BY referral_date DESC"
            )
            log_sql_query(query, "ALL")
            cursor.execute(query, (start_date, end_date, status))
        else:
            query = (
                "SELECT referral_id, case_id, referral_date, referred_by, "
                "referral_type, status, details "
                "FROM referrals "
                "WHERE referral_date BETWEEN ? AND ? "
                "ORDER BY referral_date DESC"
            )
            log_sql_query(query, "ALL")
            cursor.execute(query, (start_date, end_date))

        columns = [col[0].lower() for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.close()
        return [self._row_to_referral(r) for r in rows]

    def _get_activity_trend_sql(
        self, start_date: str, end_date: str
    ) -> List[DailyActivityRecord]:
        """Aggregates daily activity from SQL tables for trend chart."""
        conn = self._data_source.connect()
        cursor = conn.cursor()
        query = (
            "SELECT "
            "  CAST(activity_date AS DATE) AS activity_date, "
            "  'All' AS case_manager, "
            "  SUM(CASE WHEN activity_type IN ('assessment','care_plan_update','medication_review') THEN 1 ELSE 0 END) AS journal_count, "
            "  SUM(CASE WHEN activity_type IN ('phone_outreach','home_visit','follow_up_completed') THEN 1 ELSE 0 END) AS progress_note_count, "
            "  COUNT(*) AS total_activities "
            "FROM case_activity "
            "WHERE activity_date BETWEEN ? AND ? "
            "GROUP BY CAST(activity_date AS DATE) "
            "ORDER BY activity_date ASC"
        )
        log_sql_query(query, "ALL")
        cursor.execute(query, (start_date, end_date))
        columns = [col[0].lower() for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.close()

        return [
            DailyActivityRecord(
                activity_date=_safe_str(r.get("activity_date")),
                case_manager=_safe_str(r.get("case_manager"), "All"),
                journal_count=_safe_int(r.get("journal_count")),
                progress_note_count=_safe_int(r.get("progress_note_count")),
                referral_count=0,  # TODO: join with referrals table
                total_activities=_safe_int(r.get("total_activities")),
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Demo / CSV implementations
    # ------------------------------------------------------------------

    def _last_24h_simulated(self) -> ActivitySummary:
        """
        Builds a simulated last-24h summary from the most recent records in
        the sample CSVs. Clearly marked as simulated in the returned object.
        """
        now_str = datetime.now().isoformat(timespec="minutes")

        # Pull most recent 5 activity entries as simulated "today"
        try:
            act_df = pd.read_csv(_ACTIVITY_CSV, dtype=str)
            act_df = act_df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)
            act_df = act_df.sort_values("activity_date", ascending=False).head(10)

            journal_count = act_df[
                act_df["activity_type"].isin(self.JOURNAL_TYPES)
            ].shape[0]
            progress_count = act_df[
                act_df["activity_type"].isin(self.PROGRESS_TYPES)
            ].shape[0]
            care_plan_count = act_df[
                act_df["activity_type"] == "care_plan_update"
            ].shape[0]
            phone_count = act_df[
                act_df["activity_type"] == "phone_outreach"
            ].shape[0]
        except Exception as exc:
            _logger.warning(f"ActivityTrackingService._last_24h_simulated: {exc}")
            journal_count = progress_count = care_plan_count = phone_count = 0

        # Pull most recent 3 referrals
        try:
            ref_df = pd.read_csv(_REFERRALS_CSV, dtype=str)
            ref_df = ref_df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)
            referral_count = ref_df.sort_values("referral_date", ascending=False).head(3).shape[0]
        except Exception:
            referral_count = 0

        return ActivitySummary(
            journal_entries=journal_count,
            progress_notes=progress_count,
            new_referrals=referral_count,
            care_plan_updates=care_plan_count,
            phone_outreach_count=phone_count,
            as_of=now_str,
            is_simulated=True,
        )

    def _get_referrals_csv(
        self,
        start_date: str,
        end_date: str,
        status: Optional[str],
    ) -> List[ReferralRecord]:
        """Loads referrals from sample CSV with date and status filters."""
        try:
            df = pd.read_csv(_REFERRALS_CSV, dtype=str)
            df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)
            df = df[
                (df["referral_date"] >= start_date) &
                (df["referral_date"] <= end_date)
            ]
            if status:
                df = df[df["status"] == status]
            df = df.sort_values("referral_date", ascending=False)
            return [self._row_to_referral(row.to_dict()) for _, row in df.iterrows()]
        except FileNotFoundError:
            _logger.warning(f"ActivityTrackingService: CSV not found at {_REFERRALS_CSV}")
            return []
        except Exception as exc:
            _logger.error(f"ActivityTrackingService._get_referrals_csv: {exc}")
            return []

    def _get_activity_trend_csv(
        self, start_date: str, end_date: str
    ) -> List[DailyActivityRecord]:
        """Aggregates daily activity from sample CSV for trend charts."""
        try:
            df = pd.read_csv(_ACTIVITY_CSV, dtype=str)
            df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)
            df = df[
                (df["activity_date"] >= start_date) &
                (df["activity_date"] <= end_date)
            ]
            if df.empty:
                return []

            df["journal_flag"] = df["activity_type"].isin(self.JOURNAL_TYPES).astype(int)
            df["progress_flag"] = df["activity_type"].isin(self.PROGRESS_TYPES).astype(int)
            df["all_flag"] = 1

            grouped = df.groupby("activity_date").agg(
                journal_count=("journal_flag", "sum"),
                progress_note_count=("progress_flag", "sum"),
                total_activities=("all_flag", "sum"),
            ).reset_index()

            return [
                DailyActivityRecord(
                    activity_date=_safe_str(row.get("activity_date")),
                    case_manager="All",
                    journal_count=int(row.get("journal_count", 0)),
                    progress_note_count=int(row.get("progress_note_count", 0)),
                    referral_count=0,
                    total_activities=int(row.get("total_activities", 0)),
                )
                for _, row in grouped.iterrows()
            ]
        except Exception as exc:
            _logger.error(f"ActivityTrackingService._get_activity_trend_csv: {exc}")
            return []

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_referral(row: dict) -> ReferralRecord:
        return ReferralRecord(
            referral_id=_safe_str(row.get("referral_id")),
            case_id=_safe_str(row.get("case_id")),
            referral_date=_safe_str(row.get("referral_date")),
            referred_by=_safe_str(row.get("referred_by")),
            referral_type=_safe_str(row.get("referral_type")),
            status=_safe_str(row.get("status")),
            details=_safe_str(row.get("details")),
        )
