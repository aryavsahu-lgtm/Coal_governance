# CoalGov-AI: Smart Governance & Compliance Monitoring Platform for Indian Coal Mines

An enterprise-grade digital governance, statutory compliance, and AI-assisted safety monitoring platform engineered for Indian coal mining subsidiaries (Coal India Limited, ECL, BCCL, etc.) under the regulatory framework of the **Directorate General of Mines Safety (DGMS)**, the **Mines Act 1952**, and the **Coal Mines Regulations (CMR) 2017**.

---

## 1. Project Overview & Workflow

CoalGov-AI centralizes multi-subsidiary and multi-mine operations into a unified closed-loop governance workflow:

$$\text{Field Activity / Sensor / CCTV} \longrightarrow \text{Data Collection} \longrightarrow \text{AI Vision / Rule Analysis} \longrightarrow \text{Statutory Violation} \longrightarrow \text{Automated Assignment} \longrightarrow \text{CAPA Remediation} \longrightarrow \text{Authorized Verification} \longrightarrow \text{Closed} \longrightarrow \text{Immutable Audit \& Analytics}$$

---

## 2. Key Features

- **8 Granular RBAC Role Interfaces:**
  1. *Super Admin*: Global system settings, user management, audit trails, and health diagnostics.
  2. *Corporate Management*: Executive overview across subsidiaries, cross-mine risk analytics, and performance benchmarks.
  3. *Mine Officer (Agent/GM)*: Mine-level operational control, CAPA tracking, and zone oversight.
  4. *Safety Officer*: PPE violations, hazard zone alerts, incident investigations, and CAPA verification.
  5. *Inspection Officer*: Scheduled surprise inspections, checklist submission, and multimedia logging.
  6. *Environmental Officer*: MoEFCC / SPCB clearance compliance, emissions, and ETP monitoring.
  7. *Contractor*: Worker counts, statutory permit renewals, and remediation proof submissions.
  8. *Regulatory Authority (DGMS)*: Statutory audits, inspection history, non-compliance review, and closure oversight.
- **AI Visual Violation Studio (YOLOv8 + OpenCV):** Real-time automated detection of personnel, mandatory helmets, high-vis vests, and restricted hazard zone boundary breaches with OpenCV visual bounding boxes.
- **Deterministic Rule Engine & Multi-Tier Escalation:** Configurable business rule evaluator with automated 4-tier escalation (Reminder $\rightarrow$ Safety Officer $\rightarrow$ Mine Manager $\rightarrow$ Corporate Board).
- **Statutory Document Vault & OCR:** Automated PDF and scanned image text extraction, certificate number parsing, and 30-day expiration alerts.
- **Explainable Risk Scoring:** Transparent 0–100 safety risk scores with explicit contributing factors (e.g., 8 recent safety violations, 3 repeat PPE violations, 4 overdue CAPA actions).
- **Operational Anomaly Detection:** Scikit-Learn Isolation Forest and Z-Score statistics flagging unusual drops in output or absenteeism with non-defamatory investigation guidance.
- **Mobile-Friendly Field Reporting:** Responsive mobile intake with device GPS auto-capture and local offline queue with auto-sync when online.
- **GIS Spatial Hazard Mapping:** Leaflet.js map with layers for mines, hazard zones, violations, incidents, and field reports.
- **Regulatory RAG Knowledge Assistant:** Grounded retrieval-augmented chatbot citing specific CMR 2017 and Mines Act 1952 regulations with zero hallucination.
- **Automated Report Generation:** 1-click downloadable governance summaries in PDF and CSV.

---

## 3. Technology Stack

- **Backend:** Python 3.12 / 3.14, Flask, Flask-CORS, PyJWT, Bcrypt, PyMongo, Pydantic, ReportLab.
- **Database:** MongoDB (Atlas & Local connection resilience with singleton pooling and graceful fallback).
- **AI & Computer Vision:** Ultralytics YOLOv8, OpenCV (cv2), Scikit-Learn, PyPDF, Tesseract/EasyOCR fallback.
- **Frontend:** HTML5, CSS3, Bootstrap 5, Bootstrap Icons, Leaflet.js, Chart.js.

---

## 4. Folder Structure

```
coal_governance/
├── app/
│   ├── __init__.py                 # Flask App Factory & Blueprints
│   ├── config.py                   # Centralized Configuration (.env)
│   ├── auth/                       # JWT Authentication & RBAC Decorators
│   ├── database/                   # MongoDB Singleton, Indexes & Seed Data
│   ├── subsidiaries/               # Corporate Subsidiaries (ECL, BCCL)
│   ├── mines/                      # Mines & Hazard Zones CRUD
│   ├── compliance/                 # Statutory Compliance (CMR 2017)
│   ├── inspections/                # Inspection Lifecycle State Machine
│   ├── field_reports/              # Mobile Field Observation Intake
│   ├── violations/                 # Violation Lifecycle & CAPA Dispatch
│   ├── corrective_actions/         # CAPA Submission & Verification
│   ├── incidents/                  # Incident Reporting & Root Cause Analysis
│   ├── contractors/                # Contractor Registry & Explainable Risk
│   ├── documents/                  # Document Vault & Expiry Detection
│   ├── storage/                    # StorageService Interface (Local / S3)
│   ├── ai/                         # YOLOv8, OpenCV, OCR & Risk Engines
│   ├── workflow/                   # Rule Engine & Multi-Tier Escalation
│   ├── rag/                        # Statutory Regulations Knowledge Chatbot
│   ├── gis/                        # Leaflet.js GeoJSON Feeds
│   ├── analytics/                  # Executive Metrics & Anomaly Detection
│   ├── notifications/              # In-App Notification Center
│   ├── audit/                      # Append-Only Audit Trail Logger
│   ├── reports/                    # Downloadable PDF & CSV Generators
│   ├── utils/                      # Standard JSON Envelopes & Validators
│   └── views.py                    # Web UI Routing
├── frontend/
│   ├── templates/                  # Bootstrap 5 Jinja2 Templates
│   └── static/                     # CSS & Modular JS
├── uploads/                        # Evidence Photos, Videos & Certificates
├── models/                         # YOLO Weights Repository (yolov8n.pt)
├── tests/                          # Automated Integration & Workflow Tests
├── scripts/                        # Database Seeding Script (seed_db.py)
├── requirements.txt
├── .env.example
├── README.md
└── run.py                          # Server Launcher
```

---

## 5. Quick Start & Installation

### 1. Prerequisites
- Python 3.12+ installed.
- (Optional) MongoDB Atlas URI or local MongoDB instance running on `localhost:27017`.

### 2. Setup Environment & Dependencies
```bash
cd coal_governance
python -m venv venv
# On Windows:
venv\Scripts\activate

# Install pinned dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
Update your `MONGODB_URI` in `.env`:
```env
MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.lxjbus5.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=coal_governance
JWT_SECRET=coal_gov_super_secret_jwt_key_dgms_compliance_2026_x89a1
```

*(Note: The application has built-in startup resilience. If the MongoDB URI is invalid or unreachable, it starts cleanly in local fallback mode so you can test features immediately.)*

### 4. Seed Database with Realistic Demo Data
Run the seeding script to initialize all 8 role accounts, subsidiaries, mines, zones, compliance checklists, and sample violations:
```bash
python scripts/seed_db.py
```

### 5. Launch the Server
```bash
python run.py
```
Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## 6. Pre-Configured Demo Credentials

Use these 1-click accounts on the login screen (`/login`):

| Role | Email | Password |
|---|---|---|
| **Super Admin** | `admin@coalgov.in` | `Admin@1234` |
| **Corporate Management** | `corporate@coalgov.in` | `Corp@1234` |
| **Mine Officer (GM)** | `mine.officer@coalgov.in` | `Mine@1234` |
| **Safety Officer** | `safety.officer@coalgov.in` | `Safety@1234` |
| **Statutory Inspector** | `inspector@coalgov.in` | `Inspect@1234` |
| **Environmental Officer** | `env.officer@coalgov.in` | `Env@1234` |
| **Contractor** | `contractor@abcexcavators.com` | `Contractor@1234` |
| **Regulatory Authority (DGMS)** | `dgms.inspector@gov.in` | `Dgms@1234` |

---

## 7. Running Automated Tests

Run the complete test suite including the 20-step primary acceptance scenario:
```bash
python -m unittest discover -s tests -p "test_*.py"
```

---

## 8. REST API Documentation Summary

| Method | Endpoint | Description | Access |
|---|---|---|---|
| `POST` | `/api/auth/login` | JWT Authentication | Public |
| `GET` | `/api/mines` | List all mines | Authenticated |
| `POST` | `/api/inspections` | Schedule statutory inspection | Safety / Admin |
| `POST` | `/api/inspections/<id>/start` | Mark inspection in progress | Inspector / Safety |
| `POST` | `/api/inspections/<id>/submit` | Submit field observations | Inspector |
| `GET` | `/api/violations` | List safety violations | Authenticated |
| `POST` | `/api/violations` | Create violation & dispatch CAPA | Safety / Admin |
| `POST` | `/api/corrective-actions/<id>/submit-evidence` | Submit remediation proof | Assigned Officer |
| `POST` | `/api/corrective-actions/<id>/verify` | Verify CAPA proof | Safety Officer / DGMS |
| `POST` | `/api/violations/<id>/close` | Close verified violation | Safety / Admin |
| `POST` | `/api/ai/image-detect` | YOLOv8 visual PPE detection | Authenticated |
| `POST` | `/api/documents/upload` | Upload document & run OCR | Authenticated |
| `GET` | `/api/gis/features` | GeoJSON layers for Leaflet | Authenticated |
| `GET` | `/api/analytics/dashboard` | Aggregated executive metrics | Authenticated |
| `POST` | `/api/chat` | RAG regulatory query assistant | Authenticated |
| `GET` | `/api/reports/download` | Export PDF / CSV governance report | Authenticated |
