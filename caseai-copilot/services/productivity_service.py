"""
ProductivityService — CaseAI Copilot
Retrieves and aggregates daily productivity metrics per case manager.

SQL mode:  Attempts to call the TCM_Daily_Productivity stored procedure.
           Falls back to the daily_productivity table if the proc doesn't exist.
Demo mode: Reads from data/sample_productivity.csv.
"""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import List, Optional

import pandas as pd

from models.schemas import ProductivityRecord
from utils.logger import get_logger, log_sql_query

_logger = get_logger("caseai.productivity_service")

# Path to demo CSV
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_PRODUCTIVITY_CSV = os.path.join(_DATA_DIR, "sample_productivity.csv")


def _safe_int(val, default: int = 0) -> int:
    try:
        return int(val) if val is not None and str(val).strip() not in ("", "nan", "None") else default
    except (ValueError, TypeError):
        return default


def _safe_float(val, default: float = 0.0) -> float:
    try:
        return float(val) if val is not None and str(val).strip() not in ("", "nan", "None") else default
    except (ValueError, TypeError):
        return default


def _safe_str(val, default: str = "") -> str:
    if val is None:
        return default
    s = str(val).strip()
    return default if s.lower() in ("nan", "none", "null") else s


def _row_to_record(row: dict) -> ProductivityRecord:
    return ProductivityRecord(
        productivity_id=_safe_str(row.get("productivity_id")),
        report_date=_safe_str(row.get("report_date")),
        case_manager=_safe_str(row.get("case_manager")),
        total_cases=_safe_int(row.get("total_cases")),
        tcm_count=_safe_int(row.get("tcm_count")),
        fcm_count=_safe_int(row.get("fcm_count")),
        task_count=_safe_int(row.get("task_count")),
        assessment_count=_safe_int(row.get("assessment_count")),
        phone_outreach_count=_safe_int(row.get("phone_outreach_count")),
        home_visit_count=_safe_int(row.get("home_visit_count")),
        hours_worked=_safe_float(row.get("hours_worked")),
    )


class ProductivityService:
    """
    Retrieves daily productivity data, either from SQL Server or demo CSV.

    Usage:
        svc = ProductivityService(data_source=sql_or_mock_source)
        records = svc.get_productivity(start_date="2026-03-01", end_date="2026-03-11")
    """

    def __init__(self, data_source=None):
        """
        Args:
            data_source: A SQLDataSource or MockDataSource instance.
                         If None, always uses demo CSV data.
        """
        self._data_source = data_source

    def get_productivity(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        case_manager: Optional[str] = None,
    ) -> List[ProductivityRecord]:
        """
        Returns productivity records filtered by date range and optionally by case manager.

        Args:
            start_date:   ISO date string "YYYY-MM-DD". Defaults to first day of current month.
            end_date:     ISO date string "YYYY-MM-DD". Defaults to today.
            case_manager: If provided, filters to a single case manager (exact match).

        Returns:
            List of ProductivityRecord, sorted by report_date ascending.
        """
        today = date.today()
        if not start_date:
            start_date = today.replace(day=1).isoformat()
        if not end_date:
            end_date = today.isoformat()

        # Try SQL first, fall back to demo data
        from services.sql_service import SQLDataSource  # avoid circular import
        if self._data_source is not None and isinstance(self._data_source, SQLDataSource):
            records = self._get_from_sql(start_date, end_date, case_manager)
            if records is not None:
                return records

        return self._get_from_csv(start_date, end_date, case_manager)

    def get_case_managers(self) -> List[str]:
        """Returns sorted list of distinct case manager names from available data."""
        records = self._get_from_csv(
            start_date="2000-01-01",
            end_date=date.today().isoformat(),
        )
        managers = sorted({r.case_manager for r in records if r.case_manager})
        return managers

    def get_case_managers_from_sql(self) -> List[str]:
        """Returns distinct case managers from SQL, falls back to CSV."""
        from services.sql_service import SQLDataSource
        if self._data_source is not None and isinstance(self._data_source, SQLDataSource):
            try:
                conn = self._data_source.connect()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT DISTINCT case_manager FROM daily_productivity ORDER BY case_manager"
                )
                rows = [r[0] for r in cursor.fetchall() if r[0]]
                cursor.close()
                if rows:
                    return rows
            except Exception as exc:
                _logger.warning(f"ProductivityService.get_case_managers_from_sql: {exc}")
        return self.get_case_managers()

    # ------------------------------------------------------------------
    # SQL access
    # ------------------------------------------------------------------

    def _get_from_sql(
        self,
        start_date: str,
        end_date: str,
        case_manager: Optional[str],
    ) -> Optional[List[ProductivityRecord]]:
        """
        Tries to call TCM_Daily_Productivity stored procedure.
        Falls back to direct table query if proc does not exist.
        Returns None if SQL is completely unavailable (triggers CSV fallback).
        """
        # 1) Try stored procedure
        try:
            records = self._call_stored_proc(start_date, end_date, case_manager)
            if records is not None:
                return records
        except Exception as exc:
            _logger.info(f"ProductivityService: stored proc unavailable ({exc}), trying table.")

        # 2) Try direct table query
        try:
            return self._query_productivity_table(start_date, end_date, case_manager)
        except Exception as exc:
            _logger.warning(
                f"ProductivityService: table query also failed ({exc}). "
                "Falling back to CSV demo data."
            )
            return None

    def _call_stored_proc(
        self,
        start_date: str,
        end_date: str,
        case_manager: Optional[str],
    ) -> Optional[List[ProductivityRecord]]:
        """
        Calls TCM_Daily_Productivity stored procedure with date parameters.

        Expected proc signature:
            EXEC TCM_Daily_Productivity @StartDate = ?, @EndDate = ?
        The proc should return columns matching ProductivityRecord fields.

        TODO: Update the EXEC call below to match your actual stored procedure
              name and parameter names if they differ.
        """
        conn = self._data_source.connect()
        cursor = conn.cursor()

        query = "EXEC TCM_Daily_Productivity @StartDate = ?, @EndDate = ?"
        log_sql_query(query, "ALL")
        cursor.execute(query, (start_date, end_date))

        columns = [col[0].lower() for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.close()

        if not rows:
            return []

        records = [_row_to_record(r) for r in rows]

        # Apply case manager filter post-fetch (proc may not support it)
        if case_manager:
            records = [r for r in records if r.case_manager == case_manager]

        _logger.info(
            f"ProductivityService: loaded {len(records)} records from stored procedure."
        )
        return sorted(records, key=lambda r: r.report_date)

    def _query_productivity_table(
        self,
        start_date: str,
        end_date: str,
        case_manager: Optional[str],
    ) -> List[ProductivityRecord]:
        """
        Queries the daily_productivity table directly when stored proc is unavailable.
        """
        conn = self._data_source.connect()
        cursor = conn.cursor()

        if case_manager:
            query = (
                "SELECT productivity_id, report_date, case_manager, total_cases, "
                "tcm_count, fcm_count, task_count, assessment_count, "
                "phone_outreach_count, home_visit_count, hours_worked "
                "FROM daily_productivity "
                "WHERE report_date BETWEEN ? AND ? AND case_manager = ? "
                "ORDER BY report_date ASC"
            )
            log_sql_query(query, "ALL")
            cursor.execute(query, (start_date, end_date, case_manager))
        else:
            query = (
                "SELECT productivity_id, report_date, case_manager, total_cases, "
                "tcm_count, fcm_count, task_count, assessment_count, "
                "phone_outreach_count, home_visit_count, hours_worked "
                "FROM daily_productivity "
                "WHERE report_date BETWEEN ? AND ? "
                "ORDER BY report_date ASC"
            )
            log_sql_query(query, "ALL")
            cursor.execute(query, (start_date, end_date))

        columns = [col[0].lower() for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.close()

        records = [_row_to_record(r) for r in rows]
        _logger.info(
            f"ProductivityService: loaded {len(records)} records from daily_productivity table."
        )
        return records

    # ------------------------------------------------------------------
    # Demo / CSV access
    # ------------------------------------------------------------------

    def _get_from_csv(
        self,
        start_date: str,
        end_date: str,
        case_manager: Optional[str] = None,
    ) -> List[ProductivityRecord]:
        """Loads productivity data from the sample CSV file."""
        try:
            df = pd.read_csv(_PRODUCTIVITY_CSV, dtype=str)
            df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)

            # Date filter
            df = df[
                (df["report_date"] >= start_date) &
                (df["report_date"] <= end_date)
            ]

            # Case manager filter
            if case_manager:
                df = df[df["case_manager"] == case_manager]

            df = df.sort_values("report_date")
            records = [_row_to_record(row.to_dict()) for _, row in df.iterrows()]
            _logger.info(
                f"ProductivityService: loaded {len(records)} records from CSV "
                f"({start_date} to {end_date})."
            )
            return records

        except FileNotFoundError:
            _logger.warning(f"ProductivityService: CSV not found at {_PRODUCTIVITY_CSV}")
            return []
        except Exception as exc:
            _logger.error(f"ProductivityService._get_from_csv: {exc}")
            return []
