# CaseAI Copilot — Prompt Strategy

## Philosophy

Every AI prompt in CaseAI Copilot is built around three principles:

1. **Grounding**: The AI must only use information explicitly provided in the case context. No external knowledge, no assumptions.
2. **Structured output**: Where structured data (JSON) is needed, the prompt clearly defines the schema and enforces it.
3. **Operational framing**: The AI is framed as a case management assistant, not a clinical decision maker.

---

## Prompt Templates

### 1. `SYSTEM_PROMPT_BASE`
**Purpose:** Sets the AI's identity, role, and behavioral guardrails for all requests.

**Key elements:**
- Explicitly defines the AI as an "operational assistant, not a clinical decision maker"
- Lists five core principles: evidence-based, no hallucination, factual accuracy, operational focus, transparency
- Lists explicit limitations: only knows what's in the provided data
- Instructs the AI to flag urgent safety concerns from documented data without diagnosing

**Why it works:** By establishing the operational vs. clinical boundary in the system prompt, every feature inherits these constraints without re-stating them.

---

### 2. `build_summary_prompt()`
**Purpose:** Generate a structured narrative case summary.

**Output format:** Free-form text organized into five named sections:
- Case Overview
- Recent Developments
- Active Issues
- Follow-up Needs
- Notable Context

**Hallucination prevention:**
- "Use ONLY information from the data above."
- "If a section has no relevant data, write 'No information documented.'"
- "Reference dates and specific documented events."

**Why separate from JSON prompts:** Summaries are narrative output meant for human reading. Forcing JSON would constrain the natural language quality. Free text is fine here because the consumer (UI) just renders it directly.

---

### 3. `build_timeline_prompt()`
**Purpose:** Extract chronological events from mixed data sources.

**Output format:** JSON array with schema:
```json
{"date": "YYYY-MM-DD", "event": "...", "source": "notes|structured|both", "confidence": "high|medium|low"}
```

**Hallucination prevention:**
- Explicit schema definition prevents Claude from inventing new fields
- `confidence` field allows Claude to express uncertainty (e.g., "low" for inferred dates)
- `source` field forces Claude to attribute each event to its data origin
- "Do not create events not supported by the data"

**Confidence levels encode epistemic honesty:** The AI distinguishes between explicit date stamps (high), approximate references (medium), and inferred events (low) — which surfaces in the UI as visual indicators.

---

### 4. `build_risk_prompt()`
**Purpose:** Identify operational and care coordination risks.

**Output format:** JSON array with schema:
```json
{"risk_name": "...", "severity": "Low|Medium|High", "evidence": "...", "source": "...", "explanation": "..."}
```

**Hallucination prevention:**
- Lists specific risk categories to check (engagement, medication, documentation, support, follow-up, access)
- Requires an "evidence" field that must be a quote or close paraphrase from case data
- "Only flag risks that are actually evidenced in the provided data"
- "Do not flag generic or speculative risks not grounded in this specific case"

**Why the evidence field matters:** It prevents the AI from adding generic boilerplate risks like "patient may have difficulty with compliance" without actual evidence. The evidence field forces traceability.

---

### 5. `build_gaps_prompt()`
**Purpose:** Identify missing documentation, overdue follow-ups, or incomplete workflows.

**Output format:** JSON array with schema:
```json
{"gap_type": "...", "description": "...", "severity": "Low|Medium|High", "recommendation": "..."}
```

**Hallucination prevention:**
- Defines specific gap categories to look for (post-discharge, care plan, referral, medication, outreach, inactivity, no nurse, notes without activities)
- "Only flag gaps that can be specifically identified from the data"
- "Do not flag speculative gaps"

**Recommendation field:** Forces the AI to suggest an actionable response, making the output operationally useful rather than just descriptive.

---

### 6. `build_validation_prompt()`
**Purpose:** Cross-reference notes against structured data to find discrepancies and confirmations.

**Output format:** JSON array with schema:
```json
{"observation": "...", "notes_suggest": "...", "data_shows": "...", "severity": "Info|Low|Medium|High"}
```

**Design decision:** "Info" is a valid severity level here to allow the AI to also report positive confirmations (notes and data agree). This makes the validation output balanced rather than only surfacing problems.

**Hallucination prevention:**
- "Only report on things you can directly compare between the two data sources"
- "Do not invent discrepancies"
- The two-column schema (`notes_suggest` and `data_shows`) forces the AI to cite both sides of every comparison

---

### 7. `build_qa_prompt()`
**Purpose:** Answer a specific user question grounded in the case data.

**Output format:** Free-form text answer (not JSON — natural language is more appropriate here).

**Hallucination prevention:**
- "You MUST base your answer ONLY on the case data provided below"
- "Do NOT use external knowledge, make assumptions, or invent information"
- Instructs citation: "state it clearly and cite the source (e.g., 'According to the note dated...')"
- Explicit fallback for unknown answers: "This information is not documented in the available case data."
- Explicitly declines clinical questions: "If the question asks for a clinical recommendation or medical advice, politely decline..."

---

## JSON Output Strategy

### The `SAFE_JSON_INSTRUCTION` constant
All JSON-requesting prompts append this shared instruction:

```
CRITICAL OUTPUT REQUIREMENTS:
- You MUST return ONLY valid JSON. No prose, no explanation, no preamble.
- Do NOT wrap the JSON in markdown code fences (no ```json or ```).
- Every string value must be properly escaped.
- If you have nothing to report for a category, return an empty JSON array: []
- Do not invent, fabricate, or assume information not present in the provided case data.
- If a field value is uncertain or not documented, use "Not documented" rather than guessing.
```

**Why this matters:** Claude sometimes wraps JSON in markdown code blocks or adds explanatory prose. The instruction explicitly forbids this. The `parse_ai_json()` utility in `utils/formatting.py` also handles code-fenced JSON defensively using regex stripping.

### Defensive JSON parsing
`parse_ai_json()` in `utils/formatting.py`:
1. Strips markdown code fences if present
2. Attempts `json.loads()` on the cleaned text
3. If that fails, uses regex to extract the first JSON array or object in the response
4. Returns empty list on complete failure with a logged warning

This three-level fallback ensures the app never crashes due to unexpected AI output formatting.

---

## How Prompts Prevent Hallucination

1. **Context injection:** All case data is included verbatim in every prompt. The AI cannot need to "remember" anything.
2. **Evidence requirements:** Risk and gap prompts require an `evidence` field that must cite the source data.
3. **Explicit uncertainty handling:** Timeline confidence levels and the "Not documented" fallback for JSON fields both give the AI a structured way to express uncertainty without inventing facts.
4. **Operational scope limitation:** The system prompt's operational framing limits the domain — the AI won't venture into clinical knowledge that isn't in the case data.
5. **Empty array instruction:** All JSON prompts explicitly say "if nothing to report, return []" — this prevents the AI from generating placeholder or illustrative data.

---

## How to Improve Prompts

### Improving summary quality
- Add a "tone" instruction: "Write in the voice of an experienced case manager, not a researcher."
- Add specific fields from your organization's care plan template.

### Improving risk detection precision
- Add examples of high-severity vs. low-severity risks relevant to your case types.
- Add organization-specific risk categories (e.g., re-admission within 30 days, LOC change).

### Improving timeline accuracy
- Add explicit instructions about how to handle events that appear in both notes and structured data (merge vs. separate entries).

### Adding few-shot examples
For any JSON-output prompt, adding 1-2 examples of expected output significantly improves consistency. Example:
```
Here is an example of a correctly formatted risk flag:
{"risk_name": "Missed Appointment", "severity": "Medium", ...}
```

### Testing prompts independently
Each prompt function can be called standalone and tested with a sample context before integrating:
```python
from config.prompts import build_risk_prompt
from models.dto import metadata_to_text, notes_to_text
print(build_risk_prompt(meta_text, notes_text, structured_text))
```
