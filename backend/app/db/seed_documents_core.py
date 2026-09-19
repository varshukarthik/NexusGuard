"""Canonical NovaTech Solutions policy & procedure library (FICTIONAL DEMO DATA).

These hand-written documents anchor the most common employee questions (IT support, VPN, laptop replacement,
benefits, reimbursement, procurement, onboarding, security, compliance…). The large synthetic knowledge base in
seed_large_dataset.py adds thousands of further articles around them.

Tuple format is identical to seed_documents.DOCUMENTS:
(id, title, filename, doc_type, owner_dept, classification, allowed_departments, allowed_roles,
 family_key, version, effective_date, owner_code, content)
"""

ALL = ["*"]
EXEC = "Executive"

CORE_DOCUMENTS = [
# ---------------------------------------------------------------- PUBLIC --------------------------------------------
("DOC-1034", "About NovaTech Solutions — Products & Services", "Products and Services.pdf", "Overview", "Marketing",
 "PUBLIC", ALL, ALL, "public-products", "2026.2", "2026-08-20", "NT-0640", """
NovaTech Solutions builds enterprise software that helps mid-market companies automate work securely. Our products are sold in India, Singapore and the United Kingdom.

NovaFlow is our workflow automation platform: visual process design, approvals, SLA tracking and 200+ connectors.

NovaDesk is our customer service platform: omnichannel ticketing, knowledge base, customer portal and CSAT analytics.

Nova AI Suite (generally available since 12 August 2026) adds permission-aware enterprise search, agentic service-desk automation and AI-assisted approvals on top of NovaFlow and NovaDesk.

NovaInsight provides operational analytics dashboards; NovaConnect is our integration and API management layer.

Professional services: implementation, migration from legacy tools, training and 24x7 premium support.

Contact sales at sales@novatech.demo. Customer support is available through the NovaDesk customer portal.
"""),
("DOC-1035", "Public Privacy Notice", "Privacy Notice.pdf", "Policy", "Legal", "PUBLIC", ALL, ALL,
 "privacy-notice", "2.0", "2026-03-01", "NT-0512", """
This notice explains how NovaTech Solutions collects and uses personal data of customers, website visitors and job applicants.

What we collect: contact details you give us, product usage telemetry, and support conversations. We do not sell personal data.

Why we use it: to provide and secure our services, to respond to requests, to meet legal obligations and, with consent, for marketing.

Retention: customer account data is kept for the contract term plus 3 years; job applicant data for 12 months.

Your rights: access, correction, deletion and objection. Contact privacy@novatech.demo. We respond within 30 days.

NovaTech is ISO 27001 certified and completes a SOC 2 Type II audit annually.
"""),
("DOC-1036", "NovaTech Office Locations", "Office Locations.pdf", "Overview", "Operations", "PUBLIC", ALL, ALL,
 "office-locations", "2026.1", "2026-01-10", "NT-0701", """
NovaTech Solutions operates six offices.

Hyderabad (headquarters): NovaTech Campus, HITEC City. Home of Engineering, Product, HR, Finance and the IT Service Desk.

Bengaluru: Whitefield technology centre — Engineering, Data & AI and Customer Success.

Pune: Hinjewadi delivery centre — Engineering, Operations and professional services.

Chennai: OMR operations hub — Customer Success and the 24x7 support desk.

Singapore: Asia-Pacific sales and customer success office.

London: United Kingdom sales office (opening for Nova AI Suite availability in Q1 2027).

Visitors must register at reception and use the NovaGuest Wi-Fi network.
"""),
("DOC-1037", "Careers & Hiring at NovaTech — Public FAQ", "Careers FAQ.pdf", "FAQ", "Human Resources", "PUBLIC", ALL,
 ALL, "careers-faq", "1.3", "2026-05-15", "NT-0233", """
How do I apply? All open roles are listed on the NovaTech careers page. Apply online with your CV; we do not charge any fee at any stage.

What does the interview process look like? A recruiter screen, one or two technical or functional interviews, and a final conversation with the hiring manager. Most processes complete within 3 weeks.

Do you offer hybrid work? Yes. Most roles are hybrid, with up to 3 work-from-home days per week after onboarding.

What benefits do you offer? Health insurance for employees and families, learning budgets, wellness programmes and parental leave. Details are shared with offers.

Do you hire interns and graduates? Yes — the NovaStart graduate programme runs every July.
"""),
("DOC-1038", "Sustainability & Community Commitment", "Sustainability.pdf", "Policy", "Operations", "PUBLIC", ALL, ALL,
 "sustainability", "1.1", "2026-04-22", "NT-0701", """
NovaTech Solutions is committed to operating responsibly.

Targets: 100% renewable electricity in Indian offices by FY28; net-zero operational emissions (Scope 1 and 2) by 2030.

Community: every employee receives two paid volunteering days per year. The NovaTech Foundation funds digital-skills programmes for 5,000 students annually.

Responsible AI: our AI products follow the NovaTech Responsible AI Principles — human oversight, permission-aware data access, transparency and auditability.
"""),
("DOC-1039", "Public Announcement: NovaTech opens Chennai operations hub", "Chennai Hub Announcement.pdf",
 "Announcement", "Marketing", "PUBLIC", ALL, ALL, "press-chennai-hub", "1.0", "2026-06-18", "NT-0640", """
Chennai, 18 June 2026 — NovaTech Solutions today opened a new operations hub on OMR, Chennai. The hub hosts Customer Success and a 24x7 support desk for NovaDesk and Nova AI Suite customers.

The site will employ about 180 people by March 2027 and is certified to the same ISO 27001 controls as our Hyderabad headquarters.
"""),

# ---------------------------------------------------------------- INTERNAL: IT --------------------------------------
("DOC-1040", "IT Service Desk — Support Model & Ownership", "IT Support Model.pdf", "Procedure",
 "Information Technology", "INTERNAL", ALL, ALL, "it-support-model", "1.4", "2026-06-10", "NT-0310", """
Who is responsible for IT support? The IT Service Desk, part of the Information Technology department, owns first-line support for all employees. The IT Service Desk is led by Farhan Sheikh (IT Support Engineer) and reports to Arjun Nair, Security Administrator and head of IT operations.

Support channels:
1. Ask the NovaTech Solutions AI assistant to raise a ticket (fastest — it pre-fills category and priority).
2. Use the IT service portal.
3. Call the Service Desk hotline extension 4357 (HELP) for P1 incidents.

Support tiers: L1 Service Desk (accounts, devices, software); L2 Platform & Network team (VPN, Wi-Fi, cloud access); L3 Security Operations (incidents, suspicious activity).

Hours: 08:00–22:00 IST on weekdays; P1 incidents are covered 24x7 by the on-call engineer.
"""),
("DOC-1041", "IT Incident Escalation Matrix", "IT Escalation Matrix.pdf", "Procedure", "Information Technology",
 "INTERNAL", ALL, ALL, "it-escalation", "2.0", "2026-05-20", "NT-0310", """
Escalation process for an IT issue:
1. Raise a ticket with the correct priority (P1 business down, P2 user blocked, P3 degraded, P4 request).
2. If the first response SLA is missed (P1 1 hour, P2 4 hours, P3 1 business day), reply on the ticket with "ESCALATE" — it moves to the L2 queue lead.
3. If the issue is still unresolved after 2x the SLA, the L2 lead escalates to the IT Operations Manager.
4. Security-related issues (phishing, lost device, suspicious login) always go straight to Security Operations at security@novatech.demo.
5. Business-critical outages affecting more than 25 users are declared a Major Incident; status updates are posted every 30 minutes.

Managers can request a priority review for any ticket that blocks a customer deliverable.
"""),
("DOC-1042", "Laptop & Device Replacement Procedure", "Laptop Replacement Procedure.pdf", "Procedure",
 "Information Technology", "INTERNAL", ALL, ALL, "laptop-replacement", "3.0", "2026-07-01", "NT-0355", """
Laptop replacement process:
1. Raise an IT ticket in the Hardware category describing the fault (the AI assistant can create it for you).
2. The Service Desk runs remote diagnostics within 1 business day.
3. If the fault cannot be fixed, a loaner laptop is issued within 1 business day so you can keep working.
4. Back up any local files to OneDrive; the Service Desk will not recover data from failed disks.
5. The replacement laptop is imaged, encrypted and enrolled in device management before hand-over (typically 3–5 business days).
6. Return the faulty device to the IT desk within 7 days of receiving the replacement.

Eligibility: laptops are refreshed every 4 years automatically. Early replacement outside of a hardware fault needs manager approval.
Lost or stolen devices must be reported to the Service Desk within 2 hours; a police report may be required for insurance.
"""),
("DOC-1043", "VPN Access Guide", "VPN Access Guide.pdf", "Guide", "Information Technology", "INTERNAL", ALL, ALL,
 "vpn-access", "2.2", "2026-06-15", "NT-0355", """
NovaTech uses the NovaSecure VPN (always-on client) to reach internal systems from outside the office.

How to request VPN access:
1. Submit an access request for "VPN — standard" (the AI assistant can create it for you). Your manager approves it.
2. After approval, IT enables your account within 4 business hours.
3. Install the NovaSecure VPN client from the Company Portal (Windows/macOS) — do not download VPN clients from the internet.
4. Sign in with your SSO credentials and approve the MFA prompt.
5. Keep the client connected whenever you work outside the office.

Privileged VPN profiles (production networks) additionally require Security Operations approval and are reviewed every 90 days.

Troubleshooting: if the VPN keeps disconnecting, switch networks, restart the client and check the date/time settings. If it still fails, raise a P2 Network ticket.
"""),
("DOC-1044", "Standard Software Catalog", "Software Catalog.pdf", "Guide", "Information Technology", "INTERNAL", ALL,
 ALL, "software-catalog", "2026.3", "2026-08-01", "NT-0355", """
Software available to all employees without approval: Microsoft 365 (Outlook, Teams, Word, Excel, PowerPoint, OneDrive), Slack, Zoom, Google Chrome, 1Password, Adobe Acrobat Reader, Zscaler client, NovaSecure VPN, Jira, Confluence.

Engineering standard toolset: Visual Studio Code, JetBrains IDEs (licence on request), Git, Docker Desktop, Postman, AWS CLI, Terraform.

Requires manager approval (paid licences): Figma, Adobe Creative Cloud, Tableau, Miro, JetBrains All Products, Grammarly Business.

Requires Security approval: any browser extension with access to company data, database admin tools, remote-access tools.

How to request software: ask the AI assistant to create a software request, or use the Company Portal. Approved software is installed automatically within 1 business day.
"""),
("DOC-1045", "Access Management Procedure", "Access Management Procedure.pdf", "Procedure", "Information Technology",
 "INTERNAL", ALL, ALL, "access-management", "1.6", "2026-04-18", "NT-0310", """
Access to applications and data follows least privilege.

Requesting access:
1. Submit an access request naming the system and the reason.
2. Your manager approves business need; the system owner approves the access level.
3. Access to Confidential systems additionally requires Security Operations approval.
4. Access is provisioned automatically after approval and logged.

Reviews: managers re-certify their team's access every quarter. Unused access is removed after 90 days.
Leavers: all access is revoked on the last working day by 18:00 IST.
Temporary access (for example to a Restricted document) is time-bound — usually 7 days — and expires automatically.
"""),
("DOC-1046", "Password & Authentication Policy", "Authentication Policy.pdf", "Policy", "Information Technology",
 "INTERNAL", ALL, ALL, "authentication-policy", "2.1", "2026-05-10", "NT-0310", """
Passwords must be at least 14 characters and must not be reused across systems. Passphrases are encouraged.

Multi-factor authentication is mandatory for email, VPN, source control, the HR system and the NovaTech Solutions workspace. Use the authenticator app; SMS codes are a fallback only.

Never share passwords or MFA codes — IT will never ask for them. Store work credentials only in the company password manager (1Password).

Accounts lock after 10 failed sign-ins in 15 minutes; the Service Desk can unlock after identity verification.

Service accounts and API keys are owned by a named engineer, stored in the secrets vault and rotated at least every 90 days.
"""),
("DOC-1047", "Cybersecurity Awareness Essentials", "Security Awareness.pdf", "Guide", "Information Technology",
 "INTERNAL", ALL, ALL, "security-awareness", "2026.1", "2026-02-12", "NT-0310", """
Top habits for every employee:
1. Check the sender before clicking links — report suspicious emails with the Report Phishing button.
2. Lock your screen when you step away (Windows+L / Ctrl+Cmd+Q).
3. Never paste Confidential or Restricted data into public AI chatbots — use the NovaTech Solutions assistant.
4. Keep devices updated; restart when prompted.
5. Report lost devices within 2 hours.

Annual security awareness training is mandatory and must be completed by 31 October each year. New joiners complete it in week 1.
"""),
("DOC-1048", "Cloud Platform Guide (AWS & Azure)", "Cloud Platform Guide.pdf", "Guide", "Engineering", "INTERNAL",
 ["Engineering", "Information Technology", "Product", EXEC], ALL, "cloud-platform-guide", "3.2", "2026-07-08", "NT-0417", """
NovaTech runs production on AWS (ap-south-1 primary, ap-southeast-1 DR) and corporate IT workloads on Azure.

Account structure: one AWS organisation with separate accounts for production, staging, development and shared services. Engineers get access to development by default; staging and production access is requested through Access Management.

Infrastructure as code: all infrastructure is defined in Terraform and deployed through the CI pipeline. Manual console changes in production are not allowed.

Cost hygiene: tag every resource with team, project and cost-centre. Development environments shut down automatically at 21:00 IST.

Kubernetes: services run on EKS; Project Phoenix is migrating the remaining VM workloads.
"""),

# ---------------------------------------------------------------- INTERNAL: HR --------------------------------------
("DOC-1049", "How to Request Leave", "How to Request Leave.pdf", "Procedure", "Human Resources", "INTERNAL", ALL, ALL,
 "leave-request-procedure", "1.2", "2026-01-05", "NT-0268", """
How do I request leave?
1. Check your balance — ask the AI assistant "what is my leave balance?".
2. Ask the assistant to submit the leave (for example "apply casual leave for next Monday") or use the Leave page.
3. Review the prepared request and confirm it — nothing is submitted until you approve.
4. Your reporting manager receives it in their Approvals inbox and approves or rejects it.
5. Once approved, your balance is updated automatically and your calendar is blocked.

Notice: casual and earned leave at least 2 working days in advance; sick leave may be requested on the same day. More than 5 consecutive days requires a handover note.
Cancelling: approved leave can be cancelled before the start date from the Leave page.
"""),
("DOC-1050", "Employee Benefits Guide 2026", "Benefits Guide 2026.pdf", "Guide", "Human Resources", "INTERNAL", ALL, ALL,
 "benefits-guide", "2026.1", "2026-01-15", "NT-0233", """
Benefits available to NovaTech employees in India:

Health insurance: family floater cover of ₹10 lakh (employee, spouse, two children); parents can be added at a subsidised premium. Top-up cover available.

Life and accident insurance: 3x annual fixed pay term life cover and ₹25 lakh personal accident cover.

Wellness: 24x7 employee assistance programme (confidential counselling), annual health check-up, gym reimbursement up to ₹1,500 per month.

Learning: ₹50,000 annual learning budget per employee for courses and certifications.

Retirement: provident fund (12% employer contribution) and gratuity as per law; optional NPS.

Other: meal card, internet reimbursement of ₹1,000 per month for hybrid employees, employee referral bonus of ₹75,000 for engineering roles.

Singapore and UK employees receive equivalent local benefits described in the regional addendum.
"""),
("DOC-1051", "Onboarding Documents Checklist", "Onboarding Checklist.pdf", "Checklist", "Human Resources", "INTERNAL",
 ALL, ALL, "onboarding-checklist", "2.0", "2026-06-01", "NT-0268", """
Documents required for onboarding (submit through the HR portal before day 1):
1. Signed offer letter and employment agreement.
2. Government photo ID and address proof.
3. PAN card (India) for payroll tax.
4. Bank account details for salary credit (cancelled cheque or bank letter).
5. Educational certificates and last employer relieving letter.
6. Passport-size photograph for the access badge.
7. Emergency contact form and health insurance nominee form.

Day 1: collect your laptop, complete SSO and MFA enrolment, and meet your onboarding buddy.
All documents are stored in the HR system with Confidential classification and are visible only to HR operations.
"""),
("DOC-1052", "Updating Your Employee Information", "Update Employee Information.pdf", "Procedure", "Human Resources",
 "INTERNAL", ALL, ALL, "update-employee-info", "1.1", "2026-03-12", "NT-0268", """
How can I update my employee information?
1. Personal details (address, phone, emergency contact): edit them yourself in the HR portal under My Profile — changes apply immediately.
2. Bank account or tax details: submit a change request with supporting proof; HR Operations verifies it within 3 business days. Changes after the 20th apply from the next payroll.
3. Legal name or date of birth corrections: raise an HR request with a government document.
4. Job title, department or manager changes are made by HR after manager approval — employees cannot change these themselves.

Questions: hr.ops@novatech.demo or ask the AI assistant to raise an HR request.
"""),
("DOC-1053", "Attendance & Working Hours Policy", "Attendance Policy.pdf", "Policy", "Human Resources", "INTERNAL", ALL,
 ALL, "attendance-policy", "2.0", "2026-02-01", "NT-0233", """
Standard working hours are 9:30 to 18:30 IST, Monday to Friday, with core collaboration hours of 11:00 to 16:00 IST.

Hybrid attendance: employees are expected in the office at least 2 days per week; teams agree anchor days.

Attendance is recorded automatically through badge access or VPN sign-in. Missing attendance for more than 3 days without approved leave is flagged to the manager.

Shift-based teams (24x7 support) follow the published rota; shift allowance is paid monthly.
Overtime for non-exempt roles must be pre-approved by the manager.
"""),
("DOC-1054", "Performance Review Framework", "Performance Review Framework.pdf", "Policy", "Human Resources",
 "INTERNAL", ALL, ALL, "performance-framework", "3.0", "2026-03-01", "NT-0233", """
NovaTech runs two review cycles per year: a mid-year check-in (October) and an annual review (April).

Ratings: Exceeds Expectations, Meets Expectations, Partially Meets, Below Expectations.

Process:
1. Employee self-assessment against goals and NovaTech values.
2. Manager assessment with peer feedback from at least two colleagues.
3. Department calibration to ensure consistency.
4. Review conversation and documented development plan.

Individual ratings are Confidential — visible only to the employee, their manager chain and HR.
"""),
("DOC-1055", "Promotion Policy", "Promotion Policy.pdf", "Policy", "Human Resources", "INTERNAL", ALL, ALL,
 "promotion-policy", "2.1", "2026-03-01", "NT-0233", """
Promotions are considered once a year after the annual review (April), with an exception window in October for critical roles.

Eligibility: at least 12 months in the current level, a Meets or Exceeds rating in the latest cycle, and demonstrated performance at the next level for at least two quarters.

Process: the manager submits a promotion case; the department promotion panel reviews it; HR validates budget and band. Outcomes are communicated by the manager.

Promotions come with a band change; pay adjustments follow the Confidential compensation guidelines.
"""),
("DOC-1056", "Learning & Training Programs 2026", "Training Programs.pdf", "Guide", "Human Resources", "INTERNAL", ALL,
 ALL, "training-programs", "2026.1", "2026-01-20", "NT-0268", """
Training programmes available in 2026:
- NovaStart onboarding bootcamp (all new joiners, 2 weeks).
- Leading at NovaTech (new managers, 6 sessions).
- Secure Coding Academy (engineers, mandatory annually).
- Cloud Practitioner track with AWS certification sponsorship.
- Data & AI Foundations (open to all, self-paced).
- Customer Excellence programme (Sales and Customer Success).
- Security awareness (mandatory for all, due 31 October).

Enrol through the Learning portal. External courses are funded from the ₹50,000 annual learning budget with manager approval.
"""),
("DOC-1057", "Recruitment & Hiring Procedure", "Recruitment Procedure.pdf", "Procedure", "Human Resources",
 "INTERNAL", ALL, ALL, "recruitment-procedure", "1.5", "2026-04-05", "NT-0233", """
How hiring works at NovaTech:
1. The hiring manager raises a requisition against an approved headcount plan.
2. HR Talent Acquisition publishes the role and sources candidates (referrals are encouraged).
3. Interviews: recruiter screen, functional interviews, hiring-manager round. Every panel includes at least one trained interviewer.
4. Feedback is submitted within 24 hours of each interview.
5. Offers are prepared by HR within the approved band and approved by the department head.
6. Background verification completes before the start date.

Employee referral bonus is paid after the new hire completes 90 days.
"""),
("DOC-1058", "HR Frequently Asked Questions", "HR FAQ.pdf", "FAQ", "Human Resources", "INTERNAL", ALL, ALL,
 "hr-faq", "2026.2", "2026-07-10", "NT-0268", """
When is salary credited? On the last working day of each month.
How do I download my payslip? From the HR portal under Payroll > Payslips.
Who is my HR business partner? Each department has an HR business partner listed on the HR portal; Engineering is supported by Pooja Desai.
How do I get an employment verification letter? Raise an HR request; letters are issued within 2 business days.
Can I carry forward leave? Up to 12 earned leaves; casual leave cannot be carried forward.
What is the notice period? 60 days for most roles, 90 days for managers.
How do I report a workplace concern? Speak to your HR business partner or use the anonymous Ethics Hotline.
"""),

# ---------------------------------------------------------------- INTERNAL: Finance / Procurement ------------------
("DOC-1059", "Expense Reimbursement Procedure", "Expense Reimbursement.pdf", "Procedure", "Finance", "INTERNAL", ALL,
 ALL, "expense-reimbursement", "2.4", "2026-04-01", "NT-0420", """
What is the reimbursement process?
1. Keep itemised receipts for every business expense.
2. Submit an expense claim in the Finance portal within 30 days of the expense, choosing the correct category and cost centre.
3. Your manager approves the claim; claims above ₹25,000 also need department-head approval.
4. Finance verifies receipts and policy limits within 5 business days.
5. Approved claims are paid with the next weekly reimbursement run (every Thursday) to your salary account.

Not reimbursable: personal entertainment, fines, alcohol (except approved client dinners), upgrades not covered by the Travel & Expense Policy.
Travel expenses must follow the Travel & Expense Policy limits (hotel ₹7,500 per night in metro cities).
"""),
("DOC-1060", "Purchase Request (PR) Procedure", "Purchase Request Procedure.pdf", "Procedure", "Operations",
 "INTERNAL", ALL, ALL, "purchase-request", "2.1", "2026-05-05", "NT-0701", """
Steps to create a purchase request:
1. Check whether the item is available from a preferred vendor in the vendor catalogue.
2. Create a purchase request (the AI assistant can prepare it) with item, quantity, estimated cost, cost centre and business justification.
3. Attach quotes: one quote up to ₹1 lakh; three competitive quotes above ₹1 lakh.
4. The budget owner approves the request (see the Procurement Approval Matrix for limits).
5. Procurement (Operations) converts the approved request into a purchase order and sends it to the vendor.
6. Goods receipt is confirmed by the requester; Finance pays the invoice within the agreed terms (usually net 45).

New vendors must complete security and compliance due diligence before a purchase order can be issued.
"""),
("DOC-1061", "Procurement Approval Matrix", "Procurement Approval Matrix.pdf", "Policy", "Operations", "INTERNAL", ALL,
 ALL, "procurement-approval", "3.0", "2026-05-05", "NT-0701", """
What is the approval process for procurement?
- Up to ₹50,000: line manager approval.
- ₹50,000 to ₹5 lakh: department head approval.
- ₹5 lakh to ₹50 lakh: department head and Finance Manager approval.
- Above ₹50 lakh: Chief Operating Officer approval and a Procurement Committee review.

Software and cloud services always need IT Security review regardless of value.
Contracts longer than 12 months or with auto-renewal need Legal review.
Splitting purchases to stay below an approval limit is a policy violation.
"""),
("DOC-1062", "Invoice Processing & Vendor Payments", "Invoice Processing.pdf", "Procedure", "Finance", "INTERNAL", ALL,
 ALL, "invoice-processing", "1.3", "2026-03-18", "NT-0420", """
Vendors send invoices to ap@novatech.demo quoting the purchase order number.

Three-way match: Accounts Payable matches the invoice with the purchase order and the goods receipt before payment.
Standard payment terms are net 45 days; MSME vendors are paid within 30 days as required by law.
Invoices without a valid PO number are returned to the vendor.
Payment runs happen every Tuesday and Friday.
"""),
("DOC-1063", "Cost Centre & Budget Management Guide", "Budget Management Guide.pdf", "Guide", "Finance", "INTERNAL",
 ALL, ALL, "budget-guide", "2026.1", "2026-04-02", "NT-0420", """
Every department owns one or more cost centres (for example CC-ENG-01 for Engineering platform teams).

Budgets are set annually during the April planning cycle and reviewed quarterly. Budget owners (department heads) can see detailed spend for their cost centres; detailed department budgets are Confidential.

Re-allocation between cost centres above ₹10 lakh requires Finance Manager approval.
Monthly spend reports are published to budget owners by the 7th working day.
"""),

# ---------------------------------------------------------------- INTERNAL: Legal / Compliance ---------------------
("DOC-1064", "Data Protection Policy", "Data Protection Policy.pdf", "Policy", "Legal", "INTERNAL", ALL, ALL,
 "data-protection", "2.0", "2026-03-01", "NT-0512", """
NovaTech processes personal data lawfully, fairly and only for defined purposes, in line with India's Digital Personal Data Protection Act, Singapore PDPA and UK GDPR.

Rules for employees:
1. Collect only the personal data needed for the task (data minimisation).
2. Store personal data only in approved systems; never in personal drives or public AI tools.
3. Share personal data internally on a need-to-know basis and never externally without a data processing agreement.
4. Report any suspected personal data breach to privacy@novatech.demo within 1 hour — Legal assesses notification duties.

The Data Protection Officer is Karthik Menon (Legal).
"""),
("DOC-1065", "Document Retention Policy", "Document Retention Policy.pdf", "Policy", "Legal", "INTERNAL", ALL, ALL,
 "document-retention", "1.4", "2026-02-10", "NT-0512", """
Retention periods:
- Financial records and invoices: 8 years.
- Employee records: employment period plus 7 years.
- Customer contracts: contract term plus 7 years.
- Recruitment records of unsuccessful candidates: 12 months.
- Audit logs of the NovaTech Solutions workspace: 3 years.
- Email: 5 years unless under legal hold.

Records under legal hold must not be deleted. Destruction of paper records uses certified shredding.
"""),
("DOC-1066", "Acceptable Use Policy", "Acceptable Use Policy.pdf", "Policy", "Legal", "INTERNAL", ALL, ALL,
 "acceptable-use", "3.1", "2026-01-25", "NT-0512", """
Company systems are provided for business use; limited personal use is allowed if it does not interfere with work or security.

Not allowed: installing unapproved software, bypassing security controls, sharing credentials, accessing data you are not authorised to see, using company systems for illegal or harassing content, and uploading Confidential or Restricted data to unapproved cloud or AI services.

Monitoring: NovaTech logs access to systems and data for security and compliance purposes, including AI assistant queries.
Violations may lead to disciplinary action.
"""),
("DOC-1067", "Internal Audit Procedure", "Internal Audit Procedure.pdf", "Procedure", "Legal", "INTERNAL", ALL, ALL,
 "internal-audit", "1.2", "2026-04-28", "NT-0512", """
Internal audit runs a risk-based annual audit plan approved by the Audit Committee.

Audit steps: planning and scoping; fieldwork and evidence collection; draft findings discussed with the process owner; management action plans with owners and dates; final report to the Audit Committee.

Findings are rated High, Medium or Low. High findings must be closed within 60 days and are tracked monthly.
Employees must provide auditors with requested evidence within 5 business days.
"""),
("DOC-1068", "Enterprise Risk Management Procedure", "Risk Management Procedure.pdf", "Procedure", "Legal",
 "INTERNAL", ALL, ALL, "risk-management", "1.1", "2026-05-02", "NT-0512", """
Every department maintains a risk register reviewed quarterly.

Risk scoring: likelihood (1–5) x impact (1–5). Scores of 15 or more are High and are escalated to the Executive risk review.

Each risk has an owner, mitigation actions and a target date. Project risks are recorded in the project record and summarised in monthly status reports.
"""),
("DOC-1069", "Compliance & Corporate Governance Policy", "Governance Policy.pdf", "Policy", "Legal", "INTERNAL", ALL,
 ALL, "governance-policy", "1.0", "2026-01-30", "NT-0512", """
NovaTech's Board is supported by an Audit Committee, a Nomination & Remuneration Committee and a Risk Committee.

Policy ownership: every company policy has an owning department and is reviewed at least annually. Policies are published in the NovaTech Solutions knowledge base with a classification.

Delegation of authority: approval limits for spend, hiring and contracts are defined in the Delegation of Authority matrix maintained by Finance and Legal.
"""),

# ---------------------------------------------------------------- INTERNAL: Projects & Operations ------------------
("DOC-1070", "Project Management Policy 2024", "Project Management Policy 2024.pdf", "Policy", "Operations",
 "INTERNAL", ALL, ALL, "project-policy", "1.0", "2024-06-01", "NT-0701", """
Project Management Policy v1.0 (2024).

All projects above ₹10 lakh must have a project charter approved by the sponsoring department head.

Status reports are published monthly. Health is reported as Green, Amber or Red.

A project is considered delayed when a milestone slips by more than 4 weeks. Delayed projects are reviewed at the quarterly portfolio review.

Risk registers are optional for projects under ₹50 lakh.

Project closure requires a lessons-learned session within 60 days of go-live.
"""),
("DOC-1071", "Project Management Policy 2026", "Project Management Policy 2026.pdf", "Policy", "Operations",
 "INTERNAL", ALL, ALL, "project-policy", "2.0", "2026-04-01", "NT-0701", """
Project Management Policy v2.0 (2026). Supersedes the 2024 policy.

All projects above ₹5 lakh must have a project charter approved by the sponsoring department head.

Status reports are published every 2 weeks in the NovaTech Solutions workspace. Health is reported as Green, Amber or Red with a written reason for Amber and Red.

A project is considered delayed when a milestone slips by more than 2 weeks or its deadline has passed. Delayed projects are reviewed at the monthly portfolio review.

A risk register is mandatory for every project; the top three risks are reviewed in each status report.

Project closure requires a lessons-learned session within 30 days of go-live.
"""),
("DOC-1072", "Organization Structure & Business Units", "Organization Structure.pdf", "Overview", "Human Resources",
 "INTERNAL", ALL, ALL, "org-structure", "2026.2", "2026-07-01", "NT-0233", """
NovaTech Solutions is organised into five business units:

Technology & Products — Engineering, Product and Information Technology. Led by the COO, Vikram Mehta, with Priya Reddy managing core Engineering.

Go-To-Market — Sales, Marketing and Customer Success.

Corporate Functions — Human Resources (Ananya Rao), Finance (Kavya Iyer) and Legal (Karthik Menon).

Operations — facilities, procurement, vendor management and delivery operations (Divya Nair).

Executive Office — the CEO Lakshmi Krishnan and the executive leadership team.

Each department has a department head, one or more cost centres and an HR business partner.
"""),
("DOC-1073", "Department Process Ownership Register", "Process Ownership Register.pdf", "Register", "Operations",
 "INTERNAL", ALL, ALL, "process-ownership", "1.3", "2026-06-20", "NT-0701", """
Which department owns this process?
- Leave, onboarding, payroll queries, performance reviews, promotions: Human Resources.
- IT support, laptops, VPN, software, access management: Information Technology.
- Security incidents, phishing reports, security awareness: Information Technology (Security Operations).
- Expense reimbursement, invoices, budgets, cost centres: Finance.
- Purchase requests, vendor onboarding, purchase orders, facilities, travel desk: Operations.
- Contracts, data protection, document retention, compliance: Legal.
- Customer escalations and renewals: Customer Success; new deals and quotes: Sales.
- Product roadmap and release notes: Product.
"""),
("DOC-1074", "Customer Escalation Procedure", "Customer Escalation Procedure.pdf", "Procedure", "Customer Success",
 "INTERNAL", ALL, ALL, "customer-escalation", "1.2", "2026-05-25", "NT-0701", """
When a customer escalates:
1. Log the escalation in NovaDesk with severity (Sev 1–4) and the affected product.
2. The account's Customer Success Manager owns communication and sends an acknowledgement within 1 hour for Sev 1.
3. Engineering on-call joins Sev 1 bridges within 30 minutes.
4. Status updates every 2 hours until resolution; a root-cause report within 5 business days.
5. Sales is informed when a renewal or expansion is at risk.
"""),

# ---------------------------------------------------------------- CONFIDENTIAL -------------------------------------
("DOC-1075", "Security Incident Response Procedure", "Incident Response Procedure.pdf", "Procedure",
 "Information Technology", "CONFIDENTIAL", ["Information Technology", EXEC, "Legal"], ALL, "incident-response",
 "2.3", "2026-06-02", "NT-0310", """
Incident response phases: detect, triage, contain, eradicate, recover, lessons learned.

Severity: SEV-1 (confirmed breach of Confidential/Restricted data or production outage) — incident commander assigned within 15 minutes, Legal and the COO informed within 1 hour. SEV-2 (contained compromise of a single account or device). SEV-3 (suspicious activity, no impact).

Containment playbooks cover compromised credentials, malware on endpoints, cloud misconfiguration and data exfiltration attempts.
Regulatory notifications are decided by Legal; customer notifications by the COO.
"""),
("DOC-1076", "Department Budget Summary FY26 — People Functions", "HR Budget FY26.xlsx", "Budget",
 "Human Resources", "CONFIDENTIAL", ["Human Resources", "Finance", EXEC], ALL, "hr-budget-fy26", "1.0",
 "2026-04-15", "NT-0233", """
HR budget FY26 (Confidential): ₹6.8 crore total — talent acquisition ₹2.1 crore, learning & development ₹1.9 crore, wellness ₹0.9 crore, HR systems ₹0.8 crore, engagement ₹1.1 crore.
H1 spend is 46% of budget. Learning spend is under-utilised in Sales and Operations.
"""),
("DOC-1077", "Manager Report — Engineering Attrition & Headcount Q3 2026", "Eng Headcount Q3.pdf", "Report",
 "Engineering", "CONFIDENTIAL", ["Engineering", "Human Resources", EXEC], ALL, "eng-headcount-q3", "1.0",
 "2026-09-03", "NT-0417", """
Engineering headcount at the end of Q3 2026 is 612 (target 640). Voluntary attrition is 11.8% annualised, down from 14.2% last year.
Hardest-to-fill roles: senior SRE and ML engineers. Two teams (Payments, Data Platform) are below 80% of planned capacity.
"""),

# ---------------------------------------------------------------- RESTRICTED ---------------------------------------
("DOC-1078", "Strategic Plan FY27–FY29", "Strategic Plan FY27-29.pdf", "Board Paper", "Executive", "RESTRICTED",
 [EXEC], ALL, "strategic-plan", "1.0", "2026-08-25", "NT-0001", """
Strategic Plan FY27–FY29 (Restricted). Ambition: ₹500 crore revenue by FY28 and ₹650 crore by FY29 with 22% operating margin.
Pillars: AI-native products (Nova AI Suite as the growth engine), UK and Middle East expansion, partner-led mid-market sales, and one tuck-in acquisition per year.
"""),
("DOC-1079", "Security Architecture & Configuration Baseline", "Security Baseline.pdf", "Standard",
 "Information Technology", "RESTRICTED", ["Information Technology", EXEC], ["security_admin", "senior_executive"],
 "security-baseline", "4.0", "2026-07-15", "NT-0310", """
Security configuration baseline (Restricted — administrators only). This document describes control objectives only; it contains no credentials.
Network: production VPCs have no public subnets for data stores; administrative access only through the bastion with just-in-time approval.
Identity: conditional access requires compliant devices; privileged roles use separate admin accounts with hardware keys.
Logging: all production and workspace audit logs stream to the SIEM with 3-year retention.
"""),
]
