# CaseAI Copilot — System Architecture

## Overview

CaseAI Copilot is a multi-layer Python application built with Streamlit as the UI framework and Anthropic Claude as the AI backend. The architecture is designed to be modular, testable, and extensible — each layer has a single responsibility.

---

## System Components

```
+------------------------------------------------------------+
|                    Streamlit UI (app.py)                   |
|  - Session state management                                |
|  - Tab-based feature layout                                |
|  - CSS styling and formatting                              |
+------------------------------------------------------------+
         |                |               |
         v                v               v
+---------------+  +-------------+  +------------------+
| CaseService   |  | AIService   |  | PriorityService  |
| (Orchestrate) |  | (Claude API)|  | (Heuristic)      |
+---------------+  +-------------+  +------------------+
         |                |
         v                v
+---------------+  +--------------------------------------+
| Data Sources  |  | Feature Services                     |
| MockDS (CSV)  |  | RiskService, TimelineService,        |
| SQLDataSource |  | ValidationService, QAService         |
+---------------+  +--------------------------------------+
         |                |
         v                v
+---------------+  +--------------------------------------+
| models/       |  | config/                              |
| schemas.py    |  | settings.py, prompts.py              |
| dto.py        |  +--------------------------------------+
+---------------+
         |
         v
+--------------------------------------+
| utils/                               |
| formatting.py, guards.py,            |
| helpers.py, logger.py               |
+--------------------------------------+
```

---

## Data Flow

### Case Load Flow
```
User selects case in UI
    → app.py calls CaseService.get_case_context(case_id)
    → CaseService calls DataSource.get_case_metadata()
    → CaseService calls DataSource.get_case_notes()
    → CaseService calls DataSource.get_case_visits()
    → CaseService calls DataSource.get_case_activities()
    → CaseService calls DataSource.get_medication_events()
    → CaseService assembles CaseContext object
    → CaseContext stored in st.session_state.case_context
    → UI renders case header card and tabs
```

### AI Feature Flow (e.g., Risk Detection)
```
User clicks "Detect Risks" button
    → app.py calls RiskService.detect_risks(context)
    → RiskService calls dto formatters to convert CaseContext to text
    → RiskService calls build_risk_prompt() from config/prompts.py
    → RiskService calls AIService.call_claude_for_json(system, user)
    → AIService calls anthropic.Anthropic.messages.create()
    → AIService returns response text
    → AIService calls parse_ai_json() to extract JSON array
    → RiskService calls _parse_risk_flags() to convert to List[RiskFlag]
    → List[RiskFlag] stored in st.session_state.risks
    → UI renders risk flags with severity badges and expandable details
```

### Priority Scoring Flow (No AI)
```
User clicks "Score Priority" button
    → app.py calls PriorityService.score_case(context)
    → PriorityService evaluates heuristic rules against CaseContext
    → PriorityService accumulates points and factors list
    → PriorityService returns PriorityScore object
    → PriorityScore stored in st.session_state.priority_score
    → UI renders score card with contributing factors
```

---

## AI vs. Heuristic Responsibilities

| Feature | Method | Why |
|---------|--------|-----|
| Case Summary | AI (Claude) | Requires narrative synthesis across unstructured notes |
| Timeline Extraction | AI (Claude) | Requires understanding and ordering unstructured text |
| Risk Detection | AI (Claude) | Requires interpretation of note language and clinical context |
| Data Validation | AI (Claude) | Requires comparing two different data representations |
| Q&A | AI (Claude) | Requires grounded natural language understanding |
| Priority Scoring | Heuristic | Deterministic rules are more predictable, auditable, and don't require API calls |

---

## Safety Boundaries

### AI Safety
- All prompts include explicit instructions: "Do not fabricate. If information is not in the data, say so."
- The system prompt establishes the AI as an operational assistant, not a clinical decision maker.
- JSON prompts include `SAFE_JSON_INSTRUCTION` to prevent hallucinated JSON fields.
- Q&A prompt explicitly declines to answer clinical recommendation questions.

### SQL Safety (SQLGuard)
- Only SELECT queries are permitted through the app interface.
- Dangerous keywords (DROP, DELETE, INSERT, etc.) are checked via regex.
- Statement chaining (semicolons) is blocked.
- Comment injection (-- and /* */) is blocked.
- Parameterized queries (`?` placeholders) are used throughout SQLDataSource.

### Input Validation
- User questions validated for length (5-500 chars) before AI calls.
- All data from CSV/SQL is type-cast to str with NaN/null handling.
- All exceptions are caught and logged; UI shows graceful error messages.

---

## Data Layer Design

### MockDataSource
- Loads 5 CSV files from `data/` directory on initialization.
- Filters DataFrames by `case_id` for all get_* methods.
- Returns empty lists (not exceptions) for missing data.
- Used in demo mode and as fallback when SQL fails.

### SQLDataSource
- Lazy connection: connects only when first query is executed.
- Uses pyodbc with parameterized queries exclusively.
- Implements the same interface as MockDataSource.
- `get_data_source(config)` factory function selects the correct source.

---

## Component Interaction Map

```
app.py
  |-- reads config from: config/settings.py
  |-- initializes:        services/sql_service.py (get_data_source)
  |-- uses:               services/case_service.py
  |-- delegates AI to:    services/[risk|timeline|validation|qa]_service.py
  |-- delegates scoring:  services/priority_service.py
  |-- renders with:       utils/formatting.py
  |-- validates with:     utils/guards.py
  |-- logs with:          utils/logger.py

services/case_service.py
  |-- uses:               services/sql_service.py (MockDataSource | SQLDataSource)
  |-- converts with:      models/dto.py

services/[feature]_service.py
  |-- uses:               services/ai_service.py
  |-- reads prompts from: config/prompts.py
  |-- formats data with:  models/dto.py
  |-- parses JSON with:   utils/formatting.py (parse_ai_json)
  |-- safe_gets with:     utils/helpers.py (safe_get)
  |-- logs with:          utils/logger.py

services/ai_service.py
  |-- calls:              anthropic.Anthropic.messages.create()
  |-- logs with:          utils/logger.py (log_ai_call)
  |-- parses with:        utils/formatting.py (parse_ai_json)
```

---

## How to Extend Each Layer

### Adding a New AI Feature
1. Add a new prompt builder function in `config/prompts.py`
2. Create a new service file in `services/` (e.g., `medication_service.py`)
3. Follow the same pattern: format context → build prompt → call AI → parse → return typed objects
4. Add new schema types in `models/schemas.py` if needed
5. Add a new tab in `app.py` and call the service

### Adding a New Data Source
1. Create a class implementing the same interface as `MockDataSource`
2. Implement all `get_*` methods
3. Update `get_data_source()` in `sql_service.py` to detect and return your new source

### Adding a New Risk Factor
1. Update the heuristic rules in `services/priority_service.py` — `score_case()` method
2. Update the AI risk prompt in `config/prompts.py` — `build_risk_prompt()` to guide Claude

### Changing the AI Model
1. Update `MODEL_NAME` in `config/settings.py`
2. All AI calls route through `AIService`, so one config change updates everything
