"""
CaseAI Copilot - Reports Tables Setup Script
Creates and seeds the daily_productivity and referrals tables in SQL Server.
Run once after setup_database.py:  python setup_reports_tables.py
"""

import csv
import os
import sys

import pyodbc

SERVER   = "LAPTOP-Q6V2KMQ9"
DB_NAME  = "CaseAICopilot"
CONN_STR = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SERVER};"
    f"DATABASE={DB_NAME};"
    "Trusted_Connection=yes;"
    "Connection Timeout=30;"
)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def get_conn():
    return pyodbc.connect(CONN_STR, autocommit=True)


def create_tables(conn):
    c = conn.cursor()

    c.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='daily_productivity' AND xtype='U')
        CREATE TABLE daily_productivity (
            productivity_id     NVARCHAR(20)  PRIMARY KEY,
            report_date         DATE          NOT NULL,
            case_manager        NVARCHAR(100) NOT NULL,
            total_cases         INT           DEFAULT 0,
            tcm_count           INT           DEFAULT 0,
            fcm_count           INT           DEFAULT 0,
            task_count          INT           DEFAULT 0,
            assessment_count    INT           DEFAULT 0,
            phone_outreach_count INT          DEFAULT 0,
            home_visit_count    INT           DEFAULT 0,
            hours_worked        DECIMAL(5,2)  DEFAULT 0.0
        )
    """)
    print("[OK] Table [daily_productivity] ready.")

    c.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='referrals' AND xtype='U')
        CREATE TABLE referrals (
            referral_id     NVARCHAR(20)  PRIMARY KEY,
            case_id         NVARCHAR(20)  NOT NULL,
            referral_date   DATE,
            referred_by     NVARCHAR(100),
            referral_type   NVARCHAR(150),
            status          NVARCHAR(50),
            details         NVARCHAR(MAX)
        )
    """)
    print("[OK] Table [referrals] ready.")


def seed_productivity(conn):
    csv_path = os.path.join(DATA_DIR, "sample_productivity.csv")
    if not os.path.exists(csv_path):
        print(f"[SKIP] {csv_path} not found.")
        return

    c = conn.cursor()
    c.execute("DELETE FROM daily_productivity")

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [
            (
                r["productivity_id"].strip(),
                r["report_date"].strip(),
                r["case_manager"].strip(),
                int(r["total_cases"]),
                int(r["tcm_count"]),
                int(r["fcm_count"]),
                int(r["task_count"]),
                int(r["assessment_count"]),
                int(r["phone_outreach_count"]),
                int(r["home_visit_count"]),
                float(r["hours_worked"]),
            )
            for r in reader
        ]

    c.executemany(
        "INSERT INTO daily_productivity VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    print(f"[OK] Inserted {len(rows)} productivity records.")


def seed_referrals(conn):
    csv_path = os.path.join(DATA_DIR, "sample_referrals.csv")
    if not os.path.exists(csv_path):
        print(f"[SKIP] {csv_path} not found.")
        return

    c = conn.cursor()
    c.execute("DELETE FROM referrals")

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [
            (
                r["referral_id"].strip(),
                r["case_id"].strip(),
                r["referral_date"].strip(),
                r["referred_by"].strip(),
                r["referral_type"].strip(),
                r["status"].strip(),
                r["details"].strip(),
            )
            for r in reader
        ]

    c.executemany(
        "INSERT INTO referrals VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    print(f"[OK] Inserted {len(rows)} referral records.")


def verify(conn):
    c = conn.cursor()
    tables = ["daily_productivity", "referrals"]
    print("\nRow counts:")
    for tbl in tables:
        c.execute(f"SELECT COUNT(*) FROM {tbl}")
        print(f"  {tbl:<30} {c.fetchone()[0]:>4} rows")


if __name__ == "__main__":
    print(f"\nCaseAI Copilot - Reports Tables Setup")
    print(f"Server  : {SERVER}")
    print(f"Database: {DB_NAME}\n")
    try:
        conn = get_conn()
        create_tables(conn)
        seed_productivity(conn)
        seed_referrals(conn)
        verify(conn)
        conn.close()
        print("\n[DONE] Reports tables setup complete.")
    except Exception as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
