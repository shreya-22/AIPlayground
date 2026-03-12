"""
Data source implementations for CaseAI Copilot.

Provides two interchangeable data sources:
- MockDataSource: loads from local CSV files (demo mode)
- SQLDataSource:  connects to a SQL Server database (production mode)

Both implement the same interface so services/case_service.py is agnostic.
"""
import os
from typing import List, Optional, Union

import pandas as pd

from models.schemas import (
    CaseMetadata,
    CaseNote,
    PatientVisit,
    CaseActivity,
    MedicationEvent,
)
from utils.logger import get_logger, log_sql_query

_logger = get_logger("caseai.sql_service")

# Path to data directory relative to this file
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _safe_str(value) -> str:
    """Convert a value to string, returning empty string for NaN/None."""
    if value is None:
        return ""
    s = str(value).strip()
    return "" if s.lower() in ("nan", "none", "null", "nat") else s


def _safe_optional_str(value) -> Optional[str]:
    """Convert a value to Optional[str], returning None for NaN/None."""
    s = _safe_str(value)
    return s if s else None


# ---------------------------------------------------------------------------
# MockDataSource
# ---------------------------------------------------------------------------

class MockDataSource:
    """
    Loads case data from CSV files in the data/ directory.
    Used in demo mode — no database connection required.
    """

    def __init__(self, data_dir: str = _DATA_DIR):
        self._data_dir = data_dir
        self._cases_df: Optional[pd.DataFrame] = None
        self._notes_df: Optional[pd.DataFrame] = None
        self._visits_df: Optional[pd.DataFrame] = None
        self._activities_df: Optional[pd.DataFrame] = None
        self._medications_df: Optional[pd.DataFrame] = None
        self._load_data()

    def _load_csv(self, filename: str) -> pd.DataFrame:
        """Load a CSV file, returning an empty DataFrame on error."""
        path = os.path.join(self._data_dir, filename)
        try:
            df = pd.read_csv(path, dtype=str)
            # Strip whitespace from all string columns
            df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)
            _logger.info(f"MockDataSource: loaded {len(df)} rows from {filename}")
            return df
        except FileNotFoundError:
            _logger.warning(f"MockDataSource: CSV file not found: {path}")
            return pd.DataFrame()
        except Exception as exc:
            _logger.error(f"MockDataSource: failed to load {filename}: {exc}")
            return pd.DataFrame()

    def _load_data(self) -> None:
        self._cases_df = self._load_csv("sample_cases.csv")
        self._notes_df = self._load_csv("sample_notes.csv")
        self._visits_df = self._load_csv("sample_visits.csv")
        self._activities_df = self._load_csv("sample_activity.csv")
        self._medications_df = self._load_csv("sample_medication_events.csv")

    def get_case_list(self) -> List[CaseMetadata]:
        """Return all cases as a list of CaseMetadata objects."""
        if self._cases_df is None or self._cases_df.empty:
            return []
        results = []
        for _, row in self._cases_df.iterrows():
            results.append(self._row_to_case_metadata(row))
        return results

    def get_case_metadata(self, case_id: str) -> Optional[CaseMetadata]:
        """Return metadata for a specific case, or None if not found."""
        if self._cases_df is None or self._cases_df.empty:
            return None
        mask = self._cases_df["case_id"] == case_id
        filtered = self._cases_df[mask]
        if filtered.empty:
            return None
        return self._row_to_case_metadata(filtered.iloc[0])

    def get_case_notes(self, case_id: str) -> List[CaseNote]:
        """Return all notes for a specific case."""
        if self._notes_df is None or self._notes_df.empty:
            return []
        mask = self._notes_df["case_id"] == case_id
        filtered = self._notes_df[mask].sort_values("note_date", na_position="last")
        return [
            CaseNote(
                note_id=_safe_str(row.get("note_id")),
                case_id=_safe_str(row.get("case_id")),
                note_date=_safe_str(row.get("note_date")),
                note_author=_safe_str(row.get("note_author")),
                note_text=_safe_str(row.get("note_text")),
            )
            for _, row in filtered.iterrows()
        ]

    def get_case_visits(self, case_id: str) -> List[PatientVisit]:
        """Return all visit records for a specific case."""
        if self._visits_df is None or self._visits_df.empty:
            return []
        mask = self._visits_df["case_id"] == case_id
        filtered = self._visits_df[mask].sort_values("visit_date", na_position="last")
        return [
            PatientVisit(
                visit_id=_safe_str(row.get("visit_id")),
                case_id=_safe_str(row.get("case_id")),
                visit_date=_safe_str(row.get("visit_date")),
                visit_type=_safe_str(row.get("visit_type")),
                provider_name=_safe_str(row.get("provider_name")),
                outcome=_safe_str(row.get("outcome")),
            )
            for _, row in filtered.iterrows()
        ]

    def get_case_activities(self, case_id: str) -> List[CaseActivity]:
        """Return all activity records for a specific case."""
        if self._activities_df is None or self._activities_df.empty:
            return []
        mask = self._activities_df["case_id"] == case_id
        filtered = self._activities_df[mask].sort_values("activity_date", na_position="last")
        return [
            CaseActivity(
                activity_id=_safe_str(row.get("activity_id")),
                case_id=_safe_str(row.get("case_id")),
                activity_date=_safe_str(row.get("activity_date")),
                activity_type=_safe_str(row.get("activity_type")),
                activity_status=_safe_str(row.get("activity_status")),
                details=_safe_str(row.get("details")),
            )
            for _, row in filtered.iterrows()
        ]

    def get_medication_events(self, case_id: str) -> List[MedicationEvent]:
        """Return all medication events for a specific case."""
        if self._medications_df is None or self._medications_df.empty:
            return []
        mask = self._medications_df["case_id"] == case_id
        filtered = self._medications_df[mask].sort_values("event_date", na_position="last")
        return [
            MedicationEvent(
                med_event_id=_safe_str(row.get("med_event_id")),
                case_id=_safe_str(row.get("case_id")),
                event_date=_safe_str(row.get("event_date")),
                medication_name=_safe_str(row.get("medication_name")),
                event_type=_safe_str(row.get("event_type")),
                details=_safe_str(row.get("details")),
            )
            for _, row in filtered.iterrows()
        ]

    def get_productivity_records(self, start_date: str = "", end_date: str = "") -> list:
        """
        Returns productivity records from sample_productivity.csv filtered by date range.
        Delegates to ProductivityService for full logic; here we just expose the raw CSV rows.
        """
        path = os.path.join(self._data_dir, "sample_productivity.csv")
        try:
            df = pd.read_csv(path, dtype=str)
            df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)
            if start_date:
                df = df[df["report_date"] >= start_date]
            if end_date:
                df = df[df["report_date"] <= end_date]
            return df.sort_values("report_date").to_dict("records")
        except Exception as exc:
            _logger.warning(f"MockDataSource.get_productivity_records: {exc}")
            return []

    def get_referrals(self, start_date: str = "", end_date: str = "") -> list:
        """Returns referral records from sample_referrals.csv filtered by date range."""
        path = os.path.join(self._data_dir, "sample_referrals.csv")
        try:
            df = pd.read_csv(path, dtype=str)
            df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)
            if start_date:
                df = df[df["referral_date"] >= start_date]
            if end_date:
                df = df[df["referral_date"] <= end_date]
            return df.sort_values("referral_date", ascending=False).to_dict("records")
        except Exception as exc:
            _logger.warning(f"MockDataSource.get_referrals: {exc}")
            return []

    @staticmethod
    def _row_to_case_metadata(row) -> CaseMetadata:
        return CaseMetadata(
            case_id=_safe_str(row.get("case_id")),
            member_name=_safe_str(row.get("member_name")),
            status=_safe_str(row.get("status")),
            open_date=_safe_str(row.get("open_date")),
            discharge_date=_safe_optional_str(row.get("discharge_date")),
            assigned_nurse=_safe_optional_str(row.get("assigned_nurse")),
            last_contact_date=_safe_optional_str(row.get("last_contact_date")),
            case_type=_safe_optional_str(row.get("case_type")),
            priority_label=_safe_optional_str(row.get("priority_label")),
        )


# ---------------------------------------------------------------------------
# SQLDataSource
# ---------------------------------------------------------------------------

class SQLDataSource:
    """
    Connects to a SQL Server database via pyodbc.
    Supports both Windows Authentication and SQL Server Authentication.
    Uses parameterized queries to prevent SQL injection.
    Falls back gracefully if connection fails.
    """

    def __init__(
        self,
        server: str,
        database: str,
        driver: str = "ODBC Driver 17 for SQL Server",
        auth: str = "windows",       # "windows" or "sql"
        username: str = "",
        password: str = "",
    ):
        self._server = server
        self._database = database
        self._driver = driver
        self._auth = auth.lower()
        self._username = username
        self._password = password
        self._connection = None

    def connect(self):
        """
        Establish a database connection.
        Returns the connection object or raises RuntimeError on failure.
        Supports Windows Authentication (Trusted_Connection=yes) and
        SQL Server Authentication (UID/PWD).
        """
        if self._connection is not None:
            return self._connection

        try:
            import pyodbc

            if self._auth == "windows":
                conn_str = (
                    f"DRIVER={{{self._driver}}};"
                    f"SERVER={self._server};"
                    f"DATABASE={self._database};"
                    "Trusted_Connection=yes;"
                    "Connection Timeout=30;"
                )
            else:
                conn_str = (
                    f"DRIVER={{{self._driver}}};"
                    f"SERVER={self._server};"
                    f"DATABASE={self._database};"
                    f"UID={self._username};"
                    f"PWD={self._password};"
                    "TrustServerCertificate=yes;"
                    "Connection Timeout=30;"
                )

            self._connection = pyodbc.connect(conn_str)
            _logger.info(
                f"SQLDataSource: connected to [{self._database}] on [{self._server}] "
                f"using {'Windows' if self._auth == 'windows' else 'SQL Server'} Authentication"
            )
            return self._connection
        except ImportError:
            raise RuntimeError("pyodbc is not installed. Run: pip install pyodbc")
        except Exception as exc:
            raise RuntimeError(
                f"Could not connect to SQL Server at {self._server}/{self._database}: {exc}"
            ) from exc

    def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            try:
                self._connection.close()
                self._connection = None
                _logger.info("SQLDataSource: connection closed.")
            except Exception as exc:
                _logger.warning(f"SQLDataSource: error closing connection: {exc}")

    def _execute(self, query: str, params: tuple = (), case_id: str = "") -> list:
        """Execute a parameterized query and return rows as list of dicts."""
        log_sql_query(query, case_id)
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            cursor.close()
            return rows
        except Exception as exc:
            _logger.error(f"SQLDataSource._execute: query failed: {exc}")
            return []

    def get_case_list(self) -> List[CaseMetadata]:
        query = (
            "SELECT case_id, member_name, status, open_date, discharge_date, "
            "assigned_nurse, last_contact_date, case_type, priority_label "
            "FROM cases ORDER BY open_date DESC"
        )
        rows = self._execute(query)
        return [self._row_to_case_metadata(r) for r in rows]

    def get_case_metadata(self, case_id: str) -> Optional[CaseMetadata]:
        query = (
            "SELECT case_id, member_name, status, open_date, discharge_date, "
            "assigned_nurse, last_contact_date, case_type, priority_label "
            "FROM cases WHERE case_id = ?"
        )
        rows = self._execute(query, (case_id,), case_id=case_id)
        if not rows:
            return None
        return self._row_to_case_metadata(rows[0])

    def get_case_notes(self, case_id: str) -> List[CaseNote]:
        query = (
            "SELECT note_id, case_id, note_date, note_author, note_text "
            "FROM case_notes WHERE case_id = ? ORDER BY note_date ASC"
        )
        rows = self._execute(query, (case_id,), case_id=case_id)
        return [
            CaseNote(
                note_id=_safe_str(r.get("note_id")),
                case_id=_safe_str(r.get("case_id")),
                note_date=_safe_str(r.get("note_date")),
                note_author=_safe_str(r.get("note_author")),
                note_text=_safe_str(r.get("note_text")),
            )
            for r in rows
        ]

    def get_case_visits(self, case_id: str) -> List[PatientVisit]:
        query = (
            "SELECT visit_id, case_id, visit_date, visit_type, provider_name, outcome "
            "FROM patient_visits WHERE case_id = ? ORDER BY visit_date ASC"
        )
        rows = self._execute(query, (case_id,), case_id=case_id)
        return [
            PatientVisit(
                visit_id=_safe_str(r.get("visit_id")),
                case_id=_safe_str(r.get("case_id")),
                visit_date=_safe_str(r.get("visit_date")),
                visit_type=_safe_str(r.get("visit_type")),
                provider_name=_safe_str(r.get("provider_name")),
                outcome=_safe_str(r.get("outcome")),
            )
            for r in rows
        ]

    def get_case_activities(self, case_id: str) -> List[CaseActivity]:
        query = (
            "SELECT activity_id, case_id, activity_date, activity_type, "
            "activity_status, details "
            "FROM case_activity WHERE case_id = ? ORDER BY activity_date ASC"
        )
        rows = self._execute(query, (case_id,), case_id=case_id)
        return [
            CaseActivity(
                activity_id=_safe_str(r.get("activity_id")),
                case_id=_safe_str(r.get("case_id")),
                activity_date=_safe_str(r.get("activity_date")),
                activity_type=_safe_str(r.get("activity_type")),
                activity_status=_safe_str(r.get("activity_status")),
                details=_safe_str(r.get("details")),
            )
            for r in rows
        ]

    def get_medication_events(self, case_id: str) -> List[MedicationEvent]:
        query = (
            "SELECT med_event_id, case_id, event_date, medication_name, "
            "event_type, details "
            "FROM medication_events WHERE case_id = ? ORDER BY event_date ASC"
        )
        rows = self._execute(query, (case_id,), case_id=case_id)
        return [
            MedicationEvent(
                med_event_id=_safe_str(r.get("med_event_id")),
                case_id=_safe_str(r.get("case_id")),
                event_date=_safe_str(r.get("event_date")),
                medication_name=_safe_str(r.get("medication_name")),
                event_type=_safe_str(r.get("event_type")),
                details=_safe_str(r.get("details")),
            )
            for r in rows
        ]

    def get_productivity_records(self, start_date: str = "", end_date: str = "") -> list:
        """
        Queries the daily_productivity table in SQL Server.
        Returns raw row dicts for consumption by ProductivityService.
        """
        query = (
            "SELECT productivity_id, report_date, case_manager, total_cases, "
            "tcm_count, fcm_count, task_count, assessment_count, "
            "phone_outreach_count, home_visit_count, hours_worked "
            "FROM daily_productivity "
            "WHERE report_date BETWEEN ? AND ? "
            "ORDER BY report_date ASC"
        )
        params = (start_date or "2000-01-01", end_date or "2099-12-31")
        log_sql_query(query, "ALL")
        return self._execute(query, params)

    def get_referrals(self, start_date: str = "", end_date: str = "") -> list:
        """
        Queries the referrals table in SQL Server.
        Returns raw row dicts for consumption by ActivityTrackingService.
        """
        query = (
            "SELECT referral_id, case_id, referral_date, referred_by, "
            "referral_type, status, details "
            "FROM referrals "
            "WHERE referral_date BETWEEN ? AND ? "
            "ORDER BY referral_date DESC"
        )
        params = (start_date or "2000-01-01", end_date or "2099-12-31")
        log_sql_query(query, "ALL")
        return self._execute(query, params)

    @staticmethod
    def _row_to_case_metadata(row: dict) -> CaseMetadata:
        return CaseMetadata(
            case_id=_safe_str(row.get("case_id")),
            member_name=_safe_str(row.get("member_name")),
            status=_safe_str(row.get("status")),
            open_date=_safe_str(row.get("open_date")),
            discharge_date=_safe_optional_str(row.get("discharge_date")),
            assigned_nurse=_safe_optional_str(row.get("assigned_nurse")),
            last_contact_date=_safe_optional_str(row.get("last_contact_date")),
            case_type=_safe_optional_str(row.get("case_type")),
            priority_label=_safe_optional_str(row.get("priority_label")),
        )


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------

def get_data_source(config) -> Union[MockDataSource, SQLDataSource]:
    """
    Returns the appropriate data source based on APP_MODE in config.

    If APP_MODE is 'sql', attempts to return a SQLDataSource.
    - DB_AUTH=windows: uses Windows Authentication (no username/password needed)
    - DB_AUTH=sql:     uses SQL Server Authentication (requires DB_USERNAME + DB_PASSWORD)

    If the SQL connection fails or APP_MODE is 'demo', falls back to MockDataSource.

    Args:
        config: AppConfig instance from config.settings.

    Returns:
        MockDataSource or SQLDataSource instance.
    """
    if config.APP_MODE == "sql":
        # Require server and database at minimum
        if not all([config.DB_SERVER, config.DB_DATABASE]):
            _logger.warning(
                "SQL mode selected but DB_SERVER or DB_DATABASE is missing. "
                "Falling back to MockDataSource (demo mode)."
            )
            return MockDataSource()

        # For SQL Auth, also require credentials
        db_auth = getattr(config, "DB_AUTH", "windows")
        if db_auth == "sql" and not all([config.DB_USERNAME, config.DB_PASSWORD]):
            _logger.warning(
                "SQL Server Authentication selected but DB_USERNAME or DB_PASSWORD is missing. "
                "Falling back to MockDataSource (demo mode)."
            )
            return MockDataSource()

        sql_source = SQLDataSource(
            server=config.DB_SERVER,
            database=config.DB_DATABASE,
            driver=config.DB_DRIVER,
            auth=db_auth,
            username=config.DB_USERNAME,
            password=config.DB_PASSWORD,
        )

        # Test the connection eagerly so we can fall back cleanly if it fails
        try:
            sql_source.connect()
            _logger.info(
                f"SQL data source connected: [{config.DB_DATABASE}] on [{config.DB_SERVER}]"
            )
            return sql_source
        except RuntimeError as exc:
            _logger.warning(
                f"SQL connection failed: {exc}. "
                "Falling back to MockDataSource (demo mode)."
            )
            return MockDataSource()

    _logger.info("Using MockDataSource (demo mode).")
    return MockDataSource()
