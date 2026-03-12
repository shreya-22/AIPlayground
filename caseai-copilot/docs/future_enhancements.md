# CaseAI Copilot — Future Enhancements Roadmap

## Phase 1: Security & Access Control

### Authentication & RBAC
- Integrate Azure Active Directory (Azure Entra ID) or Okta for SSO authentication
- Role-based access control: Case Manager, Supervisor, Read-Only Auditor roles
- Case-level access restrictions: users can only view cases assigned to their team
- Session timeout and re-authentication after inactivity
- Audit log of who viewed which case and when

**Implementation path:**
- Use `streamlit-authenticator` or MSAL for Azure AD integration
- Add a `user_roles` table to the database
- Wrap all case data queries with role-based filtering at the service layer

---

## Phase 2: Export & Reporting

### PDF Export
- One-click "Export Case Report" button on the Case Overview tab
- PDF includes: case metadata, AI summary, risk flags, timeline, and validation observations
- Branded with organization logo and timestamp
- Digitally watermarked with "AI-Generated Draft — Requires Human Review"

**Implementation path:**
- Use `reportlab` or `weasyprint` for PDF generation
- Create a `ExportService` class in `services/`
- Add an "Export to PDF" button in `app.py`

### Excel/CSV Worklist Export
- Export the Priority Worklist to Excel with color-coded urgency labels
- Include configurable date range filters for the worklist

---

## Phase 3: Azure Deployment

### Azure App Service Deployment
- Containerize the app with Docker
- Deploy to Azure App Service (Linux) or Azure Container Instances
- Use Azure Key Vault for all secrets (API keys, DB passwords)
- Application Insights integration for monitoring and usage telemetry

**Dockerfile template:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Azure SQL Database
- Migrate from SQL Server on-premise to Azure SQL Database
- Use Managed Identity for passwordless authentication
- Enable Azure SQL Threat Detection for query anomaly alerts

### Azure Deployment Checklist
- [ ] Azure App Service or ACI provisioned
- [ ] Azure SQL Database with appropriate firewall rules
- [ ] Azure Key Vault with app identity configured
- [ ] Application Insights connected
- [ ] Azure Front Door or API Management for rate limiting
- [ ] Network Security Group rules reviewed

---

## Phase 4: Audit Logging Database

### Persistent AI Audit Trail
- Log every AI call to a database table (not just console logs)
- Schema: `ai_audit_log(log_id, user_id, case_id, feature, model, input_tokens, output_tokens, timestamp, session_id)`
- Schema: `user_activity_log(log_id, user_id, case_id, action, timestamp)`

### Supervisor Dashboard
- New Streamlit page for supervisors showing:
  - AI feature usage by user
  - Most reviewed cases
  - Cases with highest risk flags
  - Outstanding follow-up items across all cases
  - Trend charts: cases opened vs. closed per week

**Implementation path:**
- Add `AuditService` class in `services/`
- Replace current logger calls with DB-persistent audit writes
- Add a `supervisor_dashboard.py` Streamlit page

---

## Phase 5: Additional Data Sources

### FHIR Integration
- Connect to HL7 FHIR R4 APIs (Epic, Cerner, Azure Health Data Services)
- Map FHIR resources to existing schemas:
  - `Patient` → `CaseMetadata`
  - `ClinicalImpression` / `DocumentReference` → `CaseNote`
  - `Encounter` → `PatientVisit`
  - `MedicationRequest` / `MedicationDispense` → `MedicationEvent`
- Create `FHIRDataSource` class implementing the same interface as `MockDataSource`

### EHR Direct Integration
- Configurable SQL views for Epic Caboodle / Clarity
- Pre-built column mappings for common EHR schemas

### External Case Management Systems
- Connectors for: Salesforce Health Cloud, Netsmart myEvolv, HealthEC
- REST API adapter pattern for webhook-based real-time case updates

---

## Phase 6: Alert System

### Real-Time Urgency Alerts
- Background job that runs priority scoring across all active cases daily
- Alerts sent via email or Microsoft Teams when:
  - A case score exceeds threshold (e.g., score > 75)
  - A case has had no contact for > 14 days
  - A discharged case has no post-discharge follow-up after 72 hours
  - A medication adherence concern is documented without follow-up

### Alert Delivery Channels
- Email (via SendGrid or Azure Communication Services)
- Microsoft Teams webhook notifications
- In-app notification bell icon in sidebar

**Implementation path:**
- Add `AlertService` class in `services/`
- Use APScheduler or Azure Functions for scheduled scoring jobs
- Add notification preferences to user profile

---

## Phase 7: Workflow Actions

### Action Buttons in the UI
Currently CaseAI Copilot is read-only. Add actionable workflow integration:

- **Schedule Follow-Up**: Create a follow-up activity record directly from the Risk or Gaps view
- **Assign Nurse**: Update the assigned nurse field from the Case Overview tab
- **Create Task**: Push a task to the case management system from an identified gap
- **Document Outreach Attempt**: Log a phone outreach attempt without leaving the AI review tab
- **Escalate Case**: Flag a case for supervisor review with a one-click button
- **Close Gaps**: Mark documentation gaps as resolved after action is taken

**Implementation path:**
- Add write methods to `SQLDataSource` (with SQL guard validation)
- Create `WorkflowService` in `services/`
- Add confirmation dialogs to all write actions
- Separate read and write database roles in SQL permissions

---

## Phase 8: Advanced AI Features

### Longitudinal Trend Analysis
- Compare a case across multiple review periods to identify improvement or deterioration
- "How has this case changed since last week?" — AI-powered comparison

### Peer Case Comparison (Anonymized)
- Compare current case patterns against anonymized similar cases
- "Other cases with similar profiles typically have X outcome after Y intervention"

### Automated Care Plan Suggestions
- Based on identified gaps and risks, suggest standard care plan items
- NOT prescriptive — surfaces options for the case manager to review and choose

### Batch Processing Mode
- Process multiple cases at once (e.g., all cases due for weekly review)
- Generate a digest report summarizing the most urgent findings across the caseload

### Voice Interface
- Browser-based voice input for the Q&A feature
- Useful for case managers on the phone or in a clinical setting without hands-free keyboard access

---

## Phase 9: Compliance & Privacy

### HIPAA Compliance Hardening
- Data masking in logs: ensure PHI is never written to log files
- Minimum Necessary standard: only load data fields required for the current operation
- Business Associate Agreement (BAA) with Anthropic confirmed before production use
- Data residency controls for AI API calls (US-only routing option)

### Data Retention Policies
- Configurable session data expiration
- AI output not stored persistently unless explicitly saved
- Audit log retention policy aligned with HIPAA 6-year requirement

---

## Technical Debt & Quality Improvements

- Unit test suite with pytest covering all services
- Integration tests with mocked Anthropic responses
- Pre-commit hooks for linting (ruff) and type checking (mypy)
- GitHub Actions CI/CD pipeline
- Performance optimization: cache case data in session state with TTL
- Async AI calls for batch operations using `asyncio` and `anthropic`'s async client
