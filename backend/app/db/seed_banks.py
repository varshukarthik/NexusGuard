"""Vocabulary banks for the synthetic NovaTech Solutions dataset.

Everything here is FICTIONAL. Person names are random first/last-name combinations; company, vendor and customer
names are invented. Real software products appear only as items in a software catalogue.
"""

FIRST_NAMES = """Aarav Aditi Akash Alisha Amrita Anand Anika Anjali Ankit Anushka Arjun Arnav Aryan Avni Ayesha Bhavana
Chetan Chitra Daksh Deepa Deepak Devika Dhruv Diya Esha Gaurav Gauri Harini Harsh Isha Ishita Jatin Jaya Kabir Kajal
Karan Kavitha Keerthi Kiran Kriti Kunal Lakshya Lavanya Madhav Mahima Manav Maya Meghna Mihir Mira Mohit Nandini
Naveen Neel Nidhi Nikita Nisha Omkar Pallavi Parth Pooja Pranav Prarthana Preeti Rachit Radhika Raghav Rajat Ramya
Ranjit Reema Reyansh Ritika Rohit Ruchi Sahil Sakshi Samar Sameera Sanjay Sara Saurabh Shreya Shruti Siddhi Simran
Smita Sonal Srinivas Sukanya Sunil Swati Tanish Tara Tejas Trisha Uday Urvi Varun Vedant Vidya Vinay Vishal Yamini
Yash Zoya Adrian Alicia Ben Chloe Daniel Elena Ethan Grace Hannah Isaac Jasmine Julian Leah Liam Lucas Mei Nathan
Nina Oliver Priscilla Ryan Sophie Wei Zara Farid Imran Nadia Omar Salma Tariq Hui Jun Kenji Min""".split()

LAST_NAMES = """Acharya Agarwal Ahuja Bajaj Banerjee Bhat Bhatt Chandra Chatterjee Chawla Chopra Das Dasgupta Desai Dhillon
Dixit Dubey Gandhi Ghosh Goel Gokhale Gupta Hegde Iyengar Jain Joshi Kamath Kapoor Karnik Kashyap Khanna Kohli
Krishnamurthy Kulkarni Kumar Lal Mahajan Malhotra Mani Mathur Menon Mishra Mukherjee Murthy Nadkarni Naidu Nambiar
Narang Natarajan Oberoi Pai Pandey Parekh Patil Pillai Prabhu Prasad Raghavan Rajan Raman Rao Rastogi Reddy Saini
Saxena Sen Sethi Shah Shankar Sharma Shenoy Shetty Sinha Srinivasan Subramanian Suri Swaminathan Tandon Thakur
Thomas Tiwari Trivedi Varghese Venkatesan Verma Vyas Wadhwa Yadav Anderson Brooks Carter Chen Clarke Evans Fernandes
Foster Hughes Kim Lee Lim Martin Nguyen Ong Patel Reid Silva Tan Walker Wong Young""".split()

LOCATIONS = [  # id, name, city, country, kind, address, tz
    ("LOC-HYD", "Hyderabad HQ — NovaTech Campus", "Hyderabad", "India", "Headquarters", "HITEC City, Hyderabad",
     "Asia/Kolkata"),
    ("LOC-BLR", "Bengaluru Technology Centre", "Bengaluru", "India", "Office", "Whitefield, Bengaluru", "Asia/Kolkata"),
    ("LOC-PNQ", "Pune Delivery Centre", "Pune", "India", "Office", "Hinjewadi Phase 2, Pune", "Asia/Kolkata"),
    ("LOC-MAA", "Chennai Operations Hub", "Chennai", "India", "Operations hub", "OMR, Chennai", "Asia/Kolkata"),
    ("LOC-SIN", "Singapore Office", "Singapore", "Singapore", "Sales office", "One-North, Singapore",
     "Asia/Singapore"),
    ("LOC-LON", "London Office", "London", "United Kingdom", "Sales office", "Shoreditch, London", "Europe/London"),
]

BUSINESS_UNITS = [
    ("BU-TECH", "Technology & Products", "Builds and runs NovaTech's products, platforms and internal IT.",
     ["Engineering", "Product", "Information Technology"]),
    ("BU-GTM", "Go-To-Market", "Wins, grows and retains customers.", ["Sales", "Marketing", "Customer Success"]),
    ("BU-CORP", "Corporate Functions", "People, finance and legal services for the company.",
     ["Human Resources", "Finance", "Legal"]),
    ("BU-OPS", "Operations", "Facilities, procurement, vendor management and delivery operations.", ["Operations"]),
    ("BU-EXEC", "Executive Office", "Company leadership and strategy.", ["Executive"]),
]

DEPT_DESCRIPTIONS = {
    "Executive": "Company leadership: strategy, board relations and executive decision-making.",
    "Engineering": "Designs, builds and operates NovaFlow, NovaDesk, NovaInsight and the Nova AI Suite.",
    "Human Resources": "Talent acquisition, onboarding, payroll, performance, learning and employee relations.",
    "Finance": "Financial planning, accounting, payables, receivables, budgets and cost-centre reporting.",
    "Sales": "New business, expansion and renewals across India, Singapore and the UK.",
    "Marketing": "Brand, demand generation, product marketing, events and communications.",
    "Information Technology": "IT Service Desk, devices, corporate applications, networks and security operations.",
    "Legal": "Contracts, compliance, data protection, governance and litigation management.",
    "Operations": "Facilities, procurement, vendor management, travel desk and delivery operations.",
    "Product": "Product strategy, roadmaps, research, design and release management.",
    "Customer Success": "Onboarding, adoption, support escalations and renewals for NovaTech customers.",
}

# department -> profile used to generate people
DEPT_PROFILES = {
    "Engineering": dict(
        share=0.30, loc=[("Hyderabad", 5), ("Bengaluru", 4), ("Pune", 3)],
        ic=[("software_engineer", "Software Engineer", 5), ("senior_engineer", "Senior Software Engineer", 3),
            ("senior_engineer", "Staff Software Engineer", 1), ("devops_engineer", "DevOps Engineer", 1),
            ("devops_engineer", "Site Reliability Engineer", 1), ("qa_engineer", "QA Engineer", 2),
            ("data_scientist", "Data Scientist", 1), ("data_scientist", "ML Engineer", 1)],
        mgr=("engineering_manager", "Engineering Manager"), director="Director of Engineering",
        skills="Python FastAPI Java Spring Go TypeScript React Node.js PostgreSQL Kafka Redis Kubernetes Docker AWS "
               "Terraform GraphQL Elasticsearch PyTorch MLOps gRPC Playwright".split()),
    "Product": dict(
        share=0.05, loc=[("Hyderabad", 3), ("Bengaluru", 2)],
        ic=[("product_manager", "Product Manager", 3), ("product_manager", "Senior Product Manager", 1),
            ("designer", "Product Designer", 2), ("designer", "UX Researcher", 1)],
        mgr=("product_lead", "Group Product Manager"), director=None,
        skills="Roadmapping Discovery Analytics SQL Figma UX-research Pricing A/B-testing Jira Storytelling".split()),
    "Information Technology": dict(
        share=0.065, loc=[("Hyderabad", 4), ("Bengaluru", 1), ("Chennai", 1)],
        ic=[("it_support", "IT Support Engineer", 4), ("it_support", "Network Engineer", 1),
            ("it_support", "Systems Administrator", 1), ("security_analyst", "Security Analyst", 2)],
        mgr=("it_manager", "IT Operations Manager"), director=None,
        skills="Intune Entra-ID ServiceNow Networking Zscaler M365 Linux Windows-Server SIEM Incident-response".split()),
    "Human Resources": dict(
        share=0.045, loc=[("Hyderabad", 4), ("Bengaluru", 1), ("Singapore", 1)],
        ic=[("hr_specialist", "HR Specialist", 3), ("recruiter", "Talent Acquisition Partner", 2),
            ("hr_specialist", "HR Business Partner", 1), ("hr_specialist", "Payroll Specialist", 1)],
        mgr=("hr_manager", "HR Manager"), director=None,
        skills="Recruiting Workday Payroll Employee-relations Onboarding HR-analytics Compensation L&D".split()),
    "Finance": dict(
        share=0.055, loc=[("Hyderabad", 4), ("Pune", 1)],
        ic=[("finance_analyst", "Finance Analyst", 3), ("accountant", "Accountant", 3),
            ("finance_analyst", "FP&A Analyst", 2)],
        mgr=("finance_manager", "Finance Manager"), director=None,
        skills="FP&A SAP Excel Tally GST Accounts-payable Treasury Audit Power-BI Budgeting".split()),
    "Sales": dict(
        share=0.12, loc=[("Hyderabad", 2), ("Bengaluru", 2), ("Pune", 1), ("Singapore", 2), ("London", 1)],
        ic=[("sales_executive", "Account Executive", 4), ("sales_executive", "Sales Development Representative", 3),
            ("sales_executive", "Solutions Consultant", 2)],
        mgr=("sales_director", "Regional Sales Manager"), director="Sales Director",
        skills="Enterprise-sales Negotiation Salesforce Solution-selling Forecasting Demos Partnerships".split()),
    "Marketing": dict(
        share=0.055, loc=[("Hyderabad", 3), ("Bengaluru", 2), ("Singapore", 1)],
        ic=[("marketing_specialist", "Marketing Specialist", 3), ("marketing_specialist", "Content Strategist", 2),
            ("marketing_specialist", "Product Marketing Manager", 1)],
        mgr=("marketing_manager", "Marketing Manager"), director=None,
        skills="SEO Content Campaigns HubSpot Events Brand Analytics Copywriting Social-media".split()),
    "Legal": dict(
        share=0.02, loc=[("Hyderabad", 3), ("Singapore", 1)],
        ic=[("legal_associate", "Legal Associate", 3), ("legal_associate", "Compliance Analyst", 2)],
        mgr=("legal_counsel", "Senior Legal Counsel"), director=None,
        skills="Contracts Privacy Compliance Litigation IP Regulatory Negotiation".split()),
    "Operations": dict(
        share=0.11, loc=[("Hyderabad", 3), ("Pune", 2), ("Chennai", 2)],
        ic=[("operations_analyst", "Operations Analyst", 3), ("procurement_specialist", "Procurement Specialist", 2),
            ("operations_analyst", "Facilities Coordinator", 1), ("operations_analyst", "Delivery Coordinator", 2)],
        mgr=("operations_manager", "Operations Manager"), director="Director of Operations",
        skills="Procurement Vendor-management Facilities Six-Sigma SAP-Ariba Logistics Planning".split()),
    "Customer Success": dict(
        share=0.12, loc=[("Chennai", 4), ("Bengaluru", 2), ("Singapore", 1), ("London", 1)],
        ic=[("customer_success_manager", "Customer Success Manager", 3), ("support_engineer", "Support Engineer", 4),
            ("customer_success_manager", "Implementation Consultant", 2)],
        mgr=("cs_lead", "Customer Success Lead"), director="Director of Customer Success",
        skills="Customer-onboarding NovaDesk NovaFlow Escalations Renewals SQL Troubleshooting Training".split()),
    "Executive": dict(
        share=0.005, loc=[("Hyderabad", 1)],
        ic=[("executive_staff", "Chief of Staff", 1), ("executive_staff", "Executive Assistant", 2)],
        mgr=("executive_staff", "Chief of Staff"), director=None,
        skills="Strategy Board-relations Communications Planning".split()),
}

CODENAMES = """Aquila Andromeda Aurora Borealis Cassini Castor Cepheus Comet Corvus Cygnus Draco Eclipse Equinox Falcon
Fenix Galileo Gemini Halo Horizon Hydra Indus Juno Kepler Lumen Lynx Lyra Meridian Mercury Nebula Neptune Nimbus
Nova Octans Onyx Orbit Pegasus Perseus Polaris Pulsar Quasar Radiant Rigel Saturn Sirius Solstice Spectra Stellar
Tempo Titan Triton Umbra Vega Vertex Voyager Zenith Zephyr Kaveri Godavari Narmada Tapti Yamuna Ganga Krishna
Brahma Indigo Saffron Cobalt Cedar Maple Banyan Lotus Peacock Tiger Monsoon Himalaya Deccan Konark Ajanta Ellora
Hampi Sanchi Charminar Golconda Marina""".split()

PROJECT_THEMES = {
    "Engineering": (["Payments", "Identity & Access", "Enterprise Search", "Notifications", "Billing", "Observability",
                     "Data Platform", "Mobile App", "API Gateway", "Workflow Engine", "Customer 360",
                     "Integration Hub", "Reporting Engine", "Scheduling Service", "Audit Trail", "Document Service",
                     "Analytics Pipeline", "Recommendation Engine", "Pricing Service", "Tenant Onboarding",
                     "NovaDesk Chat", "NovaFlow Designer", "AI Copilot", "Vector Search", "Event Streaming"],
                    ["Modernization", "Re-platforming", "v2", "Migration to Kubernetes", "Hardening",
                     "Performance Program", "Rewrite", "SDK", "Automation", "Multi-region Rollout", "Cost Optimisation",
                     "Reliability Program"]),
    "Product": (["NovaFlow", "NovaDesk", "Nova AI Suite", "NovaInsight", "NovaConnect", "Mobile", "Admin Console",
                 "Marketplace"],
                ["Roadmap 2027", "Pricing Revamp", "Usability Study", "Onboarding Redesign", "Feature Adoption Program",
                 "Accessibility Upgrade", "Packaging Refresh", "Customer Research Sprint"]),
    "Information Technology": (["Laptop Refresh", "Zero Trust Network", "Email Security", "Service Desk",
                                "Identity Governance", "Endpoint Management", "Wi-Fi Upgrade", "SIEM", "Backup",
                                "Collaboration Tools", "Asset Management", "Privileged Access"],
                               ["Rollout", "Upgrade", "Consolidation", "Automation", "Migration", "Hardening",
                                "Phase 2"]),
    "Human Resources": (["HRIS", "Performance Cycle", "Onboarding Experience", "Learning Platform", "Payroll",
                         "Employee Engagement", "Diversity Hiring", "Wellness", "Campus Hiring", "Rewards"],
                        ["Transformation", "Redesign", "Automation", "2026 Program", "Rollout", "Refresh"]),
    "Finance": (["Month-end Close", "Accounts Payable", "Revenue Recognition", "Treasury", "Expense Management",
                 "FP&A Forecasting", "GST Compliance", "Cost Allocation", "Procure-to-Pay", "Audit Readiness"],
                ["Automation", "Modernization", "Program", "Upgrade", "Controls Review", "Dashboard"]),
    "Sales": (["CRM", "Partner Channel", "Enterprise Accounts", "Singapore Expansion", "UK Launch", "Deal Desk",
               "Sales Enablement", "Territory Planning", "Pricing Desk"],
              ["Program", "Rollout", "Playbook", "Acceleration", "Optimisation", "2027 Plan"]),
    "Marketing": (["Brand Refresh", "Website", "Demand Generation", "Customer Advocacy", "Events", "Content Hub",
                   "Webinar Series", "ABM", "Analyst Relations"],
                  ["Program", "Relaunch", "Campaign", "2026", "Automation", "Q4 Push"]),
    "Legal": (["Contract Lifecycle", "Privacy Program", "DPDP Readiness", "Policy Library", "Litigation Tracker",
               "Trademark Portfolio", "Vendor Contracts"],
              ["Implementation", "Review", "Remediation", "Program", "Automation"]),
    "Operations": (["Facilities", "Vendor Consolidation", "Travel Desk", "Workplace", "Procurement Portal",
                    "Delivery Excellence", "Hyderabad Campus", "Chennai Hub", "Fleet", "Energy Efficiency"],
                   ["Upgrade", "Program", "Optimisation", "Expansion", "Automation", "Fit-out"]),
    "Customer Success": (["Customer Onboarding", "Health Scoring", "Renewal Desk", "Support Knowledge Base",
                          "Escalation Management", "Customer Academy", "Adoption Analytics", "24x7 Support"],
                         ["Program", "Redesign", "Automation", "Expansion", "Playbook"]),
    "Executive": (["Strategic Partnership", "Market Entry", "Corporate Development", "Board Governance",
                   "Investor Relations"], ["Evaluation", "Program", "Review"]),
}

PUBLIC_PROJECTS = [
    ("Open Source Connector SDK", "Engineering", "Publish an open-source SDK so partners can build NovaFlow connectors."),
    ("Public API Developer Portal", "Engineering", "Launch a public developer portal with API reference and sandbox."),
    ("Accessibility Compliance Program", "Product", "Make NovaFlow and NovaDesk conform to WCAG 2.2 AA."),
    ("NovaTech Foundation Digital Skills 2026", "Human Resources", "Teach digital skills to 5,000 students in partner colleges."),
    ("Green Campus Initiative", "Operations", "Move the Hyderabad campus to 100% renewable electricity."),
    ("Customer Community Portal", "Customer Success", "Launch an online community for NovaTech customers."),
    ("NovaTech Developer Conference 2026", "Marketing", "Host the annual developer and customer conference in Hyderabad."),
    ("Status Page Transparency Program", "Engineering", "Publish real-time service status and incident history."),
    ("Responsible AI Principles", "Legal", "Publish and operationalise NovaTech's Responsible AI Principles."),
    ("Chennai Hub Community Hiring", "Human Resources", "Hire and train 120 graduates from Tamil Nadu colleges."),
]

OBJECTIVES = {
    "Engineering": ["reduce p95 latency by 40% and remove single points of failure",
                    "move remaining VM workloads to Kubernetes and cut infrastructure cost by 20%",
                    "ship a secure, well-documented API for enterprise customers",
                    "improve reliability to 99.95% availability across regions",
                    "replace legacy components with a maintainable, tested service",
                    "enable real-time data for analytics and AI features"],
    "Product": ["increase feature adoption among mid-market customers", "simplify onboarding and reduce time-to-value",
                "define the next four quarters of roadmap priorities with customer evidence"],
    "Information Technology": ["strengthen endpoint security and reduce support tickets",
                               "modernise corporate IT with automation and self-service",
                               "improve identity governance and quarterly access reviews"],
    "Human Resources": ["improve the employee experience and reduce time-to-productivity",
                        "automate HR operations and payroll accuracy", "strengthen hiring quality and diversity"],
    "Finance": ["shorten the month-end close from 8 to 5 working days", "strengthen financial controls and audit readiness",
                "automate payables and improve forecast accuracy"],
    "Sales": ["grow qualified pipeline in priority segments", "improve win rates with better enablement",
              "expand into new regions with a partner-led motion"],
    "Marketing": ["generate qualified demand for the Nova AI Suite", "strengthen brand awareness in target markets",
                  "turn happy customers into public advocates"],
    "Legal": ["reduce contract turnaround time and legal risk", "achieve compliance with new data-protection rules",
              "standardise policies and approvals across the company"],
    "Operations": ["reduce facility and vendor costs while improving service", "streamline procurement approvals",
                   "improve delivery predictability for customer projects"],
    "Customer Success": ["raise net revenue retention above 115%", "reduce escalations and time-to-resolution",
                         "help customers adopt new features faster"],
    "Executive": ["evaluate strategic options for long-term growth", "prepare governance changes for the Board"],
}

MILESTONE_BANK = ["Discovery & requirements", "Architecture sign-off", "Vendor selection", "MVP build",
                  "Pilot with two teams", "Security review", "User acceptance testing", "Data migration", "Go-live",
                  "Hypercare & handover", "Training rollout", "Phase 2 scope approval"]

RISK_BANK = {
    "Engineering": [("Dependency on the legacy billing API may delay integration testing", "Build a contract-test harness and agree a freeze window with the billing team"),
                    ("Key senior engineer allocated to two projects", "Backfill with a contractor and pair a second engineer on critical modules"),
                    ("Performance targets not yet validated at production scale", "Run load tests at 2x peak before go-live"),
                    ("Kubernetes storage driver instability during cut-over", "Keep a rollback path and run a rehearsal in staging"),
                    ("Third-party API rate limits could throttle data sync", "Negotiate higher limits and add a queue with back-off"),
                    ("Security review findings may require design changes", "Engage Security Operations early and fix High findings first"),
                    ("Cloud cost overrun during dual-running period", "Set budget alerts and decommission old stack within 30 days")],
    "Product": [("Customer research sample too small for pricing decisions", "Extend interviews to 20 customers across segments"),
                ("Competing roadmap priorities across product lines", "Use the quarterly prioritisation council"),
                ("Design resources shared with three initiatives", "Stagger design sprints")],
    "Information Technology": [("Laptop supply delays from vendor", "Order with two vendors and keep a buffer of 5% spare devices"),
                               ("User disruption during rollout", "Roll out by department with communications and floor-walkers"),
                               ("Legacy applications incompatible with new policy", "Run a compatibility pilot and keep exceptions time-bound")],
    "Human Resources": [("Low adoption of the new portal by managers", "Run manager training and nudges"),
                        ("Payroll data migration errors", "Parallel-run two payroll cycles"),
                        ("Tight hiring market for senior roles", "Increase referral bonus and widen locations")],
    "Finance": [("ERP customisation effort underestimated", "Limit scope to standard processes in phase 1"),
                ("Audit timelines overlap with close", "Pre-agree evidence requests with auditors"),
                ("Data quality in legacy ledgers", "Run reconciliation sprints before migration")],
    "Sales": [("Pipeline concentration in a few large deals", "Broaden mid-market prospecting"),
              ("Partner onboarding slower than planned", "Dedicated partner manager for top 10 partners"),
              ("Longer procurement cycles at enterprise customers", "Engage procurement earlier with standard terms")],
    "Marketing": [("Event dates clash with major industry conferences", "Lock venue early and adjust dates"),
                  ("Content production capacity", "Use an agency for long-form content"),
                  ("Lead quality below target", "Tighten scoring with Sales")],
    "Legal": [("Regulatory guidance still evolving", "Track guidance monthly and design for flexibility"),
              ("Business teams bypass contract templates", "Make templates available in the workspace and train teams")],
    "Operations": [("Vendor lead times for fit-out materials", "Pre-order long-lead items"),
                   ("Budget approval pending for phase 2", "Prepare phased business case"),
                   ("Facility works may disrupt teams", "Schedule works on weekends")],
    "Customer Success": [("Support volume spike after major release", "Add temporary shift coverage"),
                         ("Churn risk in two strategic accounts", "Executive sponsor calls and success plans"),
                         ("Knowledge base articles out of date", "Monthly content review with Product")],
    "Executive": [("Valuation expectations may diverge", "Use independent valuation advisors"),
                  ("Confidentiality of discussions", "Restrict data room access to named individuals")],
}

TECH_STACK = {
    "Engineering": "Python FastAPI Java Go TypeScript React PostgreSQL Kafka Redis Kubernetes AWS Terraform "
                   "OpenSearch pgvector".split(),
    "Product": "Figma Amplitude Jira Productboard Miro".split(),
    "Information Technology": "Intune Entra-ID ServiceNow Zscaler Microsoft-365 Palo-Alto Splunk".split(),
    "Human Resources": "Workday ServiceNow-HR Power-BI LinkedIn-Recruiter".split(),
    "Finance": "SAP-S/4HANA Power-BI Excel Coupa BlackLine".split(),
    "Sales": "Salesforce Gong Outreach LinkedIn-Sales-Navigator Power-BI".split(),
    "Marketing": "HubSpot WordPress Google-Analytics Canva Semrush".split(),
    "Legal": "Ironclad OneTrust SharePoint DocuSign".split(),
    "Operations": "SAP-Ariba ServiceNow Power-BI AutoCAD".split(),
    "Customer Success": "NovaDesk Gainsight Salesforce Zendesk-migration Power-BI".split(),
    "Executive": "Board-portal Power-BI".split(),
}

TASK_BANK = {
    "Engineering": ["Implement {theme} API endpoints", "Write integration tests for {theme}", "Fix flaky tests in {theme} pipeline",
                    "Review PR for {theme} data model", "Update runbook for {milestone}", "Load test {theme} at 2x peak",
                    "Set up dashboards and alerts for {theme}", "Resolve security findings from {milestone}",
                    "Document architecture decision for {theme}", "Prepare demo for {milestone}",
                    "Migrate {theme} configuration to Terraform", "Triage production bugs in {theme}"],
    "Product": ["Write PRD for {theme}", "Interview five customers about {theme}", "Prioritise backlog for {milestone}",
                "Prepare release notes for {theme}", "Review designs for {theme}", "Define success metrics for {milestone}"],
    "Information Technology": ["Pilot {theme} with one department", "Update knowledge article for {theme}",
                               "Schedule change window for {milestone}", "Validate compliance of devices for {theme}",
                               "Send user communication for {milestone}", "Close incident tickets related to {theme}"],
    "Human Resources": ["Draft communication for {theme}", "Collect manager feedback on {theme}", "Configure workflow for {milestone}",
                        "Prepare training for {theme}", "Review data migration for {milestone}"],
    "Finance": ["Reconcile ledgers for {theme}", "Prepare variance analysis for {milestone}", "Document controls for {theme}",
                "Validate vendor master data for {theme}", "Prepare audit evidence for {milestone}"],
    "Sales": ["Update account plans for {theme}", "Prepare QBR deck for {milestone}", "Qualify new leads for {theme}",
              "Review pricing proposal for {theme}", "Log call notes in CRM for {milestone}"],
    "Marketing": ["Draft campaign brief for {theme}", "Publish blog post for {theme}", "Coordinate speakers for {milestone}",
                  "Review landing page for {theme}", "Report campaign metrics for {milestone}"],
    "Legal": ["Review contract templates for {theme}", "Update policy draft for {milestone}", "Assess regulatory impact of {theme}",
              "Prepare training note on {theme}"],
    "Operations": ["Collect vendor quotes for {theme}", "Update delivery plan for {milestone}", "Inspect site progress for {theme}",
                   "Raise purchase request for {theme}", "Review SLA report for {milestone}"],
    "Customer Success": ["Run onboarding session for {theme}", "Update success plans for {milestone}", "Review escalations in {theme}",
                         "Refresh help-centre articles for {theme}", "Prepare renewal forecast for {milestone}"],
    "Executive": ["Review board pack for {theme}", "Prepare briefing for {milestone}"],
}

SOFTWARE = [  # name, category, vendor, licence, approval_required, platforms, description
    ("Microsoft 365", "Productivity", "Microsoft", "Enterprise agreement", False, ["Windows", "macOS", "Web"], "Outlook, Teams, Word, Excel, PowerPoint and OneDrive."),
    ("Slack", "Collaboration", "Salesforce", "Enterprise Grid", False, ["Windows", "macOS", "Web", "Mobile"], "Team messaging for projects and communities."),
    ("Zoom", "Collaboration", "Zoom", "Business", False, ["Windows", "macOS", "Mobile"], "Video meetings with external participants."),
    ("Google Chrome", "Browser", "Google", "Free", False, ["Windows", "macOS"], "Standard managed browser."),
    ("1Password", "Security", "1Password", "Business", False, ["Windows", "macOS", "Mobile"], "Company password manager."),
    ("Adobe Acrobat Reader", "Productivity", "Adobe", "Free", False, ["Windows", "macOS"], "View and sign PDF documents."),
    ("Zscaler Client Connector", "Security", "Zscaler", "Enterprise", False, ["Windows", "macOS"], "Secure internet access and zero-trust networking."),
    ("NovaSecure VPN", "Network", "NovaTech IT", "Internal", False, ["Windows", "macOS"], "Always-on VPN for internal systems."),
    ("Jira", "Work management", "Atlassian", "Cloud Premium", False, ["Web"], "Issue and project tracking."),
    ("Confluence", "Knowledge", "Atlassian", "Cloud Premium", False, ["Web"], "Team documentation and wikis."),
    ("Visual Studio Code", "Developer tools", "Microsoft", "Free", False, ["Windows", "macOS", "Linux"], "Code editor for engineers."),
    ("JetBrains IntelliJ IDEA", "Developer tools", "JetBrains", "Named licence", True, ["Windows", "macOS", "Linux"], "Java/Kotlin IDE."),
    ("JetBrains PyCharm", "Developer tools", "JetBrains", "Named licence", True, ["Windows", "macOS", "Linux"], "Python IDE."),
    ("Docker Desktop", "Developer tools", "Docker", "Business", False, ["Windows", "macOS"], "Local containers for development."),
    ("Postman", "Developer tools", "Postman", "Enterprise", False, ["Windows", "macOS", "Web"], "API testing and collections."),
    ("Git", "Developer tools", "Open source", "Free", False, ["Windows", "macOS", "Linux"], "Version control client."),
    ("GitHub Enterprise", "Developer tools", "GitHub", "Enterprise", False, ["Web"], "Source control and CI."),
    ("AWS CLI", "Cloud", "Amazon Web Services", "Free", False, ["Windows", "macOS", "Linux"], "Command-line access to AWS accounts you are authorised for."),
    ("Terraform", "Cloud", "HashiCorp", "Free", False, ["Windows", "macOS", "Linux"], "Infrastructure as code."),
    ("DBeaver", "Data tools", "DBeaver", "Community", True, ["Windows", "macOS"], "Database client — production access needs Security approval."),
    ("Figma", "Design", "Figma", "Organization", True, ["Web", "macOS", "Windows"], "Product and UI design."),
    ("Adobe Creative Cloud", "Design", "Adobe", "Named licence", True, ["Windows", "macOS"], "Photoshop, Illustrator, InDesign, Premiere."),
    ("Canva", "Design", "Canva", "Teams", True, ["Web"], "Quick marketing graphics."),
    ("Tableau", "Analytics", "Salesforce", "Creator", True, ["Windows", "macOS"], "Visual analytics."),
    ("Power BI", "Analytics", "Microsoft", "Pro", True, ["Windows", "Web"], "Dashboards and reporting."),
    ("Miro", "Collaboration", "Miro", "Business", True, ["Web"], "Online whiteboard."),
    ("Grammarly Business", "Productivity", "Grammarly", "Business", True, ["Web", "Windows", "macOS"], "Writing assistant."),
    ("Salesforce Sales Cloud", "CRM", "Salesforce", "Enterprise", True, ["Web"], "CRM for Sales and Customer Success."),
    ("HubSpot Marketing Hub", "Marketing", "HubSpot", "Professional", True, ["Web"], "Marketing automation."),
    ("Workday", "HR", "Workday", "Enterprise", False, ["Web"], "HR portal: profile, leave, payslips, reviews."),
    ("SAP S/4HANA", "Finance", "SAP", "Enterprise", True, ["Web"], "Finance ERP."),
    ("SAP Ariba", "Procurement", "SAP", "Enterprise", True, ["Web"], "Procurement and supplier portal."),
    ("ServiceNow", "ITSM", "ServiceNow", "Enterprise", False, ["Web"], "IT service portal and tickets."),
    ("DocuSign", "Legal", "DocuSign", "Business Pro", True, ["Web"], "Electronic signatures."),
    ("Ironclad", "Legal", "Ironclad", "Enterprise", True, ["Web"], "Contract lifecycle management."),
    ("Gainsight", "Customer Success", "Gainsight", "Enterprise", True, ["Web"], "Customer health scoring."),
    ("Gong", "Sales", "Gong", "Enterprise", True, ["Web"], "Conversation intelligence."),
    ("Splunk", "Security", "Splunk", "Enterprise", True, ["Web"], "SIEM and log search — Security Operations only."),
    ("Wireshark", "Network", "Open source", "Free", True, ["Windows", "macOS"], "Packet capture — requires Security approval."),
    ("Python 3.12", "Developer tools", "Open source", "Free", False, ["Windows", "macOS", "Linux"], "Python runtime."),
    ("Node.js LTS", "Developer tools", "Open source", "Free", False, ["Windows", "macOS", "Linux"], "JavaScript runtime."),
    ("Microsoft Visio", "Productivity", "Microsoft", "Plan 2", True, ["Windows", "Web"], "Diagrams."),
    ("Snagit", "Productivity", "TechSmith", "Named licence", True, ["Windows", "macOS"], "Screen capture."),
    ("Loom", "Collaboration", "Atlassian", "Business", True, ["Web", "macOS", "Windows"], "Async video."),
    ("Kubernetes Lens", "Developer tools", "Mirantis", "Free", False, ["Windows", "macOS", "Linux"], "Kubernetes IDE."),
    ("Datadog", "Observability", "Datadog", "Enterprise", True, ["Web"], "Monitoring for production services."),
]

IT_ISSUES = [  # issue text, category, priority, steps
    ("won't start or crashes on launch", "Software", "P3",
     ["Restart your laptop and try again.", "Check for pending updates in the Company Portal and install them.",
      "Clear the application cache (Settings > Reset) and sign in again.",
      "Reinstall {sw} from the Company Portal — never from the internet."]),
    ("sign-in or SSO loop", "Access", "P2",
     ["Close all browser windows and sign in again in a private window.", "Confirm the MFA prompt on your authenticator app.",
      "Check that your device date and time are set automatically.", "If you recently changed your password, sign out of all {sw} sessions."]),
    ("is very slow", "Software", "P3",
     ["Close unused tabs and applications.", "Connect to the office network or check your home bandwidth.",
      "Disable unapproved browser extensions.", "Update {sw} to the latest approved version."]),
    ("licence or access request", "Access", "P4",
     ["Check the Standard Software Catalog to see whether {sw} needs approval.", "Ask the AI assistant to create a software request with a business justification.",
      "Your manager approves paid licences; Security approves sensitive tools.", "The licence is assigned within 1 business day after approval."]),
    ("sync or data not updating", "Software", "P3",
     ["Check the service status page for {sw}.", "Sign out and sign back in.", "Ensure the client is not paused and has enough disk space.",
      "Raise a P3 ticket with screenshots if the problem continues."]),
    ("error after latest update", "Software", "P3",
     ["Note the exact error message and time.", "Restart {sw} and your laptop.", "Roll back is not self-service — raise a ticket so IT can pin the previous version."]),
]

DEVICE_TOPICS = [
    ("Laptop battery drains quickly", "Hardware", ["Check battery health in the vendor utility.", "Lower screen brightness and close heavy apps.", "If health is below 70%, raise a Hardware ticket for a battery replacement."]),
    ("External monitor not detected", "Hardware", ["Reconnect the cable and try another port.", "Update display drivers via the Company Portal.", "Test with a different cable at the IT desk."]),
    ("Wi-Fi keeps disconnecting in the office", "Network", ["Forget and rejoin the NovaCorp network.", "Make sure you are not on NovaGuest.", "Raise a Network ticket with your floor and desk number."]),
    ("Printer not found", "Hardware", ["Connect to the office network.", "Add the printer from the Company Portal printers list.", "Use secure print release with your badge."]),
    ("Keyboard or trackpad not working", "Hardware", ["Restart the laptop.", "Check for liquid damage — do not power on if wet.", "Raise a P2 Hardware ticket for a loaner."]),
    ("Disk almost full", "Hardware", ["Empty the Downloads folder and recycle bin.", "Move files to OneDrive.", "IT can expand storage only for engineering build machines."]),
    ("Lost or stolen laptop", "Hardware", ["Report to the Service Desk within 2 hours.", "IT remotely locks and wipes the device.", "File a police report if stolen and share the reference."]),
    ("Mobile email setup", "Access", ["Install Outlook from the app store.", "Enrol the phone in Intune when prompted.", "Approve MFA."]),
]

HR_TOPICS = [
    ("Parental leave", "Maternity leave is 26 weeks and paternity leave 4 weeks. Adoption leave is 12 weeks. Apply at least 8 weeks before the expected date and upload supporting documents to the HR portal."),
    ("Compensatory off", "Employees who work on a public holiday or weekend at the manager's request earn one compensatory off, to be used within 60 days."),
    ("Internal job posting (IJP)", "Employees with 12+ months in role and a Meets or better rating can apply for internal roles. Inform your manager before applying; the hiring manager interviews within 2 weeks."),
    ("Employee referral programme", "Refer candidates through the referral portal. Bonuses are paid after the new hire completes 90 days: ₹75,000 for engineering, ₹40,000 for other roles."),
    ("Probation and confirmation", "New employees are on probation for 6 months. Confirmation is based on manager feedback; probation can be extended once by 3 months."),
    ("Exit process and full-and-final settlement", "Submit resignation in the HR portal. Complete handover and asset return. Full-and-final settlement is paid within 45 days of the last working day."),
    ("Relocation support", "Employees relocating at the company's request receive travel, 14 days of temporary accommodation and a one-time relocation allowance."),
    ("Salary advance", "Employees may request an interest-free salary advance of up to one month's net pay once per year for emergencies, recovered over 6 months."),
    ("Shift allowance", "Employees on night shifts (21:00–06:00) receive a shift allowance of ₹400 per night, paid with the next month's salary."),
    ("Work anniversary and long-service awards", "Long-service awards are presented at 5, 10 and 15 years with an additional 2 days of earned leave."),
    ("Employee assistance programme", "Free and confidential counselling for employees and dependants, available 24x7 by phone or video."),
    ("Mandatory training", "All employees complete Code of Conduct, POSH and Security Awareness training every year."),
    ("Holiday exchange", "Employees may swap up to two optional holidays per year for regional festivals from the optional holiday list."),
    ("Business attire and dress code", "Dress is business casual; customer-facing meetings may require formal attire."),
    ("Workplace harassment (POSH)", "NovaTech has zero tolerance for harassment. Complaints can be raised with the Internal Committee; all complaints are handled confidentially."),
    ("Bereavement leave", "Up to 5 days of paid bereavement leave for immediate family members."),
    ("Sabbatical", "Employees with 5+ years of service may request an unpaid sabbatical of up to 6 months with department-head approval."),
    ("Flexible working hours", "Within core hours of 11:00–16:00 IST, employees may choose their start time between 08:00 and 11:00."),
    ("Performance improvement plan", "A PIP lasts 60 days with clear goals and bi-weekly check-ins with the manager and HR business partner."),
    ("Health insurance claims", "Cashless claims at network hospitals through the insurer app; reimbursement claims within 30 days of discharge."),
]

FINANCE_TOPICS = [
    ("Corporate card usage", "Corporate cards are issued to employees who travel more than 4 times a year. Only business expenses; reconcile within 7 days of the statement."),
    ("Month-end close checklist", "Accruals by working day 2, reconciliations by day 4, management reports by day 7."),
    ("Petty cash", "Each office has a petty cash float of ₹20,000 for small purchases below ₹2,000, held by the office administrator."),
    ("GST invoice requirements", "Invoices must show NovaTech's GSTIN for the correct state, HSN/SAC code and tax breakup. Invoices without GSTIN cannot be claimed."),
    ("Foreign currency expenses", "Expenses in foreign currency are reimbursed at the card conversion rate or the RBI reference rate on the expense date."),
    ("Per diem rates", "Domestic per diem is ₹1,500 per day; Singapore SGD 80; London GBP 60."),
    ("Capital expenditure approval", "Assets above ₹1 lakh with a life over 1 year are capitalised; capex requests need Finance Manager approval."),
    ("Budget re-allocation", "Moving budget between categories within a cost centre up to ₹10 lakh needs the budget owner; above that needs Finance Manager approval."),
    ("Client entertainment", "Client meals up to ₹3,000 per person need manager approval; attendee names must be recorded."),
    ("Mileage reimbursement", "Business use of a personal car is reimbursed at ₹12 per km and two-wheelers at ₹6 per km."),
]

PROCUREMENT_TOPICS = [
    ("Preferred vendors", "Use preferred vendors in the vendor catalogue first; they have negotiated rates and completed due diligence."),
    ("New vendor onboarding", "New vendors submit KYC, bank details, GST registration and a security questionnaire. Onboarding takes about 10 business days."),
    ("Purchase order changes", "Changes to value or scope after a PO is issued need a PO amendment approved at the same level as the original."),
    ("Emergency purchases", "Emergency purchases for business continuity may proceed with department-head approval by email; the PR must be raised within 2 business days."),
    ("Software purchases", "All software and SaaS purchases require IT Security review and must be added to the Standard Software Catalog."),
    ("Hardware purchases", "Laptops, monitors and peripherals are purchased centrally by IT; departments should not buy hardware directly."),
    ("Consulting and professional services", "Consulting engagements need a statement of work with deliverables, rates and a Legal-reviewed contract."),
    ("Goods receipt", "Requesters must confirm goods receipt in the procurement portal within 5 days of delivery so invoices can be paid."),
]

LEGAL_TOPICS = [
    ("NDA", "Use the NovaTech mutual NDA template for early discussions. Non-standard NDAs need Legal review."),
    ("Master Services Agreement", "Customer MSAs follow the standard template; liability caps below 12 months' fees need Legal approval."),
    ("Data Processing Agreement", "A DPA is mandatory whenever a vendor processes personal data on our behalf."),
    ("Statement of Work", "SOWs must reference the governing MSA and list deliverables, milestones and acceptance criteria."),
    ("Reseller agreement", "Partner and reseller agreements need Legal and Finance review of margins and territories."),
    ("Open-source licences", "Engineers must check new open-source dependencies against the approved licence list; copyleft licences need Legal review."),
    ("Anti-bribery", "Never offer or accept anything of value to influence a business decision. Gifts above ₹5,000 must be reported."),
    ("Export controls", "Certain encryption features may be subject to export controls; check with Legal before selling to new countries."),
    ("Cross-border data transfers", "Personal data may leave India only to approved processors with contractual safeguards."),
    ("Conflict of interest", "Disclose outside employment, board roles or investments in vendors or competitors to Legal within 7 days."),
]

SECURITY_TOPICS = [
    ("Phishing", "Phishing emails create urgency and ask you to click, pay or share credentials. Use the Report Phishing button; never forward suspicious emails to colleagues."),
    ("QR-code phishing", "Treat QR codes in emails and posters as links. Do not scan codes asking you to sign in."),
    ("Voice phishing (vishing)", "IT will never call you to ask for your password or MFA code. Hang up and call the Service Desk on the published number."),
    ("USB devices", "Do not plug in unknown USB drives. Company laptops block removable storage by default."),
    ("Tailgating", "Do not hold doors for people without a badge; escort visitors at all times."),
    ("Clean desk", "Lock away printed Confidential documents and lock your screen when you leave your desk."),
    ("Working in public places", "Use a privacy screen, avoid calls about Confidential topics and always use the VPN on public Wi-Fi."),
    ("MFA fatigue attacks", "If you receive MFA prompts you did not start, deny them and report to Security Operations immediately."),
    ("Secure file sharing", "Share files through OneDrive with named people; do not use personal email or public links for Confidential data."),
    ("Using AI tools safely", "Use the NovaTech Solutions assistant for company data. Never paste Confidential data into public AI tools."),
    ("Reporting a security incident", "Email security@novatech.demo or call extension 4357. Report within 1 hour — speed matters more than certainty."),
    ("Travel security", "Carry only the data you need, keep devices with you and report device inspections at borders to Security."),
]

SALES_INDUSTRIES = ["Banking", "Insurance", "Retail", "Manufacturing", "Healthcare", "Logistics", "Telecom",
                    "Education", "Government", "Energy", "Media", "Hospitality", "Pharma", "Real Estate", "Fintech"]
REGIONS = ["India South", "India West", "India North", "Singapore", "United Kingdom"]
CUSTOMER_PREFIX = """Arcadia Bluepeak Crestline Deltaview Evergreen Fairway Granite Harbourline Ironbridge Jadestone Keystone
Lighthouse Meridian Northwind Oakridge Pinnacle Quantix Riverstone Sapphire Tidewater Unison Vantage Westbrook Zenova
Amberly Brightpath Cloudpeak Driftwood Everest Fulcrum Goldleaf Horizonte Indigo Juniper Kestrel Lumina Monarch
Nexora Orchid Pacifica Redwood Silverline Trident Upland Verdant Willow Yellowfin Zircon""".split()
CUSTOMER_SUFFIX = ["Retail Group", "Logistics", "Bank", "Insurance", "Manufacturing", "Healthcare", "Telecom",
                   "Industries", "Pharma", "Foods", "Energy", "Capital", "Motors", "Hotels", "Media", "Systems",
                   "Finance", "Textiles", "Realty", "Airways"]
VENDOR_CATEGORIES = ["Cloud & Hosting", "Software", "Hardware", "Facilities", "Consulting", "Training", "Travel",
                     "Marketing Services", "Security Services", "Staffing", "Legal Services", "Office Supplies"]
VENDOR_WORDS = """Apex Brightstar Cobalt Datawave Elevate Fortis Globex Helix Infinite Jupiter Kinetic Lattice Matrix
Nimbus Optima Prism Quantum Radius Summit Tensor Ultra Vector Wavelength Xenon Yotta Zeta Aster Bolt Crux Dyna""".split()
VENDOR_TAILS = ["Technologies", "Solutions", "Services", "Systems", "Consulting", "Infra", "Supplies", "Networks",
                "Labs", "Partners"]

PRODUCTS = [
    ("PRD-NFLOW", "NovaFlow", "Workflow automation", "Visual workflow automation with approvals, SLAs and 200+ connectors.", 1_800_000),
    ("PRD-NDESK", "NovaDesk", "Customer service", "Omnichannel ticketing, knowledge base and customer portal.", 1_500_000),
    ("PRD-NAI", "Nova AI Suite", "AI", "Permission-aware enterprise search, agentic service desk and AI approvals.", 2_400_000),
    ("PRD-NINS", "NovaInsight", "Analytics", "Operational analytics dashboards and KPI tracking.", 900_000),
    ("PRD-NCON", "NovaConnect", "Integration", "Integration platform and API management.", 1_100_000),
    ("PRD-PSVC", "Implementation Services", "Services", "Implementation, migration and training services.", 600_000),
    ("PRD-PREM", "Premium Support", "Services", "24x7 premium support with a named support engineer.", 450_000),
    ("PRD-NMOB", "NovaFlow Mobile", "Workflow automation", "Mobile approvals and field workflows.", 350_000),
]

ANNOUNCEMENT_TEMPLATES = [
    ("Town hall recap — {month}", "INTERNAL", "Human Resources",
     "Highlights from the {month} town hall: the CEO shared progress on company priorities, the Nova AI Suite adoption numbers and upcoming hiring. Recording available on the intranet for 30 days."),
    ("Product release: NovaFlow {ver}", "PUBLIC", "Product",
     "NovaFlow {ver} is now available with faster form rendering, new approval templates and improved audit exports. Customers on the cloud edition are upgraded automatically."),
    ("Product release: NovaDesk {ver}", "PUBLIC", "Product",
     "NovaDesk {ver} introduces AI-suggested replies, SLA heatmaps and a redesigned customer portal."),
    ("Office update: {city}", "INTERNAL", "Operations",
     "Facilities update for {city}: the cafeteria menu has been refreshed, two new focus rooms are open on level 3 and parking allocation changes from next month."),
    ("IT maintenance window — {month}", "INTERNAL", "Information Technology",
     "Planned maintenance on {month} weekend: email, VPN and the HR portal may be unavailable for up to 2 hours on Saturday night. No action needed."),
    ("Security reminder — {topic}", "INTERNAL", "Information Technology",
     "This month's security reminder is about {topic}. Report anything suspicious using the Report Phishing button or to security@novatech.demo."),
    ("NovaTech recognised as a Great Place to Work {year}", "PUBLIC", "Human Resources",
     "NovaTech Solutions has been certified as a Great Place to Work for {year}, reflecting employee feedback on trust, learning and flexibility."),
    ("Welcome to our new joiners — {month}", "INTERNAL", "Human Resources",
     "Please welcome the {n} colleagues who joined NovaTech in {month} across Engineering, Customer Success and Sales. Say hello at the next team social."),
    ("Customer milestone: {n} customers on Nova AI Suite", "PUBLIC", "Marketing",
     "More than {n} customers now use the Nova AI Suite in production, with an average 30% reduction in ticket handling time."),
    ("Benefits enrolment window open — {month}", "INTERNAL", "Human Resources",
     "The annual benefits enrolment window is open until the end of {month}. Review health insurance top-ups and add parents if needed."),
]

DEPT_PROCESSES = {
    "Engineering": ["Release management process", "On-call rotation and paging guide", "Code review checklist",
                    "Incident postmortem template", "Feature flag guidelines", "Database change process",
                    "API versioning standard", "Secure coding checklist", "Performance testing guide",
                    "Observability standards"],
    "Product": ["Product requirements template", "Roadmap prioritisation process", "Release notes guidelines",
                "Customer interview guide", "Beta programme process"],
    "Information Technology": ["New starter IT setup", "Leaver deprovisioning checklist", "Change management process",
                               "Patch management schedule", "Backup and restore procedure", "Asset tagging procedure"],
    "Human Resources": ["Offer approval workflow", "Background verification process", "Leave approval guidelines for managers",
                        "Payroll input deadlines", "Exit interview process"],
    "Finance": ["Accounts payable workflow", "Revenue recognition checklist", "Quarterly forecast process",
                "Vendor payment run process", "Expense audit sampling"],
    "Sales": ["Opportunity stage definitions", "Discount approval process", "Quote-to-cash process",
              "Territory rules of engagement", "Partner deal registration"],
    "Marketing": ["Campaign launch checklist", "Brand approval process", "Event planning checklist",
                  "Lead handover process"],
    "Legal": ["Contract request intake", "Legal hold procedure", "Policy review cycle", "Trademark usage guidelines"],
    "Operations": ["Facility request process", "Travel booking process", "Meeting room booking rules",
                   "Vendor performance review", "Delivery governance process"],
    "Customer Success": ["Customer onboarding playbook", "Health score definitions", "Renewal process",
                         "Support severity definitions", "Knowledge article standards"],
}
