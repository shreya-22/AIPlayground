# CaseAI Copilot

**Enterprise-grade AI-powered healthcare case review assistant for case managers and care coordinators.**

---

## What Problem Does It Solve?

Healthcare case managers often manage dozens of active cases simultaneously. Each case contains scattered information across clinical notes, visit records, medication histories, and activity logs. Manually reviewing all this context before a patient call or care conference is time-consuming and error-prone.

CaseAI Copilot brings AI-powered intelligence directly into the case review workflow:
- Instantly surfaces the most important information from a case
- Identifies documentation gaps, missed follow-ups, and risk flags
- Cross-checks notes against structured records to find discrepancies
- Answers specific questions about a case grounded in the actual data
- Ranks cases by urgency so managers know where to focus first

---

## Key Features

- **AI Case Summary** — Structured narrative summary across all case data
- **Chronological Timeline** — AI-extracted timeline of all case events
- **Risk Detection** — Identifies engagement, medication, documentation, and support risks
- **Data Validation** — Cross-checks notes vs. structured records for discrepancies
- **Grounded Q&A** — Ask any question about a case; answers cite the source data
- **Priority Scoring** — Heuristic urgency scoring (0-100) across all cases
- **Worklist View** — Ranked worklist to help managers triage their caseload
- **Demo + SQL Mode** — Works with bundled sample data or a SQL Server database
- **Safety First** — AI is framed as operational assistant, not clinical decision maker

---

## Architecture Overview

```
app.py (Streamlit UI)
    |
    ├── config/
    │   ├── settings.py      -- Environment config & AppConfig
    │   └── prompts.py       -- All AI prompt templates
    |
    ├── services/
    │   ├── case_service.py  -- Case data orchestration
    │   ├── sql_service.py   -- MockDataSource & SQLDataSource
    │   ├── ai_service.py    -- Anthropic Claude API wrapper
    │   ├── risk_service.py  -- Risk flag detection
    │   ├── timeline_service.py -- Timeline generation
    │   ├── validation_service.py -- Notes vs. data cross-check
    │   ├── qa_service.py    -- Grounded Q&A
    │   └── priority_service.py  -- Heuristic scoring
    |
    ├── models/
    │   ├── schemas.py       -- All domain dataclasses
    │   └── dto.py           -- Text formatters for prompt injection
    |
    ├── utils/
    │   ├── formatting.py    -- Markdown output formatters
    │   ├── guards.py        -- SQL safety guard & input validation
    │   ├── helpers.py       -- Date utilities & text helpers
    │   └── logger.py        -- Structured audit logging
    |
    └── data/
        └── sample_*.csv     -- Sample healthcare case data
```

---

## Setup Instructions

### Prerequisites

- Python 3.10 or higher
- pip
- An Anthropic API key (for AI features)
- SQL Server + ODBC Driver 17 (optional, for SQL mode only)

### Step 1: Clone or download the project

```bash
cd caseai-copilot
```

### Step 2: Create a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
ANTHROPIC_API_KEY=sk-ant-your-key-here
APP_MODE=demo
LOG_LEVEL=INFO
```

### Step 5: Run the app

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`.

---

## Environment Variable Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | For AI features | — | Your Anthropic API key |
| `APP_MODE` | No | `demo` | `demo` or `sql` |
| `DB_SERVER` | SQL mode only | — | SQL Server hostname |
| `DB_DATABASE` | SQL mode only | — | Database name |
| `DB_USERNAME` | SQL mode only | — | Database username |
| `DB_PASSWORD` | SQL mode only | — | Database password |
| `DB_DRIVER` | No | `ODBC Driver 17 for SQL Server` | ODBC driver name |
| `LOG_LEVEL` | No | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Running in Demo Mode

Demo mode requires no database — it uses the bundled CSV files in `data/`.

```env
APP_MODE=demo
ANTHROPIC_API_KEY=sk-ant-your-key
```

**What you get:**
- 5 pre-built sample cases with realistic clinical data
- All AI features work with real Anthropic API calls
- No SQL Server needed

**Without an API key:**
- You can still view raw case data (notes, visits, activities, medications)
- All AI features (summary, timeline, risk, Q&A) will show a "no API key" message

---

## Running in SQL Mode

SQL mode connects to your SQL Server database.

```env
APP_MODE=sql
ANTHROPIC_API_KEY=sk-ant-your-key
DB_SERVER=your-server.database.windows.net
DB_DATABASE=CaseManagement
DB_USERNAME=case_reader
DB_PASSWORD=your-password
DB_DRIVER=ODBC Driver 17 for SQL Server
```

**Required database tables:**
- `cases` — case_id, member_name, status, open_date, discharge_date, assigned_nurse, last_contact_date, case_type, priority_label
- `case_notes` — note_id, case_id, note_date, note_author, note_text
- `patient_visits` — visit_id, case_id, visit_date, visit_type, provider_name, outcome
- `case_activities` — activity_id, case_id, activity_date, activity_type, activity_status, details
- `medication_events` — med_event_id, case_id, event_date, medication_name, event_type, details

**Fallback behavior:** If SQL connection fails, the app automatically falls back to demo mode with a warning message.

---

## Project Structure

```
caseai-copilot/
├── app.py                      # Main Streamlit application
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variable template
├── .gitignore                  # Git ignore rules
├── config/
│   ├── settings.py             # App configuration (AppConfig)
│   └── prompts.py              # All AI prompt templates
├── data/
│   ├── sample_cases.csv        # 5 sample case records
│   ├── sample_notes.csv        # Realistic clinical/operational notes
│   ├── sample_visits.csv       # Visit and appointment records
│   ├── sample_activity.csv     # Case management activities
│   └── sample_medication_events.csv  # Medication history
├── services/
│   ├── ai_service.py           # Anthropic Claude API wrapper
│   ├── case_service.py         # Case data orchestration
│   ├── sql_service.py          # Data sources (Mock + SQL)
│   ├── risk_service.py         # AI risk detection
│   ├── timeline_service.py     # AI timeline generation
│   ├── validation_service.py   # Notes vs. data cross-check
│   ├── qa_service.py           # Grounded Q&A
│   └── priority_service.py     # Heuristic priority scoring
├── models/
│   ├── schemas.py              # Domain dataclasses
│   └── dto.py                  # Text formatters for prompts
├── utils/
│   ├── formatting.py           # Markdown output formatters
│   ├── guards.py               # SQL guard & input validation
│   ├── helpers.py              # Date/text utilities
│   └── logger.py               # Structured logging
└── docs/
    ├── architecture.md         # System architecture guide
    ├── prompt_strategy.md      # Prompt design documentation
    └── future_enhancements.md  # Roadmap and future features
```

---

## Sample Use Cases / Demo Scenarios

### Scenario 1: CASE001 — Margaret Wilson (Post-Surgical, Medium)
Best for demonstrating: AI Summary, Timeline, and Medication validation.
- Successful post-surgical recovery story
- Medication adherence gap that was caught and resolved
- Clean documentation across notes and structured data

### Scenario 2: CASE002 — Robert Chen (Chronic Disease, High)
Best for demonstrating: Risk Analysis, Gaps, and Q&A.
- Multiple failed outreach attempts
- Caregiver fatigue documented
- Medication adherence failures across multiple drugs
- Social work referral placed but never followed up

### Scenario 3: CASE003 — Dorothy Patterson (Cardiac Rehab, Discharged)
Best for demonstrating: Data Validation Insights.
- Excellent compliance and documented outcomes
- Contradiction: discharge occurred but no post-discharge follow-up in structured data
- Good test case for notes vs. structured data cross-comparison

### Scenario 4: CASE004 — James Thompson (Complex Care, Critical)
Best for demonstrating: Priority Scoring, Risk Analysis.
- Highest urgency case in the dataset
- Critical medication non-adherence (CHF patient without diuretics)
- Patient found by wellness check — hospital admission suspected
- Multiple failed contacts, no caregiver, no signed care plan

### Scenario 5: CASE005 — Susan Martinez (Behavioral Health, Medium)
Best for demonstrating: Documentation Gaps.
- Active behavioral health case
- Assigned nurse field is blank — administrative gap
- Stable patient with good treatment engagement but coordination coverage missing

---

## Safety and Limitations

- **CaseAI Copilot is NOT a clinical decision support system.** It does not diagnose conditions, recommend treatments, or replace clinical judgment.
- All AI outputs are based strictly on the case data provided in each request. The AI cannot access external medical databases, patient records outside the system, or clinical guidelines.
- AI outputs should be reviewed by a qualified professional before any action is taken.
- The Q&A feature is grounded — it will explicitly decline to answer questions outside the scope of the case data.
- SQL injection protection is implemented in `utils/guards.py`. Only SELECT queries are permitted in SQL mode.
- No patient data is sent to Anthropic except what is explicitly included in AI prompts.

---

## Troubleshooting

**App won't start:**
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Verify Python version: `python --version` (requires 3.10+)

**AI features not working:**
- Confirm `ANTHROPIC_API_KEY` is set in your `.env` file
- Verify the key is valid at console.anthropic.com
- Check console output for authentication errors

**SQL mode falling back to demo:**
- Verify all `DB_*` environment variables are set
- Confirm ODBC Driver 17 is installed on your machine
- Test connection string manually with a SQL client first

**CSV data not loading:**
- Verify the `data/` folder exists and contains the sample CSV files
- Check for file permission issues on Windows

**Port already in use:**
```bash
streamlit run app.py --server.port 8502
```

---

## Future Enhancements

See [docs/future_enhancements.md](docs/future_enhancements.md) for the full roadmap including:
- Authentication & RBAC
- PDF export
- Azure deployment guide
- Audit logging to database
- Alert system for urgent cases
- Workflow action buttons (schedule follow-up, create task, etc.)
