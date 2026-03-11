"""
Case Management AI Summarization Demo
A proof-of-concept Streamlit application demonstrating AI-powered
summarization of clinical nursing notes.
"""
import streamlit as st
import pandas as pd
import anthropic
import os
from datetime import datetime
# ── Page configuration ────────────────────────────────────────────────────────
st.set_page_config(
 page_title="CaseAI — Clinical Summary Demo",
 page_icon=" ",
 layout="wide",
 initial_sidebar_state="expanded",
)
# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
 @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&display=swap');
 html, body, [class*="css"] {
 font-family: 'DM Sans', sans-serif;
 }
 /* Sidebar */
 section[data-testid="stSidebar"] {
 background: #0f1923;
 border-right: 1px solid #1e2d3d;
 }
 section[data-testid="stSidebar"] * {
 color: #c9d6df !important;
 }
 /* Main background */
 .main .block-container {
 background: #f5f7fa;
 padding-top: 2rem;
 }
 /* Dashboard card */
 .case-card {
 background: white;
 border: 1px solid #e2e8f0;
 border-left: 4px solid #2563eb;
 border-radius: 8px;
 padding: 1rem 1.25rem;
 margin-bottom: 0.75rem;
 transition: box-shadow 0.2s;
 }
 .case-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
 .case-card h4 {
 font-family: 'DM Serif Display', serif;
 font-size: 1.05rem;
 color: #1e293b;
 margin: 0 0 0.25rem 0;
 }
 .case-card .meta { font-size: 0.8rem; color: #64748b; }
 .case-card .badge {
 display: inline-block;
 background: #eff6ff;
 color: #2563eb;
 border-radius: 20px;
 padding: 2px 10px;
 font-size: 0.75rem;
 font-weight: 600;
 margin-top: 0.4rem;
 }
 /* Note entry */
 .note-entry {
 background: #f8fafc;
 border: 1px solid #e2e8f0;
 border-radius: 6px;
 padding: 0.75rem 1rem;
 margin-bottom: 0.5rem;
 font-size: 0.875rem;
 line-height: 1.6;
 color: #374151;
 }
 .note-date { font-weight: 600; color: #2563eb; font-size: 0.78rem; margin-bottom: 4px; }
 /* Summary output */
 .summary-box {
 background: white;
 border: 1px solid #bbdefb;
 border-left: 5px solid #1565c0;
 border-radius: 8px;
 padding: 1.5rem;
 margin-top: 1rem;
 }
 .summary-box h3 {
 font-family: 'DM Serif Display', serif;
 color: #1565c0;
 margin-top: 0;
 }
 .summary-content { line-height: 1.8; color: #1e293b; white-space: pre-wrap; }
 /* Section header */
 .section-header {
 font-family: 'DM Serif Display', serif;
 font-size: 1.3rem;
 color: #0f172a;
 border-bottom: 2px solid #2563eb;
 padding-bottom: 0.4rem;
 margin-bottom: 1rem;
 }
 /* Stat metric */
 .stat-box {
 background: white;
 border: 1px solid #e2e8f0;
 border-radius: 8px;
 padding: 1rem;
 text-align: center;
 }
 .stat-box .stat-num { font-size: 2rem; font-weight: 700; color: #2563eb; }
 .stat-box .stat-label { font-size: 0.8rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; }
 /* Header banner */
 .app-header {
 background: linear-gradient(135deg, #0f1923 0%, #1e3a5f 100%);
 color: white;
 padding: 1.25rem 1.75rem;
 border-radius: 10px;
 margin-bottom: 1.5rem;
 display: flex;
 align-items: center;
 gap: 1rem;
 }
 .app-header h1 {
 font-family: 'DM Serif Display', serif;
 font-size: 1.6rem;
 margin: 0;
 color: white;
 }
 .app-header .subtitle { font-size: 0.85rem; color: #93c5fd; margin: 0; }
 div[data-testid="stButton"] button {
 background: #2563eb;
 color: white;
 border: none;
 border-radius: 6px;
 padding: 0.5rem 1.25rem;
 font-weight: 600;
 font-size: 0.9rem;
 }
 div[data-testid="stButton"] button:hover { background: #1d4ed8; }
</style>
""", unsafe_allow_html=True)
# ── Data loading ───────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
 cases = pd.read_csv("data/cases.csv")
 notes = pd.read_csv("data/notes.csv")
 return cases, notes
cases_df, notes_df = load_data()
# Count notes per case
note_counts = notes_df.groupby("case_id").size().reset_index(name="note_count")
cases_df = cases_df.merge(note_counts, on="case_id", how="left").fillna(0)
cases_df["note_count"] = cases_df["note_count"].astype(int)
# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
 st.markdown("## CaseAI Demo")
 st.markdown("*Clinical Summarization Proof-of-Concept*")
 st.divider()
 st.markdown("### Select a Case")
 case_options = {
 f"{row['case_id']} — {row['patient_name']}": row["case_id"]
 for _, row in cases_df.iterrows()
 }
 selected_label = st.radio("Cases", list(case_options.keys()), label_visibility="collapsed")
 selected_case_id = case_options[selected_label]
 st.divider()
 st.markdown("### AI Settings")
 ai_model = st.selectbox(
 "Model",
 ["claude-sonnet-4-20250514", "claude-haiku-4-5-20251001"],
 help="Sonnet = higher quality. Haiku = faster & cheaper."
 )
 api_key = st.text_input(
 "Anthropic API Key",
 type="password",
 placeholder="sk-ant-...",
 help="Your key is used only for this session and never stored."
 )
 st.divider()
 st.caption("Demo build — March 2026")
 st.caption("Data is fictional for illustrative purposes only.")
# ── Main area ─────────────────────────────────────────────────────────────────
# Header
st.markdown("""
<div class="app-header">
 <span style="font-size:2rem;"> </span>
 <div>
 <h1>CaseAI — Clinical Note Summarization</h1>
 <p class="subtitle">Proof-of-concept · AI-powered case review for nurse case managers</p>
 </div>
</div>
""", unsafe_allow_html=True)
# ── Dashboard stats ────────────────────────────────────────────────────────────
total_notes = len(notes_df)
col1, col2, col3, col4 = st.columns(4)
with col1:
 st.markdown(f"""<div class="stat-box">
 <div class="stat-num">{len(cases_df)}</div>
 <div class="stat-label">Active Cases</div>
 </div>""", unsafe_allow_html=True)
with col2:
 st.markdown(f"""<div class="stat-box">
 <div class="stat-num">{total_notes}</div>
 <div class="stat-label">Total Notes</div>
 </div>""", unsafe_allow_html=True)
with col3:
 avg_notes = round(total_notes / len(cases_df), 1)
 st.markdown(f"""<div class="stat-box">
 <div class="stat-num">{avg_notes}</div>
 <div class="stat-label">Avg Notes / Case</div>
 </div>""", unsafe_allow_html=True)
with col4:
 st.markdown(f"""<div class="stat-box">
 <div class="stat-num">~2 sec</div>
 <div class="stat-label">AI Summary Time</div>
 </div>""", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)
# ── Two-column layout ──────────────────────────────────────────────────────────
left_col, right_col = st.columns([1, 2], gap="large")
# LEFT — Case list
with left_col:
 st.markdown('<div class="section-header"> Case List</div>', unsafe_allow_html=True)
 for _, row in cases_df.iterrows():
    is_selected = row["case_id"] == selected_case_id
    border_color = "#2563eb" if is_selected else "#cbd5e1"
    bg_color = "#eff6ff" if is_selected else "white"
    st.markdown(f"""
    <div class="case-card" style="border-left-color:{border_color}; background:{bg_color};">
    <h4>{row['patient_name']}</h4>
    <div class="meta">ID: {row['case_id']} &nbsp;|&nbsp; {row['assigned_nurse']}</div>
    <div class="meta" style="margin-top:4px; font-size:0.78rem; color:#475569;">{row['diagnosis']}</div>
    <span class="badge"> {row['note_count']} notes</span>
    </div>
    """, unsafe_allow_html=True)
# RIGHT — Case detail
with right_col:
 case_info = cases_df[cases_df["case_id"] == selected_case_id].iloc[0]
 case_notes = notes_df[notes_df["case_id"] == selected_case_id].copy()
 if "note_date" in case_notes.columns:
    case_notes = case_notes.sort_values("note_date")
 st.markdown(f'<div class="section-header"> {case_info["patient_name"]}</div>', unsafe_allow_html=True)
 # Case metadata
 info_cols = st.columns(3)
 with info_cols[0]:
    st.markdown(f"**Case ID:** `{case_info['case_id']}`")
    st.markdown(f"**DOB:** {case_info['dob']}")
 with info_cols[1]:
    st.markdown(f"**Nurse:** {case_info['assigned_nurse']}")
    st.markdown(f"**Notes:** {case_info['note_count']}")
 with info_cols[2]:
    st.markdown(f"**Diagnosis:**")
    st.markdown(f"_{case_info['diagnosis']}_")
 st.divider()
 # AI Summary button
 btn_col, status_col = st.columns([1, 3])
 with btn_col:
    generate_clicked = st.button(" Generate AI Summary", use_container_width=True)
 if generate_clicked:
    if not api_key:
        st.error(" Please enter your Anthropic API key in the sidebar to generate summaries.")
    else:
        all_notes_text = "\n\n".join(
            f"[{row.get('note_date', 'No date')}] {row['note']}"
            for _, row in case_notes.iterrows()
        )
        prompt = f"""You are a clinical case management AI assistant. Your job is to read nursing progress notes and generate a concise, structured clinical summary for nurse case managers.
PATIENT: {case_info['patient_name']}
DIAGNOSIS: {case_info['diagnosis']}
TOTAL NOTES: {len(case_notes)}
NURSING NOTES:
{all_notes_text}
Generate a structured summary using EXACTLY this format. Be concise — 5 to 8 bullet points total across all sections. Use plain language that a case manager would find useful at a glance.
Patient Status
• [key clinical condition, functional status, and how the patient is doing overall]
• [relevant vital signs trends, lab findings, or significant changes]
Follow Ups
• [scheduled appointments, pending referrals, or outstanding consultations]
• [any next clinical steps or monitoring planned]
Recommendations
• [care coordination actions or patient/family education needs]
• [risk factors to monitor or interventions to consider]
Keep each bullet to 1–2 sentences. Do not invent information not present in the notes. Use clinical but accessible language."""
        with st.spinner(" AI is reading all notes and generating summary…"):
            try:
                client = anthropic.Anthropic(api_key=api_key)
                response = client.messages.create(
                    model=ai_model,
                    max_tokens=800,
                    messages=[{"role": "user", "content": prompt}]
                )
                summary_text = response.content[0].text
                st.markdown(f"""
                <div class="summary-box">
                <h3> AI-Generated Case Summary</h3>
                <div style="font-size:0.78rem; color:#64748b; margin-bottom:0.75rem;">
                Generated {datetime.now().strftime("%B %d, %Y at %I:%M %p")} &nbsp;·&nbsp;
                Model: {ai_model} &nbsp;·&nbsp;
                Based on {len(case_notes)} notes
                </div>
                <div class="summary-content">{summary_text}</div>
                </div>
                """, unsafe_allow_html=True)
                with st.expander(" Token usage"):
                    st.write(f"- Input tokens: {response.usage.input_tokens}")
                    st.write(f"- Output tokens: {response.usage.output_tokens}")
            except anthropic.AuthenticationError:
                st.error(" Invalid API key. Please check your Anthropic API key in the sidebar.")
            except anthropic.RateLimitError:
                st.error(" Rate limit reached. Please wait a moment and try again.")
            except Exception as e:
                st.error(f" Error calling AI: {str(e)}")
 st.divider()
 # Raw notes
 with st.expander(f" View All Raw Notes ({len(case_notes)} entries)", expanded=False):
    for _, row in case_notes.iterrows():
        date_str = row.get("note_date", "")
        st.markdown(
           f"""
           <div class="note-entry">
           <div class="note-date"> {date_str}</div>
           {row['note']}
           </div>
           """,
           unsafe_allow_html=True)
# ── Footer ─────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
   """
   <div style="text-align:center; color:#94a3b8; font-size:0.78rem; padding:1rem 0;">
   CaseAI Proof-of-Concept &nbsp;·&nbsp; Data is entirely fictional &nbsp;·&nbsp; 
   For demonstration purposes only &nbsp;·&nbsp; Not for clinical use
   </div>
   """,
   unsafe_allow_html=True)