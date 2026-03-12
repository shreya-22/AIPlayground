"""
CaseAI Copilot - Database Setup Script
Creates the CaseAICopilot database, all tables, and seeds sample data.
Run once: python setup_database.py
"""

import pyodbc
import sys

SERVER = "LAPTOP-Q6V2KMQ9"
DB_NAME = "CaseAICopilot"
CONN_MASTER = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE=master;Trusted_Connection=yes;"
CONN_DB     = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DB_NAME};Trusted_Connection=yes;"


def create_database():
    conn = pyodbc.connect(CONN_MASTER, autocommit=True)
    cursor = conn.cursor()
    cursor.execute(f"""
        IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = '{DB_NAME}')
            CREATE DATABASE [{DB_NAME}]
    """)
    conn.close()
    print(f"[OK] Database [{DB_NAME}] ready.")


def create_tables():
    conn = pyodbc.connect(CONN_DB, autocommit=True)
    c = conn.cursor()

    c.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='cases' AND xtype='U')
        CREATE TABLE cases (
            case_id           NVARCHAR(20)  PRIMARY KEY,
            member_name       NVARCHAR(100) NOT NULL,
            status            NVARCHAR(50),
            open_date         DATE,
            discharge_date    DATE NULL,
            assigned_nurse    NVARCHAR(100) NULL,
            last_contact_date DATE NULL,
            case_type         NVARCHAR(100),
            priority_label    NVARCHAR(50)
        )
    """)
    print("[OK] Table [cases] ready.")

    c.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='case_notes' AND xtype='U')
        CREATE TABLE case_notes (
            note_id     NVARCHAR(20)  PRIMARY KEY,
            case_id     NVARCHAR(20)  NOT NULL REFERENCES cases(case_id),
            note_date   DATE,
            note_author NVARCHAR(100),
            note_text   NVARCHAR(MAX)
        )
    """)
    print("[OK] Table [case_notes] ready.")

    c.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='patient_visits' AND xtype='U')
        CREATE TABLE patient_visits (
            visit_id      NVARCHAR(20)  PRIMARY KEY,
            case_id       NVARCHAR(20)  NOT NULL REFERENCES cases(case_id),
            visit_date    DATE,
            visit_type    NVARCHAR(100),
            provider_name NVARCHAR(100),
            outcome       NVARCHAR(MAX)
        )
    """)
    print("[OK] Table [patient_visits] ready.")

    c.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='case_activity' AND xtype='U')
        CREATE TABLE case_activity (
            activity_id     NVARCHAR(20)  PRIMARY KEY,
            case_id         NVARCHAR(20)  NOT NULL REFERENCES cases(case_id),
            activity_date   DATE,
            activity_type   NVARCHAR(100),
            activity_status NVARCHAR(50),
            details         NVARCHAR(MAX)
        )
    """)
    print("[OK] Table [case_activity] ready.")

    c.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='medication_events' AND xtype='U')
        CREATE TABLE medication_events (
            med_event_id    NVARCHAR(20)  PRIMARY KEY,
            case_id         NVARCHAR(20)  NOT NULL REFERENCES cases(case_id),
            event_date      DATE,
            medication_name NVARCHAR(150),
            event_type      NVARCHAR(100),
            details         NVARCHAR(MAX)
        )
    """)
    print("[OK] Table [medication_events] ready.")

    conn.close()


def seed_data():
    conn = pyodbc.connect(CONN_DB, autocommit=True)
    c = conn.cursor()

    # Clear existing data
    for tbl in ["medication_events", "case_activity", "patient_visits", "case_notes", "cases"]:
        c.execute(f"DELETE FROM {tbl}")
    print("[OK] Cleared existing data.")

    # ── CASES ──────────────────────────────────────────────────────────────────
    cases = [
        ("CASE001", "Margaret Wilson",  "Active",     "2024-01-15", None,         "Sarah Johnson",  "2024-03-08", "Post-Surgical",       "Medium"),
        ("CASE002", "Robert Chen",      "Active",     "2024-02-03", None,         "Maria Garcia",   "2024-02-28", "Chronic Disease Mgmt","High"),
        ("CASE003", "Dorothy Patterson","Discharged",  "2024-01-20", "2024-03-01","James Mitchell", "2024-03-01", "Cardiac Rehab",       "Low"),
        ("CASE004", "James Thompson",   "Active",     "2024-02-20", None,         "Lisa Park",      "2024-02-15", "Complex Care",        "Critical"),
        ("CASE005", "Susan Martinez",   "Active",     "2024-03-01", None,         None,             "2024-03-05", "Behavioral Health",   "Medium"),
    ]
    c.executemany("INSERT INTO cases VALUES (?,?,?,?,?,?,?,?,?)", cases)
    print(f"[OK] Inserted {len(cases)} cases.")

    # ── NOTES ──────────────────────────────────────────────────────────────────
    notes = [
        ("N001","CASE001","2024-01-16","Sarah Johnson",
         "Initial post-surgical assessment completed. Patient Margaret Wilson is a 68-year-old female recovering from right total knee replacement performed 2024-01-14. Wound site appears clean with no signs of infection. Patient reports pain level 6/10, currently managing with prescribed oral analgesics. Physical therapy initiated in-hospital prior to discharge."),
        ("N002","CASE001","2024-01-28","Sarah Johnson",
         "Follow-up phone call completed. Patient reports PT sessions twice weekly are going well. She is ambulating with a walker and progressing per therapist expectations. Pain is now 4/10. Wound has healed with no drainage. Caregiver (daughter Linda) present and assisting with daily activities and medication management. No concerns at this time."),
        ("N003","CASE001","2024-02-15","Sarah Johnson",
         "Home visit completed. Patient demonstrates improved range of motion. Physical therapist notes patient is ahead of typical recovery curve. Patient asked about her metoprolol prescription - states she missed three doses last week because she thought the prescription had run out. Confirmed with pharmacy that refill was available. Educated patient on importance of consistent cardiac medication adherence. Refill confirmed by pharmacy same day."),
        ("N004","CASE001","2024-02-29","Sarah Johnson",
         "Monthly care plan review completed. Margaret continues to make strong post-surgical progress. PT transitioning to once weekly. Pain is now 2/10, well-controlled. Patient expressed concern about returning to driving - discussed with MD, cleared for driving after next follow-up visit. Daughter reports patient is increasingly independent with ADLs. Care plan updated to reflect current status and revised goals."),
        ("N005","CASE001","2024-03-08","Sarah Johnson",
         "Phone check-in completed. Patient reports feeling much better overall. PT formally completed as of 2024-03-05 with full discharge from PT program. Patient is walking without assistive device indoors. No new concerns. Scheduled 60-day case review for 2024-04-08. Patient states she feels confident managing independently with daughter nearby for support."),
        ("N006","CASE002","2024-02-04","Maria Garcia",
         "Initial case enrollment for Robert Chen, 54-year-old male with Type 2 Diabetes (HbA1c 9.8 at last draw), hypertension, and Stage 2 chronic kidney disease. Referred by PCP due to poor glycemic control and multiple missed clinic appointments over the past 6 months. Patient verbally engaged but expressed frustration with his medication regimen. Wife noted to be primary caregiver but reported feeling overwhelmed and burned out. Case opened for chronic disease management."),
        ("N007","CASE002","2024-02-14","Maria Garcia",
         "Attempted phone outreach - no answer. Left voicemail requesting callback. Patient had a scheduled diabetes education class today which he did not attend per educator report. Sent follow-up letter to home address. Care team notified of no-show. This is the second missed appointment in two weeks."),
        ("N008","CASE002","2024-02-20","Maria Garcia",
         "Robert returned call. States he missed appointment due to transportation issues - his car is in the shop. Discussed transportation assistance program. Reviewed medication list: patient is NOT taking Jardiance as prescribed, states the cost is too much. Initiated prior authorization review for copay assistance. Wife joined the call and reiterated feeling overwhelmed, mentions she is also caring for her own elderly mother. Documented caregiver stress. Flagged for social work referral."),
        ("N009","CASE002","2024-02-28","Maria Garcia",
         "Social work referral submitted 2024-02-21 - no response from SW department as of today. Following up internally. Jardiance prior auth approved; pharmacy notified. However patient called to say he still has not picked up the medication. Rescheduled diabetes education for 2024-03-10. Patients wife called separately expressing concerns about worsening fatigue and confusion episodes not yet documented by treating provider. Flagged as needing urgent PCP notification."),
        ("N010","CASE002","2024-03-05","Maria Garcia",
         "Outreach attempt by phone - no answer. Attempted SMS - no response. Diabetes education appointment on 2024-03-10 remains unconfirmed. Social work still has not contacted patient or family. Medication adherence status unknown. This case is escalating - patient engagement is deteriorating and caregiver is at a breaking point. Recommending supervisor review and escalation to high-complexity care management tier."),
        ("N011","CASE003","2024-01-21","James Mitchell",
         "Initial cardiac rehab case enrollment. Dorothy Patterson is a 72-year-old female referred following hospitalization for NSTEMI on 2024-01-10. Discharged from hospital 2024-01-14 with follow-up cardiology appointment scheduled. Patient is alert, oriented, and highly motivated to participate in cardiac rehab. Lives with supportive husband. Denies any current chest pain or shortness of breath. Started on post-MI medication regimen including statin, beta-blocker, and aspirin."),
        ("N012","CASE003","2024-02-01","James Mitchell",
         "First cardiac rehab session attended. Dorothy is progressing well. Heart rate and blood pressure within target parameters during exercise. Patient reports full compliance with all prescribed medications. Husband accompanied her and is actively engaged in her recovery. Patient is following low-sodium cardiac diet as instructed. No concerns at this time. Session 1 of 36 completed."),
        ("N013","CASE003","2024-02-15","James Mitchell",
         "Mid-program check-in. Dorothy has completed 8 of 36 cardiac rehab sessions with perfect attendance. Exercise tolerance improving - achieved 4 METs today compared to 2.5 METs at baseline. Blood pressure well-controlled at 118/72. Patient denies chest pain, dyspnea, or palpitations. Medication compliance confirmed. Patient expressed high satisfaction with program. On track for completion by end of February."),
        ("N014","CASE003","2024-02-26","James Mitchell",
         "Final cardiac rehab sessions completed. Dorothy successfully completed all 36 sessions of Phase II cardiac rehab. Achieved excellent functional improvement - final stress test showed 7 METs tolerance. Discharged from cardiac rehab program with maintenance exercise plan. Patient and husband educated on warning signs requiring emergency care. Patient verbally confirmed cardiology follow-up scheduled for 2024-03-15."),
        ("N015","CASE003","2024-03-01","James Mitchell",
         "Case closed - formal discharge. Dorothy Patterson has successfully completed cardiac rehab. All program goals met. Formal case discharge completed today. Post-discharge care plan provided to patient and documented in record. No further case management follow-up scheduled in system - patient transitioned to routine outpatient cardiology follow-up with Dr. Patel. Discharge summary sent to PCP and cardiologist."),
        ("N016","CASE004","2024-02-21","Lisa Park",
         "Initial enrollment for James Thompson, 61-year-old male with complex medical history including CHF (EF 30%), COPD (GOLD Stage III), Type 2 Diabetes, and recent hospitalization for acute CHF exacerbation (discharged 2024-02-18). Referred for complex care management due to three hospitalizations in 90 days. Lives alone in a second-floor apartment. No identified caregiver or emergency contact on file. Case opened as Critical priority. Initial assessment attempted - patient was home but appeared confused and did not fully engage."),
        ("N017","CASE004","2024-02-26","Lisa Park",
         "Follow-up home visit attempted - no answer at door despite patient being home per neighbor report. Left door hanger with contact information. Attempted phone call same day - no answer. Patient is non-compliant with medication monitoring (home weight log blank since hospital discharge). Per pharmacy records reviewed, patient has not picked up furosemide or Entresto since discharge 8 days ago. This is a critical medication gap for a CHF patient. Left urgent message with PCP office."),
        ("N018","CASE004","2024-03-02","Lisa Park",
         "Spoke briefly with patient by phone - James is confused about his medications and states he ran out of the water pill several days ago. He reports ankle swelling worsening over past 3 days and increased shortness of breath. He declined offer of ED evaluation and was unable to provide a caregiver contact. Notified PCP urgently - PCP instructed patient to present to office same day. Patient stated he had no way to get there. Arranged medical transport - patient confirmed transport but did not show to PCP appointment per office report."),
        ("N019","CASE004","2024-03-05","Lisa Park",
         "Unable to reach patient by phone x3 over past 3 days. No caregiver to contact. Reached neighbor Mrs. Alvarez who last saw James on 2024-03-03 and reported he appeared very short of breath and swollen. Safety concern documented. Supervisor notified. Wellness check requested through local authorities. Outcome of wellness check not yet confirmed. This case requires immediate escalation - patient is medically vulnerable, living alone, non-adherent to critical medications, and unreachable."),
        ("N020","CASE004","2024-03-07","Lisa Park",
         "Update: Wellness check confirmed patient was found at home in distress on 2024-03-05. Patient transported to ED by EMS. Admitted to hospital per neighbor report - official hospital records not yet received. Case flagged for hospital liaison follow-up. Documentation gap: no updated emergency contact, no care plan revision since admission, no confirmation of current hospital or admission diagnosis. Case remains open and Critical."),
        ("N021","CASE005","2024-03-02","Dr. Anita Sharma",
         "Initial case enrollment. Susan Martinez is a 34-year-old female referred for behavioral health case management following voluntary psychiatric hospitalization for major depressive episode (2024-02-20 to 2024-02-27). Discharged home with prescription for sertraline 100mg daily and weekly outpatient therapy with Dr. Kwan. Patient lives alone, employed part-time, has limited social support network. Initial phone assessment completed. Patient cooperative but guarded. Denies current suicidal ideation. PHQ-9 score at enrollment: 14 (moderate depression)."),
        ("N022","CASE005","2024-03-05","Dr. Anita Sharma",
         "Phone check-in completed. Susan reports she has attended one therapy session with Dr. Kwan and found it helpful. She is taking sertraline as prescribed. She reports initial side effects (mild nausea, insomnia) which are expected and discussed. Identified that patient has limited connection to peer support - referred to local depression support group (meeting Thursdays). Patient expressed interest. No crisis indicators. PHQ-9 7 days post enrollment: 12."),
        ("N023","CASE005","2024-03-08","Dr. Anita Sharma",
         "Noted during case setup review: assigned_nurse field is blank in case management system for CASE005. This is an administrative gap - behavioral health cases require a designated case manager or nurse coordinator for ongoing oversight and escalation coverage. Dr. Sharma is the treating provider but does not fulfill the care coordinator role. A case coordinator must be assigned. Flagged for supervisor action."),
        ("N024","CASE005","2024-03-10","Dr. Anita Sharma",
         "Weekly check-in call. Susan reports therapy is continuing - attended session 2 this week. States mood is a little better. Sertraline side effects have improved. She has not yet attended the support group but plans to go this Thursday. Patient mentioned isolating more on weekends and skipping meals when stressed. Discussed structured daily routine and simple meal planning. No safety concerns. PHQ-9 today: 10 (mild depression, improving). Case coordinator assignment still pending per supervisor note."),
    ]
    c.executemany("INSERT INTO case_notes VALUES (?,?,?,?,?)", notes)
    print(f"[OK] Inserted {len(notes)} notes.")

    # ── VISITS ─────────────────────────────────────────────────────────────────
    visits = [
        ("V001","CASE001","2024-01-14","Surgical Procedure",        "Dr. Raymond Hughes",          "Right total knee replacement completed without complications. Patient transferred to recovery and initiated on post-surgical care protocol."),
        ("V002","CASE001","2024-01-16","Post-Surgical Assessment",  "Sarah Johnson (RN)",           "Initial post-discharge assessment. Wound intact. Pain 6/10. PT ordered and initiated."),
        ("V003","CASE001","2024-02-15","Home Visit",                "Sarah Johnson (RN)",           "Patient progressing well. Medication concern identified - missed metoprolol doses. Education provided. Refill confirmed."),
        ("V004","CASE001","2024-03-05","Physical Therapy Discharge","PT Dept - Michael Torres",     "Patient formally discharged from PT program after achieving all goals. Ambulating without assistive device indoors."),
        ("V005","CASE002","2024-02-05","Enrollment Assessment",     "Maria Garcia (RN)",            "Initial chronic disease management assessment completed. HbA1c 9.8. Multiple medication adherence issues identified."),
        ("V006","CASE002","2024-02-14","Diabetes Education Class",  "Certified Diabetes Educator",  "NO SHOW - Patient did not attend scheduled diabetes education class. Second missed appointment in two weeks."),
        ("V007","CASE002","2024-02-21","Social Work Consultation",  "Social Work Department",       "Referral submitted by case manager. No appointment confirmed as of referral date."),
        ("V008","CASE002","2024-03-10","Diabetes Education Rescheduled","Certified Diabetes Educator","NO SHOW - Patient did not attend rescheduled diabetes education session. Status: Unconfirmed/Absent."),
        ("V009","CASE003","2024-01-21","Initial Cardiac Rehab Assessment","James Mitchell (RN)",    "Baseline assessment completed. Exercise tolerance 2.5 METs. Hemodynamically stable. Program initiated."),
        ("V010","CASE003","2024-02-01","Cardiac Rehab Session 1",   "Cardiac Rehab Team",           "Session 1 of 36 completed. HR and BP within parameters. Good patient engagement."),
        ("V011","CASE003","2024-02-15","Cardiac Rehab Mid-Program Check","James Mitchell (RN)",     "8 sessions completed. Exercise tolerance 4 METs. Perfect attendance. Blood pressure 118/72."),
        ("V012","CASE003","2024-02-26","Cardiac Rehab Program Completion","Cardiac Rehab Team",     "All 36 sessions completed. Final stress test 7 METs. Formally discharged from Phase II cardiac rehab."),
        ("V013","CASE004","2024-02-19","Post-Discharge Assessment", "Lisa Park (RN)",               "Initial assessment following CHF hospitalization discharge 2024-02-18. Patient confused and minimally engaged. Lives alone. No caregiver identified."),
        ("V014","CASE004","2024-02-26","Home Visit Attempt",        "Lisa Park (RN)",               "NO CONTACT - Patient did not answer door despite neighbor reporting patient was home. Door hanger left with contact information."),
        ("V015","CASE004","2024-03-02","PCP Urgent Appointment",    "Dr. Prakash Menon",            "NO SHOW - Patient arranged medical transport but did not present to urgent PCP appointment. Status: Absent."),
        ("V016","CASE005","2024-02-27","Psychiatric Discharge Assessment","Dr. Anita Sharma",       "Patient discharged from inpatient psychiatric unit. PHQ-9 at discharge: 16. Prescribed sertraline 100mg. Outpatient therapy arranged with Dr. Kwan."),
        ("V017","CASE005","2024-03-02","Initial Case Management Assessment","Dr. Anita Sharma",     "Enrollment assessment completed. PHQ-9: 14. Patient cooperative. Therapy referral confirmed. Safety plan reviewed."),
        ("V018","CASE005","2024-03-08","Outpatient Therapy Session 1","Dr. Jennifer Kwan (LCSW)",   "First outpatient therapy session completed. Patient engaged. Initial treatment goals established."),
        ("V019","CASE005","2024-03-14","Outpatient Therapy Session 2","Dr. Jennifer Kwan (LCSW)",   "Second session completed. Patient reports gradual mood improvement. Behavioral activation strategies introduced."),
    ]
    c.executemany("INSERT INTO patient_visits VALUES (?,?,?,?,?,?)", visits)
    print(f"[OK] Inserted {len(visits)} visits.")

    # ── ACTIVITY ───────────────────────────────────────────────────────────────
    activity = [
        ("A001","CASE001","2024-01-16","assessment",        "completed","Initial post-surgical care assessment completed. Goals set for 6-week recovery program."),
        ("A002","CASE001","2024-01-28","phone_outreach",    "completed","Follow-up call with patient and caregiver. Patient progressing. No urgent concerns."),
        ("A003","CASE001","2024-02-15","home_visit",        "completed","Home visit performed. Medication adherence issue identified and resolved. Care plan reviewed."),
        ("A004","CASE001","2024-02-15","medication_review", "completed","Metoprolol adherence gap identified. Pharmacist notified. Patient educated on importance of consistent dosing."),
        ("A005","CASE001","2024-02-29","care_plan_update",  "completed","Care plan updated at 6-week milestone. Goals revised to reflect strong recovery progress. PT reduction approved."),
        ("A006","CASE001","2024-03-08","phone_outreach",    "completed","Check-in call completed. PT program formally discharged. Patient doing well. 60-day review scheduled."),
        ("A007","CASE001","2024-04-08","follow_up_scheduled","pending", "60-day case review scheduled. Will reassess for case closure or continued monitoring."),
        ("A008","CASE002","2024-02-04","assessment",        "completed","Initial chronic disease management assessment. Complex case with multiple comorbidities and medication adherence issues identified."),
        ("A009","CASE002","2024-02-14","phone_outreach",    "failed",   "Attempted phone contact - no answer. Voicemail left. Patient missed diabetes education class same day."),
        ("A010","CASE002","2024-02-20","phone_outreach",    "completed","Patient returned call. Transportation and medication cost barriers identified. Referrals initiated."),
        ("A011","CASE002","2024-02-21","referral",          "pending",  "Social work referral submitted for caregiver support and psychosocial assessment. No response from SW as of 2024-02-28."),
        ("A012","CASE002","2024-02-21","medication_review", "completed","Jardiance prior authorization submitted. Copay assistance program initiated. Pharmacy notified upon approval."),
        ("A013","CASE002","2024-02-28","follow_up_scheduled","pending", "Diabetes education rescheduled for 2024-03-10. Transport arranged. Confirmation pending from patient."),
        ("A014","CASE002","2024-03-05","phone_outreach",    "failed",   "Attempted phone outreach - no answer. SMS sent - no response. Engagement significantly declining."),
        ("A015","CASE002","2024-03-05","follow_up_scheduled","overdue", "Supervisor review requested due to case complexity escalation. Awaiting supervisor response."),
        ("A016","CASE002","2024-03-10","follow_up_scheduled","failed",  "Diabetes education rescheduled appointment - patient no-show again. Third missed diabetes education appointment."),
        ("A017","CASE003","2024-01-21","assessment",        "completed","Initial cardiac rehab enrollment assessment. Program initiated. All baseline metrics documented."),
        ("A018","CASE003","2024-02-01","care_plan_update",  "completed","Cardiac rehab care plan established. 36-session Phase II program initiated with attendance tracking."),
        ("A019","CASE003","2024-02-26","assessment",        "completed","Program completion assessment. All goals met. Patient educated on maintenance plan and warning signs."),
        ("A020","CASE003","2024-03-01","care_plan_update",  "completed","Case closure documentation completed. Discharge summary sent to PCP and cardiologist Dr. Patel."),
        ("A021","CASE004","2024-02-21","assessment",        "completed","Initial complex care assessment attempted. Patient confused and minimally engaged. No caregiver identified. Critical priority assigned."),
        ("A022","CASE004","2024-02-21","care_plan_update",  "pending",  "Initial care plan development not completed due to patient engagement issues. Status: Draft - not signed."),
        ("A023","CASE004","2024-02-26","phone_outreach",    "failed",   "Attempted phone contact - no answer. Home visit attempt same day - no answer at door."),
        ("A024","CASE004","2024-02-27","phone_outreach",    "failed",   "Second phone attempt - no answer. Left urgent voicemail. No callback received."),
        ("A025","CASE004","2024-03-02","phone_outreach",    "completed","Brief phone contact made. Patient reported medication non-adherence and worsening symptoms. PCP notified urgently."),
        ("A026","CASE004","2024-03-02","follow_up_scheduled","failed",  "PCP urgent appointment arranged with medical transport. Patient did not show. Status: No-show."),
        ("A027","CASE004","2024-03-03","phone_outreach",    "failed",   "Attempted callback after PCP no-show - no answer."),
        ("A028","CASE004","2024-03-04","phone_outreach",    "failed",   "Attempted phone contact - no answer. No callback."),
        ("A029","CASE004","2024-03-05","phone_outreach",    "failed",   "Final attempt before safety escalation - no answer. Neighbor contact made. Wellness check requested."),
        ("A030","CASE004","2024-03-07","follow_up_scheduled","overdue", "Hospital liaison follow-up required. Patient reportedly admitted to ED/hospital. Official records not yet received. Care plan revision overdue."),
        ("A031","CASE005","2024-03-02","assessment",        "completed","Initial behavioral health enrollment assessment. PHQ-9 14. Safety plan completed. Therapy referral confirmed."),
        ("A032","CASE005","2024-03-05","phone_outreach",    "completed","First post-enrollment check-in. Patient reports good therapy engagement. Medication side effects discussed. Support group referral made."),
        ("A033","CASE005","2024-03-08","care_plan_update",  "pending",  "Care plan requires assigned nurse/coordinator. Field is blank. Flagged for supervisor to assign case coordinator."),
        ("A034","CASE005","2024-03-10","phone_outreach",    "completed","Weekly check-in. Patient improving. PHQ-9 10. Meal planning and daily routine discussed. Coordinator assignment still pending."),
        ("A035","CASE005","2024-03-17","follow_up_scheduled","pending", "Weekly check-in scheduled. Coordinator assignment must be resolved before this date."),
    ]
    c.executemany("INSERT INTO case_activity VALUES (?,?,?,?,?,?)", activity)
    print(f"[OK] Inserted {len(activity)} activity records.")

    # ── MEDICATION EVENTS ──────────────────────────────────────────────────────
    meds = [
        ("M001","CASE001","2024-01-14","Oxycodone 5mg",           "prescribed",      "Post-surgical pain management. Short-term prescription for 7 days. Patient and caregiver educated on appropriate use."),
        ("M002","CASE001","2024-01-14","Metoprolol Succinate 50mg","prescribed",      "Continuation of pre-surgical cardiac medication. Once daily dosing. Confirmed on medication reconciliation at surgical discharge."),
        ("M003","CASE001","2024-01-14","Aspirin 81mg",             "prescribed",      "Continuation of daily aspirin for cardiac history. Confirmed at discharge."),
        ("M004","CASE001","2024-01-21","Oxycodone 5mg",           "refill_completed", "7-day prescription completed. No refill issued. Patient transitioned to OTC acetaminophen per surgeon guidance."),
        ("M005","CASE001","2024-02-15","Metoprolol Succinate 50mg","adherence_concern","Patient reported missing 3 doses due to belief prescription had run out. Pharmacy confirmed refill was available. Education provided."),
        ("M006","CASE001","2024-02-15","Metoprolol Succinate 50mg","refill_completed", "Pharmacy refill confirmed available and dispensed. Patient reminded to monitor supply and request refill 7 days before running out."),
        ("M007","CASE002","2024-02-04","Metformin 1000mg BID",    "prescribed",       "Ongoing diabetes management medication. Patient states he takes this inconsistently - sometimes forgets afternoon dose."),
        ("M008","CASE002","2024-02-04","Jardiance 10mg",          "prescribed",       "Prescribed for diabetes and CKD protection. Patient expressed concern about cost at enrollment assessment."),
        ("M009","CASE002","2024-02-04","Lisinopril 20mg",         "prescribed",       "Antihypertensive for blood pressure management. Patient unclear on dosing schedule."),
        ("M010","CASE002","2024-02-04","Atorvastatin 40mg",       "prescribed",       "Statin for cardiovascular risk reduction. Patient states he runs out frequently."),
        ("M011","CASE002","2024-02-20","Jardiance 10mg",          "adherence_concern", "Patient confirmed he is NOT taking Jardiance as prescribed due to cost concerns. Prior authorization for copay assistance initiated."),
        ("M012","CASE002","2024-02-25","Jardiance 10mg",          "refill_completed",  "Prior authorization approved. Pharmacy notified of copay assistance program enrollment. Medication ready for pickup."),
        ("M013","CASE002","2024-02-28","Jardiance 10mg",          "adherence_concern", "Despite copay assistance being in place and prescription ready, patient has not picked up medication from pharmacy."),
        ("M014","CASE002","2024-02-28","Metformin 1000mg BID",    "adherence_concern", "Patient reports inconsistent adherence to Metformin - misses afternoon doses multiple times per week. No dose adjustment documented."),
        ("M015","CASE002","2024-03-05","Atorvastatin 40mg",       "refill_missed",     "Pharmacy records show Atorvastatin refill was due 2024-02-28. As of 2024-03-05 refill has not been picked up. Patient unreachable."),
        ("M016","CASE003","2024-01-14","Aspirin 81mg",            "prescribed",        "Post-MI antiplatelet therapy. Initiated at hospital discharge. Patient confirmed taking as prescribed."),
        ("M017","CASE003","2024-01-14","Metoprolol Succinate 25mg","prescribed",       "Beta-blocker post-NSTEMI. Initiated at hospital discharge."),
        ("M018","CASE003","2024-01-14","Atorvastatin 40mg",       "prescribed",        "High-intensity statin post-MI. Patient confirmed consistent adherence at all follow-up contacts."),
        ("M019","CASE003","2024-01-14","Clopidogrel 75mg",        "prescribed",        "Dual antiplatelet therapy post-NSTEMI. 12-month course. Patient educated on not stopping without cardiology guidance."),
        ("M020","CASE003","2024-02-15","Aspirin 81mg",            "refill_completed",  "Refill confirmed at mid-program check. Patient demonstrates excellent medication adherence."),
        ("M021","CASE003","2024-02-15","Atorvastatin 40mg",       "refill_completed",  "Refill confirmed. Patient adherent. No adverse effects reported."),
        ("M022","CASE004","2024-02-18","Furosemide 40mg BID",     "prescribed",        "Loop diuretic for CHF management. Critical for fluid management. Prescribed at hospital discharge 2024-02-18."),
        ("M023","CASE004","2024-02-18","Entresto 49/51mg BID",    "prescribed",        "Heart failure medication critical for cardiac function. Prescribed at hospital discharge. Patient must not discontinue without cardiology guidance."),
        ("M024","CASE004","2024-02-18","Metformin 500mg BID",     "prescribed",        "Diabetes management. Prescribed at hospital discharge."),
        ("M025","CASE004","2024-02-18","Tiotropium Inhaler",      "prescribed",        "COPD management. Daily inhaler. Prescribed at hospital discharge."),
        ("M026","CASE004","2024-02-26","Furosemide 40mg BID",     "adherence_concern", "Pharmacy records show Furosemide has NOT been picked up since hospital discharge (8 days ago). Critical medication gap for CHF patient. PCP urgently notified."),
        ("M027","CASE004","2024-02-26","Entresto 49/51mg BID",    "adherence_concern", "Entresto has NOT been picked up from pharmacy since hospital discharge. This is a critical medication adherence failure for a CHF patient with EF 30%."),
        ("M028","CASE004","2024-03-02","Furosemide 40mg BID",     "adherence_concern", "Patient confirmed verbally he ran out of furosemide several days ago. Reports worsening ankle edema and dyspnea. No refill obtained. Emergency escalation initiated."),
        ("M029","CASE005","2024-02-27","Sertraline 100mg",        "prescribed",        "Antidepressant initiated at psychiatric discharge. Patient educated on importance of consistent daily dosing and expected onset of effect (4-6 weeks for full effect)."),
        ("M030","CASE005","2024-03-05","Sertraline 100mg",        "refill_completed",  "Patient reports taking medication consistently. Pharmacy confirms no gap in fills. Side effects (mild nausea and insomnia) discussed."),
        ("M031","CASE005","2024-03-10","Sertraline 100mg",        "refill_completed",  "Continued adherence confirmed at weekly check-in. Side effects improving. No dose adjustment indicated at this time."),
    ]
    c.executemany("INSERT INTO medication_events VALUES (?,?,?,?,?,?)", meds)
    print(f"[OK] Inserted {len(meds)} medication events.")

    conn.close()


def verify():
    conn = pyodbc.connect(CONN_DB)
    c = conn.cursor()
    tables = ["cases", "case_notes", "patient_visits", "case_activity", "medication_events"]
    print("\n── Row counts ──────────────────────")
    for tbl in tables:
        c.execute(f"SELECT COUNT(*) FROM {tbl}")
        count = c.fetchone()[0]
        print(f"  {tbl:<25} {count:>3} rows")
    conn.close()


if __name__ == "__main__":
    print(f"\nCaseAI Copilot — Database Setup")
    print(f"Server  : {SERVER}")
    print(f"Database: {DB_NAME}")
    print(f"Auth    : Windows Authentication\n")
    try:
        create_database()
        create_tables()
        seed_data()
        verify()
        print("\n[DONE] Database setup complete.")
    except Exception as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
