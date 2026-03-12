"""
CaseAI Copilot - Enterprise Healthcare Case Review Copilot
Main Streamlit application entry point.
"""
import os
import sys
import json
from typing import Optional

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import streamlit as st

# --- Config & Settings ---
from config.settings import get_config

# --- Models ---
from models.schemas import CaseContext, CaseMetadata

# --- Services ---
from services.sql_service import get_data_source, MockDataSource
from services.case_service import CaseService
from services.ai_service import AIService
from services.risk_service import RiskService
from services.timeline_service import TimelineService
from services.validation_service import ValidationService
from services.qa_service import QAService
from services.priority_service import PriorityService
from services.productivity_service import ProductivityService
from services.billing_service import BillingService
from services.activity_tracking_service import ActivityTrackingService

# --- Utils ---
from utils.formatting import (
    format_risk_flags,
    format_timeline,
    format_gaps,
    format_validation,
    format_priority_score,
    severity_badge,
)
from utils.helpers import days_since, format_date_display
from utils.logger import get_logger

_logger = get_logger("caseai.app")

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="CaseAI Copilot",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>
        /* Main background */
        .main .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }

        /* Card style */
        .case-card {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 1.25rem 1.5rem;
            margin-bottom: 1rem;
        }

        /* Disclaimer banner */
        .disclaimer-banner {
            background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
            color: white;
            padding: 0.6rem 1.25rem;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 500;
            margin-bottom: 1.25rem;
            text-align: center;
            letter-spacing: 0.03em;
        }

        /* Status badge */
        .status-active {
            background: #d1fae5;
            color: #065f46;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .status-discharged {
            background: #e0e7ff;
            color: #3730a3;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 600;
        }

        /* Priority label colors */
        .priority-critical { color: #7f1d1d; font-weight: 700; }
        .priority-high     { color: #991b1b; font-weight: 600; }
        .priority-medium   { color: #92400e; font-weight: 600; }
        .priority-low      { color: #14532d; font-weight: 500; }

        /* Chat message styling */
        .chat-user {
            background: #eff6ff;
            border-left: 3px solid #2563eb;
            padding: 0.75rem 1rem;
            border-radius: 0 8px 8px 0;
            margin: 0.5rem 0;
        }
        .chat-assistant {
            background: #f0fdf4;
            border-left: 3px solid #16a34a;
            padding: 0.75rem 1rem;
            border-radius: 0 8px 8px 0;
            margin: 0.5rem 0;
        }

        /* Section headers */
        .section-header {
            font-size: 1.1rem;
            font-weight: 700;
            color: #1e3a5f;
            border-bottom: 2px solid #2563eb;
            padding-bottom: 0.3rem;
            margin: 1rem 0 0.75rem 0;
        }

        /* Metric cards */
        div[data-testid="metric-container"] {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 0.5rem;
        }

        /* Sidebar styling */
        .css-1d391kg { background: #1e3a5f; }

        /* Worklist table */
        .worklist-critical { color: #7f1d1d; }

        /* Note card */
        .note-card {
            background: #fffbeb;
            border-left: 3px solid #f59e0b;
            padding: 0.5rem 0.75rem;
            border-radius: 0 6px 6px 0;
            font-size: 0.9rem;
            margin: 0.25rem 0;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================

def init_session_state():
    defaults = {
        "selected_case_id": None,
        "case_context": None,
        "ai_summary": None,
        "timeline": None,
        "risks": None,
        "gaps": None,
        "validation": None,
        "priority_score": None,
        "chat_history": [],
        "data_source": None,
        "case_service": None,
        "ai_service": None,
        "risk_service": None,
        "timeline_service": None,
        "validation_service": None,
        "qa_service": None,
        "priority_service": None,
        "app_mode_override": None,
        "case_list": [],
        "all_priority_scores": None,
        # Reports services
        "productivity_service": None,
        "billing_service": None,
        "activity_service": None,
        # Reports data cache
        "report_productivity": None,
        "report_billing": None,
        "report_activity_summary": None,
        "report_referrals": None,
        "report_activity_trend": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()

# ============================================================
# CONFIG
# ============================================================

config = get_config()

# ============================================================
# SERVICE INITIALIZATION
# ============================================================

def initialize_services(mode: str):
    """Initialize or reinitialize all services based on current mode."""
    try:
        # Create a temporary config object with the chosen mode
        class _TempConfig:
            APP_MODE = mode
            ANTHROPIC_API_KEY = config.ANTHROPIC_API_KEY
            DB_SERVER = config.DB_SERVER
            DB_DATABASE = config.DB_DATABASE
            DB_USERNAME = config.DB_USERNAME
            DB_PASSWORD = config.DB_PASSWORD
            DB_DRIVER = config.DB_DRIVER
            DB_AUTH = config.DB_AUTH
            MODEL_NAME = config.MODEL_NAME
            MAX_TOKENS = config.MAX_TOKENS

        data_source = get_data_source(_TempConfig())
        is_mock = isinstance(data_source, MockDataSource)

        if mode == "sql" and is_mock:
            st.warning(
                "SQL connection failed or parameters are incomplete. "
                "Automatically falling back to Demo Mode with sample data.",
                icon="⚠️",
            )

        st.session_state.data_source = data_source
        st.session_state.case_service = CaseService(data_source)
        st.session_state.priority_service = PriorityService()
        st.session_state.productivity_service = ProductivityService(data_source)
        st.session_state.billing_service = BillingService()
        st.session_state.activity_service = ActivityTrackingService(data_source)

        if config.ANTHROPIC_API_KEY:
            ai_svc = AIService(
                api_key=config.ANTHROPIC_API_KEY,
                model=config.MODEL_NAME,
                max_tokens=config.MAX_TOKENS,
            )
            st.session_state.ai_service = ai_svc
            st.session_state.risk_service = RiskService(ai_svc)
            st.session_state.timeline_service = TimelineService(ai_svc)
            st.session_state.validation_service = ValidationService(ai_svc)
            st.session_state.qa_service = QAService(ai_svc)
        else:
            st.session_state.ai_service = None
            st.session_state.risk_service = None
            st.session_state.timeline_service = None
            st.session_state.validation_service = None
            st.session_state.qa_service = None

        # Load case list
        st.session_state.case_list = st.session_state.case_service.get_case_list()
        return True

    except Exception as exc:
        _logger.error(f"initialize_services: {exc}", exc_info=True)
        st.error(f"Failed to initialize services: {exc}")
        return False


# Auto-initialize on first load
if st.session_state.data_source is None:
    initialize_services(config.APP_MODE)

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown(
        """
        <div style='text-align:center; padding: 0.5rem 0 1rem 0;'>
            <span style='font-size:2.2rem;'>🏥</span><br>
            <span style='font-size:1.3rem; font-weight:700; color:#1e3a5f;'>CaseAI Copilot</span><br>
            <span style='font-size:0.75rem; color:#64748b;'>AI-Powered Case Review</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    # --- Configuration Section ---
    st.markdown("**⚙️ Configuration**")

    mode_options = ["Demo Mode (CSV Data)", "SQL Mode (Database)"]
    current_mode_index = 1 if config.APP_MODE == "sql" else 0
    selected_mode_display = st.selectbox(
        "Data Source",
        options=mode_options,
        index=current_mode_index,
        key="mode_selectbox",
        help="Demo Mode uses bundled sample CSV data. SQL Mode connects to your SQL Server database.",
    )
    selected_mode = "sql" if "SQL" in selected_mode_display else "demo"

    # Re-initialize if mode changed
    if selected_mode != st.session_state.get("app_mode_override", config.APP_MODE):
        st.session_state.app_mode_override = selected_mode
        initialize_services(selected_mode)
        st.rerun()

    # Connection status
    if st.session_state.data_source is not None:
        if isinstance(st.session_state.data_source, MockDataSource):
            st.success("✅ Demo data loaded", icon="📁")
        else:
            st.success("✅ SQL Server connected", icon="🗄️")
    else:
        st.error("❌ Data source not available")

    # API key status
    if config.ANTHROPIC_API_KEY:
        st.success("✅ AI features enabled", icon="🤖")
    else:
        st.warning("⚠️ No API key — AI features disabled", icon="🔑")

    st.divider()

    # --- About Section ---
    st.markdown("**📖 About**")
    st.caption(
        "CaseAI Copilot is an AI-assisted operational tool for healthcare case managers. "
        "It helps review cases, identify risks, generate timelines, and answer questions "
        "about individual cases — all grounded in documented case data."
    )

    st.divider()

    # --- Data Mode Info ---
    if st.session_state.case_list:
        st.markdown(f"**📊 {len(st.session_state.case_list)} cases loaded**")
        for c in st.session_state.case_list:
            label_color = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢",
            }.get((c.priority_label or "").lower(), "⚪")
            st.caption(f"{label_color} {c.case_id}: {c.member_name}")

    st.divider()
    st.caption("v1.0.0 | CaseAI Copilot | Enterprise Edition")

# ============================================================
# MAIN HEADER
# ============================================================

st.markdown(
    """
    <div style='display:flex; align-items:center; gap:0.75rem; margin-bottom:0.25rem;'>
        <span style='font-size:2rem;'>🏥</span>
        <div>
            <h1 style='margin:0; font-size:1.8rem; font-weight:800; color:#1e3a5f;'>
                CaseAI Copilot
            </h1>
            <p style='margin:0; font-size:0.9rem; color:#64748b;'>
                Enterprise Healthcare Case Review Assistant
            </p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="disclaimer-banner">'
    "⚠️ AI-Assisted Operational Review Tool &nbsp;|&nbsp; "
    "Not a clinical decision system &nbsp;|&nbsp; "
    "All AI outputs must be reviewed by qualified professionals before action"
    "</div>",
    unsafe_allow_html=True,
)

# ============================================================
# CASE SELECTION
# ============================================================

st.markdown('<div class="section-header">Case Selection</div>', unsafe_allow_html=True)

if not st.session_state.case_list:
    st.warning("No cases available. Check that data files are present or SQL connection is configured.")
    st.stop()

# Build case options
case_options = {
    f"{c.case_id} — {c.member_name} ({c.case_type or 'N/A'}) [{c.priority_label or 'N/A'}]": c.case_id
    for c in st.session_state.case_list
}
option_keys = list(case_options.keys())

col_sel, col_btn, col_clear = st.columns([4, 1, 1])

with col_sel:
    selected_display = st.selectbox(
        "Select a case to review:",
        options=option_keys,
        key="case_selectbox",
        help="Select a case by ID and member name. Priority label is shown in brackets.",
    )

with col_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    load_clicked = st.button("📂 Load Case", type="primary", use_container_width=True)

with col_clear:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Clear", use_container_width=True):
        for key in ["case_context", "ai_summary", "timeline", "risks", "gaps",
                    "validation", "priority_score", "chat_history", "all_priority_scores",
                    "selected_case_id"]:
            st.session_state[key] = None if key != "chat_history" else []
        st.rerun()

if load_clicked:
    case_id_to_load = case_options[selected_display]
    with st.spinner(f"Loading case {case_id_to_load}..."):
        try:
            context = st.session_state.case_service.get_case_context(case_id_to_load)
            st.session_state.case_context = context
            st.session_state.selected_case_id = case_id_to_load
            # Clear previous AI results when loading a new case
            for key in ["ai_summary", "timeline", "risks", "gaps",
                        "validation", "priority_score", "chat_history", "all_priority_scores"]:
                st.session_state[key] = None if key != "chat_history" else []
            st.success(f"✅ Case {case_id_to_load} loaded successfully.")
        except ValueError as exc:
            st.error(f"Case not found: {exc}")
        except Exception as exc:
            st.error(f"Failed to load case: {exc}")

# ============================================================
# CASE LOADED — MAIN CONTENT TABS
# ============================================================

context: Optional[CaseContext] = st.session_state.get("case_context")

if context is None:
    st.info("👆 Select a case above and click **Load Case** to begin.")
    st.stop()

meta = context.case_metadata

# --- Case Header Card ---
st.markdown("<br>", unsafe_allow_html=True)

priority_colors = {
    "critical": "#7f1d1d", "high": "#991b1b", "medium": "#92400e", "low": "#14532d"
}
priority_color = priority_colors.get((meta.priority_label or "").lower(), "#1e3a5f")
status_bg = "#d1fae5" if meta.status.lower() == "active" else "#e0e7ff"
status_fg = "#065f46" if meta.status.lower() == "active" else "#3730a3"

days_lc = days_since(meta.last_contact_date)
days_open = days_since(meta.open_date)

st.markdown(
    f"""
    <div class="case-card" style="border-left: 4px solid {priority_color};">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:1rem;">
            <div>
                <h2 style="margin:0; font-size:1.5rem; font-weight:800; color:#1e3a5f;">
                    {meta.member_name}
                </h2>
                <span style="font-size:0.85rem; color:#64748b;">
                    Case ID: <strong>{meta.case_id}</strong> &nbsp;|&nbsp;
                    Type: <strong>{meta.case_type or 'N/A'}</strong>
                </span>
            </div>
            <div style="display:flex; gap:0.75rem; align-items:center; flex-wrap:wrap;">
                <span style="background:{status_bg}; color:{status_fg};
                    padding:3px 12px; border-radius:12px; font-size:0.8rem; font-weight:600;">
                    {meta.status}
                </span>
                <span style="background:#fef2f2; color:{priority_color};
                    padding:3px 12px; border-radius:12px; font-size:0.8rem; font-weight:700;">
                    {meta.priority_label or 'N/A'} Priority
                </span>
            </div>
        </div>
        <div style="margin-top:0.75rem; display:flex; gap:2rem; flex-wrap:wrap; font-size:0.85rem; color:#475569;">
            <span>👤 Nurse: <strong>{meta.assigned_nurse or '⚠️ Unassigned'}</strong></span>
            <span>📅 Opened: <strong>{format_date_display(meta.open_date)}</strong></span>
            <span>📞 Last Contact: <strong>{format_date_display(meta.last_contact_date)}
                {f'({days_lc}d ago)' if days_lc is not None else ''}</strong></span>
            {f'<span>🏁 Discharged: <strong>{format_date_display(meta.discharge_date)}</strong></span>'
             if meta.discharge_date else ''}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---- Quick stats row ----
m1, m2, m3, m4 = st.columns(4)
m1.metric("📝 Notes", len(context.notes))
m2.metric("🏥 Visits", len(context.visits))
m3.metric("📋 Activities", len(context.activities))
m4.metric("💊 Med Events", len(context.medication_events))

st.markdown("<br>", unsafe_allow_html=True)

# ============================================================
# TABS
# ============================================================

tabs = st.tabs([
    "📋 Case Overview",
    "📝 Raw Notes",
    "🤖 AI Summary",
    "⏱️ Timeline",
    "⚠️ Risk Analysis",
    "🔍 Validation Insights",
    "💬 Ask CaseAI",
    "📊 Priority / Worklist",
    "📈 Reports",
])

# ---- Helper: AI not available message ----
def ai_unavailable_msg():
    st.warning(
        "AI features require an Anthropic API key. "
        "Add `ANTHROPIC_API_KEY=your_key` to your `.env` file and restart the app.",
        icon="🔑",
    )

# =============================================================
# TAB 1 — CASE OVERVIEW
# =============================================================

with tabs[0]:
    st.markdown("### Case Overview")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("**Case Details**")
        fields = {
            "Case ID": meta.case_id,
            "Member Name": meta.member_name,
            "Case Type": meta.case_type or "Not specified",
            "Status": meta.status,
            "Priority": meta.priority_label or "Not specified",
        }
        for label, value in fields.items():
            st.markdown(f"**{label}:** {value}")

        st.markdown("**Timeline**")
        st.markdown(f"**Opened:** {format_date_display(meta.open_date)}")
        if days_open is not None:
            st.markdown(f"**Days Open:** {days_open} days")
        if meta.discharge_date:
            st.markdown(f"**Discharged:** {format_date_display(meta.discharge_date)}")

    with col_right:
        st.markdown("**Care Coordination**")
        nurse_display = meta.assigned_nurse if meta.assigned_nurse else "⚠️ **NOT ASSIGNED**"
        st.markdown(f"**Assigned Nurse:** {nurse_display}")
        st.markdown(
            f"**Last Contact:** {format_date_display(meta.last_contact_date)} "
            f"{f'({days_lc} days ago)' if days_lc is not None else ''}"
        )

        if days_lc is not None:
            if days_lc > 30:
                st.error(f"⚠️ Last contact was **{days_lc} days ago** — immediate outreach recommended.")
            elif days_lc > 14:
                st.warning(f"⚠️ Last contact was **{days_lc} days ago** — follow-up may be due.")
            else:
                st.success(f"✅ Last contact was {days_lc} days ago — within normal range.")

        st.markdown("**Data Summary**")
        st.markdown(f"- {len(context.notes)} clinical/operational notes")
        st.markdown(f"- {len(context.visits)} visit records")
        st.markdown(f"- {len(context.activities)} activity records")
        st.markdown(f"- {len(context.medication_events)} medication events")

    # Activity summary table
    if context.activities:
        st.markdown("---")
        st.markdown("**Recent Activity**")
        import pandas as pd
        activity_df = pd.DataFrame([
            {
                "Date": a.activity_date,
                "Type": a.activity_type,
                "Status": a.activity_status,
                "Details": a.details[:80] + "..." if len(a.details) > 80 else a.details,
            }
            for a in sorted(context.activities, key=lambda x: x.activity_date, reverse=True)[:8]
        ])
        st.dataframe(activity_df, use_container_width=True, hide_index=True)

# =============================================================
# TAB 2 — RAW NOTES
# =============================================================

with tabs[1]:
    st.markdown("### Clinical & Operational Notes")

    if not context.notes:
        st.info("No notes are documented for this case.")
    else:
        sorted_notes = sorted(context.notes, key=lambda n: n.note_date, reverse=True)
        st.caption(f"{len(sorted_notes)} notes found. Showing most recent first.")

        for note in sorted_notes:
            with st.expander(
                f"📝 {note.note_date} — {note.note_author} (ID: {note.note_id})",
                expanded=False,
            ):
                st.markdown(
                    f'<div class="note-card">{note.note_text}</div>',
                    unsafe_allow_html=True,
                )

# =============================================================
# TAB 3 — AI SUMMARY
# =============================================================

with tabs[2]:
    st.markdown("### AI Case Summary")
    st.caption(
        "Generates a structured narrative summary from all available case data. "
        "Output is factual and evidence-based — no fabrication."
    )

    if not config.ANTHROPIC_API_KEY:
        ai_unavailable_msg()
    else:
        if st.button("🤖 Generate Summary", key="btn_summary", type="primary"):
            with st.spinner("Analyzing case..."):
                try:
                    from models.dto import metadata_to_text, notes_to_text, visits_to_text, activity_to_text, medication_to_text
                    from config.prompts import SYSTEM_PROMPT_BASE, build_summary_prompt

                    meta_text = metadata_to_text(context.case_metadata)
                    n_text = notes_to_text(context.notes)
                    s_text = (
                        visits_to_text(context.visits) + "\n\n"
                        + activity_to_text(context.activities) + "\n\n"
                        + medication_to_text(context.medication_events)
                    )
                    prompt = build_summary_prompt(meta_text, n_text, s_text)
                    summary = st.session_state.ai_service.call_claude(
                        system_prompt=SYSTEM_PROMPT_BASE,
                        user_prompt=prompt,
                        feature_name="summary",
                    )
                    st.session_state.ai_summary = summary
                    st.success("✅ Summary generated.")
                except Exception as exc:
                    st.error(f"Summary generation failed: {exc}")

        if st.session_state.ai_summary:
            st.markdown("---")
            st.markdown(st.session_state.ai_summary)
        else:
            st.info("Click **Generate Summary** to produce an AI case summary.")

# =============================================================
# TAB 4 — TIMELINE
# =============================================================

with tabs[3]:
    st.markdown("### Case Timeline")
    st.caption(
        "Extracts and chronologically orders all documented events from notes, "
        "visits, activities, and medication records."
    )

    if not config.ANTHROPIC_API_KEY:
        ai_unavailable_msg()
    else:
        if st.button("⏱️ Generate Timeline", key="btn_timeline", type="primary"):
            with st.spinner("Analyzing case..."):
                try:
                    timeline = st.session_state.timeline_service.generate_timeline(context)
                    st.session_state.timeline = timeline
                    st.success(f"✅ Timeline generated — {len(timeline)} events found.")
                except Exception as exc:
                    st.error(f"Timeline generation failed: {exc}")

        if st.session_state.timeline:
            st.markdown("---")
            timeline_data = st.session_state.timeline

            # Visual timeline
            for entry in timeline_data:
                date = getattr(entry, "date", "Unknown date")
                event = getattr(entry, "event", "")
                source = getattr(entry, "source", "unknown")
                confidence = getattr(entry, "confidence", "medium")

                conf_icons = {"high": "✅", "medium": "⚠️", "low": "❓"}
                source_color = {
                    "notes": "#fef3c7",
                    "structured": "#dbeafe",
                    "both": "#d1fae5",
                }.get(source, "#f1f5f9")

                st.markdown(
                    f"""
                    <div style="display:flex; gap:1rem; margin:0.4rem 0; align-items:flex-start;">
                        <div style="min-width:120px; font-weight:600; color:#1e3a5f; font-size:0.85rem;">
                            {date}
                        </div>
                        <div style="background:{source_color}; border-radius:6px;
                            padding:0.4rem 0.75rem; flex:1; font-size:0.88rem;">
                            {conf_icons.get(confidence, '❓')} {event}
                            <span style="font-size:0.75rem; color:#64748b; margin-left:0.5rem;">
                                [{source}]
                            </span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("Click **Generate Timeline** to extract a chronological case history.")

# =============================================================
# TAB 5 — RISK ANALYSIS
# =============================================================

with tabs[4]:
    st.markdown("### Risk Analysis")
    st.caption(
        "AI identifies operational and care coordination risks based on documented case data. "
        "Not a clinical assessment tool."
    )

    if not config.ANTHROPIC_API_KEY:
        ai_unavailable_msg()
    else:
        if st.button("⚠️ Detect Risks", key="btn_risks", type="primary"):
            with st.spinner("Analyzing case..."):
                try:
                    risks = st.session_state.risk_service.detect_risks(context)
                    st.session_state.risks = risks
                    st.success(f"✅ Risk analysis complete — {len(risks)} flag(s) identified.")
                except Exception as exc:
                    st.error(f"Risk analysis failed: {exc}")

        if st.session_state.risks is not None:
            st.markdown("---")
            risks = st.session_state.risks

            if not risks:
                st.success("✅ No risk flags identified for this case.")
            else:
                # Group by severity for display
                high_risks = [r for r in risks if getattr(r, "severity", "").lower() == "high"]
                med_risks = [r for r in risks if getattr(r, "severity", "").lower() == "medium"]
                low_risks = [r for r in risks if getattr(r, "severity", "").lower() == "low"]

                if high_risks:
                    st.markdown(f"#### 🔴 High Severity ({len(high_risks)})")
                    for risk in high_risks:
                        with st.expander(
                            f"🔴 {getattr(risk, 'risk_name', 'Unknown risk')}",
                            expanded=True,
                        ):
                            st.markdown(f"**Evidence:** {getattr(risk, 'evidence', '')}")
                            st.markdown(f"**Explanation:** {getattr(risk, 'explanation', '')}")
                            st.caption(f"Source: `{getattr(risk, 'source', 'unknown')}`")

                if med_risks:
                    st.markdown(f"#### 🟡 Medium Severity ({len(med_risks)})")
                    for risk in med_risks:
                        with st.expander(
                            f"🟡 {getattr(risk, 'risk_name', 'Unknown risk')}",
                            expanded=False,
                        ):
                            st.markdown(f"**Evidence:** {getattr(risk, 'evidence', '')}")
                            st.markdown(f"**Explanation:** {getattr(risk, 'explanation', '')}")
                            st.caption(f"Source: `{getattr(risk, 'source', 'unknown')}`")

                if low_risks:
                    st.markdown(f"#### 🟢 Low Severity ({len(low_risks)})")
                    for risk in low_risks:
                        with st.expander(
                            f"🟢 {getattr(risk, 'risk_name', 'Unknown risk')}",
                            expanded=False,
                        ):
                            st.markdown(f"**Evidence:** {getattr(risk, 'evidence', '')}")
                            st.markdown(f"**Explanation:** {getattr(risk, 'explanation', '')}")
                            st.caption(f"Source: `{getattr(risk, 'source', 'unknown')}`")
        else:
            st.info("Click **Detect Risks** to run AI-powered risk analysis.")

# =============================================================
# TAB 6 — VALIDATION INSIGHTS
# =============================================================

with tabs[5]:
    st.markdown("### Data Validation Insights")
    st.caption(
        "Compares clinical notes against structured data records (visits, activities, medications) "
        "to surface confirmations, discrepancies, and gaps."
    )

    if not config.ANTHROPIC_API_KEY:
        ai_unavailable_msg()
    else:
        if st.button("🔍 Run Validation", key="btn_validation", type="primary"):
            with st.spinner("Analyzing case..."):
                try:
                    obs_list = st.session_state.validation_service.run_validation(context)
                    st.session_state.validation = obs_list
                    st.success(f"✅ Validation complete — {len(obs_list)} observation(s) found.")
                except Exception as exc:
                    st.error(f"Validation failed: {exc}")

        if st.session_state.validation is not None:
            st.markdown("---")
            obs_list = st.session_state.validation

            if not obs_list:
                st.info("No observations returned. Ensure the case has both notes and structured data.")
            else:
                # Group by severity
                sev_order = ["High", "Medium", "Low", "Info"]
                sev_icons = {"High": "🔴", "Medium": "🟡", "Low": "🟢", "Info": "🔵"}

                for sev in sev_order:
                    sev_obs = [o for o in obs_list if getattr(o, "severity", "Info") == sev]
                    if not sev_obs:
                        continue

                    icon = sev_icons.get(sev, "⬜")
                    st.markdown(f"#### {icon} {sev} ({len(sev_obs)})")

                    for obs in sev_obs:
                        obs_label = getattr(obs, "observation", "Observation")
                        notes_say = getattr(obs, "notes_suggest", "Not documented.")
                        data_shows = getattr(obs, "data_shows", "Not in structured data.")

                        with st.expander(
                            f"{icon} {obs_label}",
                            expanded=(sev in ("High", "Medium")),
                        ):
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.markdown("**📝 Notes say:**")
                                st.info(notes_say)
                            with col_b:
                                st.markdown("**🗄️ Data shows:**")
                                st.info(data_shows)
        else:
            st.info("Click **Run Validation** to compare notes against structured records.")

# =============================================================
# TAB 7 — ASK CASEAI (Q&A)
# =============================================================

with tabs[6]:
    st.markdown("### Ask CaseAI")
    st.caption(
        "Ask any question about this specific case. Answers are grounded strictly in "
        "the documented case data — no speculation or external knowledge."
    )

    if not config.ANTHROPIC_API_KEY:
        ai_unavailable_msg()
    else:
        # Suggested question buttons
        st.markdown("**💡 Suggested Questions:**")
        suggested = QAService.get_suggested_questions()

        cols_suggestions = st.columns(2)
        for i, q in enumerate(suggested):
            col = cols_suggestions[i % 2]
            if col.button(q, key=f"suggested_q_{i}", use_container_width=True):
                # Auto-populate and trigger Q&A
                with st.spinner("Analyzing case..."):
                    try:
                        answer = st.session_state.qa_service.answer_question(context, q)
                        st.session_state.chat_history.append({"role": "user", "content": q})
                        st.session_state.chat_history.append({"role": "assistant", "content": answer})
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Q&A failed: {exc}")

        st.markdown("---")

        # Chat history display
        chat_history = st.session_state.chat_history
        if chat_history:
            st.markdown("**Conversation:**")
            for msg in chat_history:
                if msg["role"] == "user":
                    st.markdown(
                        f'<div class="chat-user">👤 <strong>You:</strong> {msg["content"]}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f'<div class="chat-assistant">🤖 <strong>CaseAI:</strong><br>{msg["content"]}</div>',
                        unsafe_allow_html=True,
                    )
            st.markdown("<br>", unsafe_allow_html=True)

        # Question input
        with st.form(key="qa_form", clear_on_submit=True):
            user_question = st.text_input(
                "Your question:",
                placeholder="e.g., What medications is the patient currently taking?",
                key="qa_input",
            )
            col_submit, col_clear_chat = st.columns([2, 1])
            with col_submit:
                submitted = st.form_submit_button(
                    "Ask CaseAI ➤", type="primary", use_container_width=True
                )
            with col_clear_chat:
                clear_chat = st.form_submit_button(
                    "Clear Chat", use_container_width=True
                )

        if submitted and user_question.strip():
            with st.spinner("Analyzing case..."):
                try:
                    answer = st.session_state.qa_service.answer_question(context, user_question.strip())
                    st.session_state.chat_history.append(
                        {"role": "user", "content": user_question.strip()}
                    )
                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": answer}
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"Q&A failed: {exc}")

        if clear_chat:
            st.session_state.chat_history = []
            st.rerun()

# =============================================================
# TAB 8 — PRIORITY / WORKLIST
# =============================================================

with tabs[7]:
    st.markdown("### Priority Scoring & Worklist")
    st.caption(
        "Heuristic-based priority scoring. Scores cases from 0–100 based on engagement gaps, "
        "clinical risk indicators, and documentation status. No AI call required."
    )

    col_score_current, col_rank_all = st.columns([1, 1])

    with col_score_current:
        if st.button(
            f"📊 Score Priority: {meta.case_id}",
            key="btn_priority_single",
            type="primary",
            use_container_width=True,
        ):
            with st.spinner("Calculating priority score..."):
                try:
                    score = st.session_state.priority_service.score_case(context)
                    st.session_state.priority_score = score
                    st.success(
                        f"✅ Priority score calculated: {score.score}/100 ({score.urgency_label})"
                    )
                except Exception as exc:
                    st.error(f"Priority scoring failed: {exc}")

    with col_rank_all:
        if st.button(
            "📋 Rank All Cases (Worklist)",
            key="btn_priority_all",
            use_container_width=True,
        ):
            with st.spinner("Scoring all cases..."):
                try:
                    all_contexts = []
                    for c in st.session_state.case_list:
                        try:
                            ctx = st.session_state.case_service.get_case_context(c.case_id)
                            all_contexts.append(ctx)
                        except Exception:
                            pass

                    all_scores = st.session_state.priority_service.rank_cases(all_contexts)
                    st.session_state.all_priority_scores = all_scores
                    st.success(f"✅ Ranked {len(all_scores)} cases.")
                except Exception as exc:
                    st.error(f"Worklist generation failed: {exc}")

    st.markdown("---")

    # Current case priority display
    if st.session_state.priority_score:
        score_obj = st.session_state.priority_score
        score_val = score_obj.score
        urgency = score_obj.urgency_label

        urgency_colors = {
            "Critical": "#7f1d1d",
            "High": "#991b1b",
            "Medium": "#92400e",
            "Low": "#14532d",
        }
        urgency_bgs = {
            "Critical": "#fef2f2",
            "High": "#fef2f2",
            "Medium": "#fffbeb",
            "Low": "#f0fdf4",
        }
        color = urgency_colors.get(urgency, "#1e3a5f")
        bg = urgency_bgs.get(urgency, "#f8fafc")

        st.markdown(
            f"""
            <div style="background:{bg}; border:2px solid {color}; border-radius:10px;
                padding:1.25rem; margin-bottom:1rem;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <h3 style="margin:0; color:{color};">{score_obj.member_name}</h3>
                        <span style="color:#64748b; font-size:0.85rem;">{score_obj.case_id}</span>
                    </div>
                    <div style="text-align:center;">
                        <div style="font-size:2.5rem; font-weight:800; color:{color};">{score_val}</div>
                        <div style="font-size:0.8rem; color:{color}; font-weight:600;">/ 100 — {urgency}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(f"_{score_obj.explanation}_")

        if score_obj.factors:
            st.markdown("**Contributing Factors:**")
            for factor in score_obj.factors:
                st.markdown(f"- {factor}")

    # All cases worklist
    if st.session_state.all_priority_scores:
        st.markdown("---")
        st.markdown("### 📋 Full Case Worklist (Ranked by Priority)")

        import pandas as pd

        urgency_icon = {
            "Critical": "⚫",
            "High": "🔴",
            "Medium": "🟡",
            "Low": "🟢",
        }

        worklist_data = []
        for ps in st.session_state.all_priority_scores:
            icon = urgency_icon.get(ps.urgency_label, "⬜")
            worklist_data.append({
                "Rank": st.session_state.all_priority_scores.index(ps) + 1,
                "Case ID": ps.case_id,
                "Member Name": ps.member_name,
                "Score": ps.score,
                "Urgency": f"{icon} {ps.urgency_label}",
                "Top Factor": ps.factors[0] if ps.factors else "N/A",
            })

        worklist_df = pd.DataFrame(worklist_data)

        st.dataframe(
            worklist_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Score": st.column_config.ProgressColumn(
                    "Score",
                    help="Priority score from 0-100",
                    min_value=0,
                    max_value=100,
                ),
            },
        )

        st.caption(
            "⚫ Critical (76-100) | 🔴 High (51-75) | 🟡 Medium (26-50) | 🟢 Low (0-25)"
        )

# =============================================================
# TAB 9 — REPORTS DASHBOARD
# =============================================================

import pandas as pd  # already imported in tab 8 but kept here for clarity

with tabs[8]:
    st.markdown("### 📈 Reports Dashboard")
    st.caption(
        "Operational metrics across all cases and case managers. "
        "Data refreshes when you click a load button. "
        "In SQL mode, results come directly from SQL Server."
    )

    prod_svc  = st.session_state.get("productivity_service")
    bill_svc  = st.session_state.get("billing_service")
    act_svc   = st.session_state.get("activity_service")

    if not prod_svc or not bill_svc or not act_svc:
        st.warning("Services not initialised. Select a data mode in the sidebar to continue.")
    else:
        # ── Report navigation ────────────────────────────────────────────────
        report_section = st.radio(
            "Select report",
            ["Case Status Overview", "Last 24h Activity", "Productivity", "Billing Summary", "Referrals & Activity Trends"],
            horizontal=True,
            label_visibility="collapsed",
        )

        st.markdown("---")

        # ====================================================================
        # SECTION: CASE STATUS OVERVIEW
        # ====================================================================
        if report_section == "Case Status Overview":
            st.markdown("#### Case Status Overview")

            case_list = st.session_state.get("case_list", [])
            if not case_list:
                st.info("No cases loaded. Select a data mode and refresh.")
            else:
                # Compute status counts
                total      = len(case_list)
                active     = sum(1 for c in case_list if (c.status or "").lower() == "active")
                open_count = sum(1 for c in case_list if (c.status or "").lower() == "open")
                closed     = sum(1 for c in case_list if (c.status or "").lower() == "closed")
                discharged = sum(1 for c in case_list if (c.status or "").lower() == "discharged")
                unassigned_cases = [c for c in case_list if not c.assigned_nurse]
                unassigned = len(unassigned_cases)

                # Top metric row
                m1, m2, m3, m4, m5, m6 = st.columns(6)
                m1.metric("Total Cases",  total)
                m2.metric("Active",       active,     delta=None)
                m3.metric("Open",         open_count)
                m4.metric("Discharged",   discharged)
                m5.metric("Closed",       closed)
                m6.metric("Unassigned",   unassigned,
                          delta=f"{unassigned} need assignment" if unassigned else None,
                          delta_color="inverse")

                st.markdown("")

                # Status distribution chart
                status_counts = {}
                for c in case_list:
                    s = (c.status or "Unknown").title()
                    status_counts[s] = status_counts.get(s, 0) + 1

                chart_df = pd.DataFrame(
                    list(status_counts.items()), columns=["Status", "Count"]
                ).set_index("Status")
                st.bar_chart(chart_df, use_container_width=True, height=220)

                # Unassigned cases table
                if unassigned_cases:
                    st.markdown("---")
                    st.markdown(
                        f"#### ⚠️ Unassigned Cases ({unassigned})"
                        "  — _These cases require a case manager assignment_"
                    )
                    unassigned_data = [
                        {
                            "Case ID":       c.case_id,
                            "Member Name":   c.member_name,
                            "Status":        c.status or "—",
                            "Case Type":     c.case_type or "—",
                            "Open Date":     c.open_date or "—",
                            "Last Contact":  c.last_contact_date or "Not recorded",
                            "Priority":      c.priority_label or "—",
                        }
                        for c in unassigned_cases
                    ]
                    st.dataframe(
                        pd.DataFrame(unassigned_data),
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.success("✅ All cases have an assigned case manager.")

                # Full case breakdown table
                st.markdown("---")
                st.markdown("#### Full Case Breakdown")
                all_cases_data = [
                    {
                        "Case ID":       c.case_id,
                        "Member":        c.member_name,
                        "Status":        c.status or "—",
                        "Type":          c.case_type or "—",
                        "Assigned To":   c.assigned_nurse or "⚠️ Unassigned",
                        "Open Date":     c.open_date or "—",
                        "Discharge":     c.discharge_date or "—",
                        "Last Contact":  c.last_contact_date or "—",
                        "Priority":      c.priority_label or "—",
                    }
                    for c in case_list
                ]
                st.dataframe(
                    pd.DataFrame(all_cases_data),
                    use_container_width=True,
                    hide_index=True,
                )

        # ====================================================================
        # SECTION: LAST 24H ACTIVITY
        # ====================================================================
        elif report_section == "Last 24h Activity":
            st.markdown("#### Last 24 Hours Activity")

            if st.button("🔄 Load Activity Snapshot", key="btn_load_24h", type="primary"):
                with st.spinner("Loading activity data..."):
                    try:
                        summary = act_svc.get_last_24h_summary()
                        st.session_state.report_activity_summary = summary
                    except Exception as exc:
                        st.error(f"Failed to load activity data: {exc}")

            summary = st.session_state.get("report_activity_summary")
            if summary:
                if summary.is_simulated:
                    st.info(
                        "📋 **Demo mode:** This snapshot is simulated from the most recent records "
                        "in the sample dataset. In SQL mode, these counts reflect real-time data."
                    )

                st.markdown(f"*As of {summary.as_of}*")
                st.markdown("")

                a1, a2, a3, a4, a5 = st.columns(5)
                a1.metric("📓 Journal Entries",    summary.journal_entries)
                a2.metric("📋 Progress Notes",     summary.progress_notes)
                a3.metric("📨 New Referrals",       summary.new_referrals)
                a4.metric("📄 Care Plan Updates",   summary.care_plan_updates)
                a5.metric("📞 Phone Outreach",      summary.phone_outreach_count)

                st.markdown("")
                total_activity = (
                    summary.journal_entries + summary.progress_notes +
                    summary.new_referrals + summary.care_plan_updates +
                    summary.phone_outreach_count
                )
                st.markdown(
                    f"<div style='background:#f0f9ff; border-left:4px solid #0369a1; "
                    f"padding:0.75rem 1rem; border-radius:6px; color:#0c4a6e;'>"
                    f"<strong>Total interactions in last 24h: {total_activity}</strong>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.info("Click **Load Activity Snapshot** to fetch current data.")

        # ====================================================================
        # SECTION: PRODUCTIVITY
        # ====================================================================
        elif report_section == "Productivity":
            st.markdown("#### TCM Daily Productivity Report")
            st.caption(
                "Displays daily service counts per case manager. "
                "In SQL mode: queries TCM_Daily_Productivity stored procedure or "
                "daily_productivity table. In demo mode: uses sample CSV data."
            )

            # Filters
            f1, f2, f3 = st.columns([1, 1, 1])
            with f1:
                start_default = pd.Timestamp.today().replace(day=1).date()
                prod_start = st.date_input("From date", value=start_default, key="prod_start")
            with f2:
                prod_end = st.date_input("To date", value=pd.Timestamp.today().date(), key="prod_end")
            with f3:
                try:
                    mgr_list = ["All"] + prod_svc.get_case_managers()
                except Exception:
                    mgr_list = ["All"]
                selected_mgr = st.selectbox("Case Manager", mgr_list, key="prod_mgr")

            if st.button("📊 Load Productivity Report", key="btn_prod", type="primary"):
                with st.spinner("Loading productivity data..."):
                    try:
                        mgr_filter = None if selected_mgr == "All" else selected_mgr
                        records = prod_svc.get_productivity(
                            start_date=prod_start.isoformat(),
                            end_date=prod_end.isoformat(),
                            case_manager=mgr_filter,
                        )
                        st.session_state.report_productivity = records
                    except Exception as exc:
                        st.error(f"Failed to load productivity data: {exc}")

            records = st.session_state.get("report_productivity")
            if records is not None:
                if not records:
                    st.warning("No productivity records found for the selected filters.")
                else:
                    # Summary metrics
                    total_tcm   = sum(r.tcm_count for r in records)
                    total_fcm   = sum(r.fcm_count for r in records)
                    total_tasks = sum(r.task_count for r in records)
                    total_hrs   = sum(r.hours_worked for r in records)
                    total_ph    = sum(r.phone_outreach_count for r in records)
                    total_hv    = sum(r.home_visit_count for r in records)

                    sm1, sm2, sm3, sm4, sm5, sm6 = st.columns(6)
                    sm1.metric("TCM Services",   total_tcm)
                    sm2.metric("FCM Services",   total_fcm)
                    sm3.metric("Tasks",          total_tasks)
                    sm4.metric("Phone Outreach", total_ph)
                    sm5.metric("Home Visits",    total_hv)
                    sm6.metric("Total Hours",    f"{total_hrs:.1f}h")

                    st.markdown("")

                    # Daily table
                    prod_rows = [
                        {
                            "Date":           r.report_date,
                            "Case Manager":   r.case_manager,
                            "Cases":          r.total_cases,
                            "TCM":            r.tcm_count,
                            "FCM":            r.fcm_count,
                            "Tasks":          r.task_count,
                            "Assessments":    r.assessment_count,
                            "Phone Outreach": r.phone_outreach_count,
                            "Home Visits":    r.home_visit_count,
                            "Hours":          r.hours_worked,
                        }
                        for r in records
                    ]
                    prod_df = pd.DataFrame(prod_rows)
                    st.dataframe(prod_df, use_container_width=True, hide_index=True)

                    st.markdown("---")
                    st.markdown("**Services by Case Manager (totals for period)**")

                    # Grouped bar chart: TCM + FCM + Tasks per manager
                    mgr_group = prod_df.groupby("Case Manager")[["TCM", "FCM", "Tasks", "Phone Outreach"]].sum()
                    st.bar_chart(mgr_group, use_container_width=True, height=280)

                    # Hours worked per manager
                    st.markdown("**Hours Worked by Case Manager**")
                    hrs_group = prod_df.groupby("Case Manager")[["Hours"]].sum()
                    st.bar_chart(hrs_group, use_container_width=True, height=220)
            else:
                st.info("Set filters and click **Load Productivity Report**.")

        # ====================================================================
        # SECTION: BILLING SUMMARY
        # ====================================================================
        elif report_section == "Billing Summary":
            st.markdown("#### Billing Summary by Case")

            # Show current rates
            with st.expander("ℹ️ Billing Rate Configuration", expanded=False):
                rates = bill_svc.get_rates()
                rc1, rc2, rc3, rc4 = st.columns(4)
                rc1.metric("0–30 days",  f"${rates['0-30 days']:.0f}/mo")
                rc2.metric("31–60 days", f"${rates['31-60 days']:.0f}/mo")
                rc3.metric("61–90 days", f"${rates['61-90 days']:.0f}/mo")
                rc4.metric(">90 days",   f"${rates['>90 days']:.0f}/mo (flat)")
                st.caption(
                    "To change rates, update BILLING_RATE_0_30 / BILLING_RATE_31_60 / "
                    "BILLING_RATE_61_90 / BILLING_RATE_GT_90 in your .env file and restart."
                )

            if st.button("💰 Compute Billing Summary", key="btn_billing", type="primary"):
                with st.spinner("Computing billing data..."):
                    try:
                        case_list = st.session_state.get("case_list", [])
                        summaries = bill_svc.compute_all(case_list)
                        st.session_state.report_billing = summaries
                    except Exception as exc:
                        st.error(f"Billing computation failed: {exc}")

            summaries = st.session_state.get("report_billing")
            if summaries is not None:
                if not summaries:
                    st.warning("No cases available for billing computation.")
                else:
                    # Grand total
                    grand_total = sum(s.total_billed for s in summaries)
                    bt1, bt2, bt3 = st.columns(3)
                    bt1.metric("Total Billed (All Cases)", f"${grand_total:,.2f}")
                    bt2.metric("Cases in '>90 day' Tier",
                               sum(1 for s in summaries if s.billing_tier == ">90"))
                    approaching = bill_svc.get_approaching_tier_change(summaries)
                    bt3.metric("Approaching Tier Change", len(approaching),
                               delta="within 5 days" if approaching else None,
                               delta_color="inverse" if approaching else "off")

                    # Approaching tier change alert
                    if approaching:
                        st.markdown("")
                        st.warning(
                            f"**{len(approaching)} case(s) will move to a higher billing tier within 5 days:**"
                        )
                        for s in approaching:
                            st.markdown(
                                f"- **{s.member_name}** ({s.case_id}) — "
                                f"currently in `{s.billing_tier}` tier, "
                                f"moves up in **{s.next_tier_days} day(s)**"
                            )

                    st.markdown("---")

                    # Full billing table
                    bill_rows = [
                        {
                            "Case ID":          s.case_id,
                            "Member":           s.member_name,
                            "Case Manager":     s.case_manager,
                            "Open Date":        s.open_date,
                            "Age (days)":       s.case_age_days,
                            "Months Active":    s.months_active,
                            "Billing Tier":     s.billing_tier,
                            "Monthly Rate ($)": f"${s.monthly_rate:.0f}",
                            "Total Billed ($)": s.total_billed,
                        }
                        for s in summaries
                    ]
                    bill_df = pd.DataFrame(bill_rows)
                    st.dataframe(
                        bill_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Total Billed ($)": st.column_config.NumberColumn(
                                "Total Billed ($)",
                                format="$%.2f",
                            ),
                        },
                    )

                    # Billing by case manager
                    st.markdown("---")
                    st.markdown("**Total Billed by Case Manager**")
                    by_mgr = bill_svc.get_billing_by_manager(summaries)
                    mgr_df = pd.DataFrame(
                        list(by_mgr.items()), columns=["Case Manager", "Total Billed ($)"]
                    ).set_index("Case Manager")
                    st.bar_chart(mgr_df, use_container_width=True, height=240)

                    # Billing by tier
                    st.markdown("**Cases per Billing Tier**")
                    tiers = bill_svc.get_by_tier(summaries)
                    tier_counts = {t: len(v) for t, v in tiers.items()}
                    tier_df = pd.DataFrame(
                        list(tier_counts.items()), columns=["Tier", "Cases"]
                    ).set_index("Tier")
                    st.bar_chart(tier_df, use_container_width=True, height=200)
            else:
                st.info("Click **Compute Billing Summary** to generate the report.")

        # ====================================================================
        # SECTION: REFERRALS & ACTIVITY TRENDS
        # ====================================================================
        elif report_section == "Referrals & Activity Trends":
            st.markdown("#### Referrals & Activity Trends")

            ref_col, trend_col = st.columns([1, 1])

            with ref_col:
                st.markdown("**Referral Filters**")
                r1, r2 = st.columns(2)
                with r1:
                    ref_start = st.date_input(
                        "From", value=pd.Timestamp("2024-01-01").date(), key="ref_start"
                    )
                with r2:
                    ref_end = st.date_input(
                        "To", value=pd.Timestamp.today().date(), key="ref_end"
                    )
                ref_status = st.selectbox(
                    "Status", ["All", "pending", "completed", "cancelled"], key="ref_status"
                )

            with trend_col:
                st.markdown("**Activity Trend Range**")
                trend_days = st.selectbox(
                    "Show last N days",
                    [30, 60, 90],
                    key="trend_days",
                )

            if st.button("📨 Load Referrals & Trends", key="btn_refs", type="primary"):
                with st.spinner("Loading referrals and activity trends..."):
                    try:
                        status_filter = None if ref_status == "All" else ref_status
                        refs = act_svc.get_referrals(
                            start_date=ref_start.isoformat(),
                            end_date=ref_end.isoformat(),
                            status=status_filter,
                        )
                        st.session_state.report_referrals = refs

                        from datetime import date, timedelta
                        trend_start = (date.today() - timedelta(days=trend_days)).isoformat()
                        trend = act_svc.get_activity_trend(
                            start_date=trend_start,
                            end_date=date.today().isoformat(),
                        )
                        st.session_state.report_activity_trend = trend
                    except Exception as exc:
                        st.error(f"Failed to load referral/trend data: {exc}")

            refs    = st.session_state.get("report_referrals")
            trend   = st.session_state.get("report_activity_trend")

            if refs is not None:
                st.markdown("---")
                st.markdown(f"**Referrals ({len(refs)} records)**")

                if refs:
                    # Summary metrics
                    pending   = sum(1 for r in refs if r.status == "pending")
                    completed = sum(1 for r in refs if r.status == "completed")
                    rm1, rm2, rm3 = st.columns(3)
                    rm1.metric("Total Referrals", len(refs))
                    rm2.metric("Pending",  pending,  delta=f"{pending} awaiting action" if pending else None, delta_color="inverse")
                    rm3.metric("Completed", completed)

                    ref_rows = [
                        {
                            "Referral ID":    r.referral_id,
                            "Case ID":        r.case_id,
                            "Date":           r.referral_date,
                            "Referred By":    r.referred_by,
                            "Type":           r.referral_type,
                            "Status":         r.status,
                            "Details":        r.details[:80] + "..." if len(r.details) > 80 else r.details,
                        }
                        for r in refs
                    ]
                    st.dataframe(
                        pd.DataFrame(ref_rows),
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.info("No referrals found for the selected filters.")

            if trend is not None:
                st.markdown("---")
                st.markdown(f"**Activity Trend (last {trend_days} days)**")
                if trend:
                    trend_rows = [
                        {
                            "Date":           t.activity_date,
                            "Journal Entries": t.journal_count,
                            "Progress Notes": t.progress_note_count,
                            "Total Activities": t.total_activities,
                        }
                        for t in trend
                    ]
                    trend_df = pd.DataFrame(trend_rows).set_index("Date")
                    st.line_chart(
                        trend_df[["Journal Entries", "Progress Notes", "Total Activities"]],
                        use_container_width=True,
                        height=260,
                    )
                else:
                    st.info("No activity records found for the selected date range.")

                # Monthly referral trend
                st.markdown("---")
                st.markdown("**Monthly Referral Volume (last 6 months)**")
                try:
                    monthly = act_svc.get_monthly_referral_counts(months=6)
                    if any(v > 0 for v in monthly.values()):
                        monthly_df = pd.DataFrame(
                            list(monthly.items()), columns=["Month", "Referrals"]
                        ).set_index("Month")
                        st.bar_chart(monthly_df, use_container_width=True, height=220)
                    else:
                        st.info("No referral data available for the past 6 months.")
                except Exception as exc:
                    st.warning(f"Could not load monthly referral trend: {exc}")

            if refs is None and trend is None:
                st.info("Click **Load Referrals & Trends** to populate this section.")

# ============================================================
# FOOTER
# ============================================================

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(
    """
    <div style="text-align:center; padding:1rem; border-top:1px solid #e2e8f0;
        font-size:0.78rem; color:#94a3b8; margin-top:2rem;">
        CaseAI Copilot v1.0.0 &nbsp;|&nbsp;
        AI-Assisted Operational Review — Not a Clinical Decision System &nbsp;|&nbsp;
        All outputs require human review before action &nbsp;|&nbsp;
        Powered by Anthropic Claude
    </div>
    """,
    unsafe_allow_html=True,
)
