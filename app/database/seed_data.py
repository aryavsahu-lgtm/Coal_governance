import datetime
import logging
from app.database.mongo import mongo
from app.auth.service import hash_password
from app.workflow.rule_engine import seed_default_rules

logger = logging.getLogger("coal_governance.seed")


def seed_database():
    """Populates database with complete realistic demonstration dataset."""
    logger.info("[Seed] Initializing database seeding...")
    now = datetime.datetime.utcnow()

    # 1. Seed Rules
    seed_default_rules()

    # 2. Seed Subsidiaries (2 subsidiaries)
    sub_ecl = {
        "name": "Eastern Coalfields Limited (ECL)",
        "code": "ECL",
        "headquarters": "Sanctoria, West Bengal",
        "contact_email": "cmd.ecl@coalindia.in",
        "contact_phone": "+91-341-2520120",
        "is_active": True,
        "is_demo": True,
        "created_at": now,
        "updated_at": now
    }
    sub_bccl = {
        "name": "Bharat Coking Coal Limited (BCCL)",
        "code": "BCCL",
        "headquarters": "Koyla Bhawan, Dhanbad, Jharkhand",
        "contact_email": "cmd.bccl@coalindia.in",
        "contact_phone": "+91-326-2230190",
        "is_active": True,
        "is_demo": True,
        "created_at": now,
        "updated_at": now
    }

    # Upsert subsidiaries
    ecl_res = mongo.subsidiaries.update_one({"code": "ECL"}, {"$set": sub_ecl}, upsert=True)
    bccl_res = mongo.subsidiaries.update_one({"code": "BCCL"}, {"$set": sub_bccl}, upsert=True)
    ecl_doc = mongo.subsidiaries.find_one({"code": "ECL"})
    bccl_doc = mongo.subsidiaries.find_one({"code": "BCCL"})
    ecl_id = str(ecl_doc["_id"])
    bccl_id = str(bccl_doc["_id"])

    # 3. Seed 4 Mines
    mines_data = [
        {
            "mine_name": "Rajmahal Open Cast Project (DEMO DATA)",
            "mine_code": "ECL-RJM-01",
            "subsidiary_id": ecl_id,
            "location": "Godda, Jharkhand",
            "latitude": 25.0485,
            "longitude": 87.3785,
            "mine_type": "OPENCAST",
            "operational_status": "ACTIVE",
            "manager": {"name": "Shri R. K. Verma", "email": "manager.rajmahal@ecl.gov.in", "phone": "+91-9431102931"},
            "contact_information": "Rajmahal Area Office, ECL",
            "is_demo": True,
            "created_at": now,
            "updated_at": now
        },
        {
            "mine_name": "Sonepur Bazari Opencast Mine (DEMO DATA)",
            "mine_code": "ECL-SPB-02",
            "subsidiary_id": ecl_id,
            "location": "Raniganj, West Bengal",
            "latitude": 23.6845,
            "longitude": 87.2144,
            "mine_type": "OPENCAST",
            "operational_status": "ACTIVE",
            "manager": {"name": "Shri A. Mukherjee", "email": "manager.sonepur@ecl.gov.in", "phone": "+91-9434018274"},
            "contact_information": "Sonepur Bazari Area, ECL",
            "is_demo": True,
            "created_at": now,
            "updated_at": now
        },
        {
            "mine_name": "Moonidih Deep Underground Project (DEMO DATA)",
            "mine_code": "BCCL-MND-01",
            "subsidiary_id": bccl_id,
            "location": "Dhanbad, Jharkhand",
            "latitude": 23.7381,
            "longitude": 86.3482,
            "mine_type": "UNDERGROUND",
            "operational_status": "ACTIVE",
            "manager": {"name": "Dr. S. K. Singh", "email": "manager.moonidih@bccl.gov.in", "phone": "+91-9431189421"},
            "contact_information": "Moonidih Colliery Office, BCCL",
            "is_demo": True,
            "created_at": now,
            "updated_at": now
        },
        {
            "mine_name": "Kusunda Open Cast Mine (DEMO DATA)",
            "mine_code": "BCCL-KSD-02",
            "subsidiary_id": bccl_id,
            "location": "Kusunda, Dhanbad, Jharkhand",
            "latitude": 23.7741,
            "longitude": 86.3985,
            "mine_type": "OPENCAST",
            "operational_status": "ACTIVE",
            "manager": {"name": "Shri P. N. Mishra", "email": "manager.kusunda@bccl.gov.in", "phone": "+91-9431320491"},
            "contact_information": "Kusunda Area VI Office, BCCL",
            "is_demo": True,
            "created_at": now,
            "updated_at": now
        }
    ]

    mine_ids = []
    for m in mines_data:
        mongo.mines.update_one({"mine_code": m["mine_code"]}, {"$set": m}, upsert=True)
        doc = mongo.mines.find_one({"mine_code": m["mine_code"]})
        mine_ids.append(str(doc["_id"]))

    primary_mine_id = mine_ids[0]
    secondary_mine_id = mine_ids[1]
    moonidih_id = mine_ids[2]
    kusunda_id = mine_ids[3]

    # 4. Seed Zones
    zones_data = [
        {
            "mine_id": primary_mine_id,
            "zone_name": "Pit 1 - Primary Coal Extraction Bench",
            "zone_code": "Z-PIT-01",
            "zone_type": "PIT",
            "risk_level": "HIGH",
            "is_restricted": False,
            "boundary_coordinates": [[25.0470, 87.3760], [25.0510, 87.3760], [25.0510, 87.3810], [25.0470, 87.3810]],
            "created_at": now,
            "updated_at": now
        },
        {
            "mine_id": primary_mine_id,
            "zone_name": "Active Blasting Hazard Perimeter",
            "zone_code": "Z-BLAST-02",
            "zone_type": "RESTRICTED",
            "risk_level": "CRITICAL",
            "is_restricted": True,
            "boundary_coordinates": [[25.0480, 87.3770], [25.0500, 87.3770], [25.0500, 87.3795], [25.0480, 87.3795]],
            "created_at": now,
            "updated_at": now
        },
        {
            "mine_id": primary_mine_id,
            "zone_name": "North Haul Road & Heavy Vehicle Transit",
            "zone_code": "Z-HAUL-03",
            "zone_type": "HAUL_ROAD",
            "risk_level": "MEDIUM",
            "is_restricted": False,
            "boundary_coordinates": [[25.0450, 87.3750], [25.0470, 87.3750], [25.0470, 87.3830], [25.0450, 87.3830]],
            "created_at": now,
            "updated_at": now
        },
        {
            "mine_id": secondary_mine_id,
            "zone_name": "Main Coal Washery & Stockpile",
            "zone_code": "Z-WSH-01",
            "zone_type": "WASHERY",
            "risk_level": "MEDIUM",
            "is_restricted": False,
            "boundary_coordinates": [[23.6820, 87.2120], [23.6860, 87.2120], [23.6860, 87.2170], [23.6820, 87.2170]],
            "created_at": now,
            "updated_at": now
        }
    ]
    for z in zones_data:
        mongo.zones.update_one({"zone_code": z["zone_code"], "mine_id": z["mine_id"]}, {"$set": z}, upsert=True)

    # 5. Seed Users for All 8 Roles
    users_data = [
        {
            "email": "admin@coalgov.in",
            "password_hash": hash_password("Admin@1234"),
            "name": "Smt. Arundhati Rao",
            "role": "SUPER_ADMIN",
            "designation": "Director General of Governance IT",
            "subsidiary_id": None,
            "mine_id": None,
            "phone": "+91-9811002233",
            "is_active": True,
            "created_at": now,
            "updated_at": now
        },
        {
            "email": "corporate@coalgov.in",
            "password_hash": hash_password("Corp@1234"),
            "name": "Shri Vikramaditya Sen",
            "role": "CORPORATE_MANAGEMENT",
            "designation": "Director (Technical), Coal India Ltd",
            "subsidiary_id": ecl_id,
            "mine_id": None,
            "phone": "+91-9833004455",
            "is_active": True,
            "created_at": now,
            "updated_at": now
        },
        {
            "email": "mine.officer@coalgov.in",
            "password_hash": hash_password("Mine@1234"),
            "name": "Shri R. K. Verma",
            "role": "MINE_OFFICER",
            "designation": "General Manager & Mine Agent",
            "subsidiary_id": ecl_id,
            "mine_id": primary_mine_id,
            "phone": "+91-9431102931",
            "is_active": True,
            "created_at": now,
            "updated_at": now
        },
        {
            "email": "safety.officer@coalgov.in",
            "password_hash": hash_password("Safety@1234"),
            "name": "Er. Priya Sharma",
            "role": "SAFETY_OFFICER",
            "designation": "Senior Mine Safety Officer",
            "subsidiary_id": ecl_id,
            "mine_id": primary_mine_id,
            "phone": "+91-9431108844",
            "is_active": True,
            "created_at": now,
            "updated_at": now
        },
        {
            "email": "inspector@coalgov.in",
            "password_hash": hash_password("Inspect@1234"),
            "name": "Shri Amitav Ghosh",
            "role": "INSPECTION_OFFICER",
            "designation": "Statutory Mining Inspector",
            "subsidiary_id": ecl_id,
            "mine_id": primary_mine_id,
            "phone": "+91-9431109922",
            "is_active": True,
            "created_at": now,
            "updated_at": now
        },
        {
            "email": "env.officer@coalgov.in",
            "password_hash": hash_password("Env@1234"),
            "name": "Dr. Neha Kulkarni",
            "role": "ENVIRONMENTAL_OFFICER",
            "designation": "Chief Environmental Officer",
            "subsidiary_id": ecl_id,
            "mine_id": primary_mine_id,
            "phone": "+91-9431107711",
            "is_active": True,
            "created_at": now,
            "updated_at": now
        },
        {
            "email": "contractor@abcexcavators.com",
            "password_hash": hash_password("Contractor@1234"),
            "name": "Shri Rajesh Gupta",
            "role": "CONTRACTOR",
            "designation": "Managing Director, ABC Earthmovers Ltd",
            "subsidiary_id": ecl_id,
            "mine_id": primary_mine_id,
            "phone": "+91-9831104433",
            "is_active": True,
            "created_at": now,
            "updated_at": now
        },
        {
            "email": "dgms.inspector@gov.in",
            "password_hash": hash_password("Dgms@1234"),
            "name": "Shri D. K. Sengupta",
            "role": "REGULATORY_AUTHORITY",
            "designation": "Deputy Director of Mines Safety (DGMS)",
            "subsidiary_id": None,
            "mine_id": None,
            "phone": "+91-9431105500",
            "is_active": True,
            "created_at": now,
            "updated_at": now
        }
    ]

    for u in users_data:
        mongo.users.update_one({"email": u["email"]}, {"$set": u}, upsert=True)

    safety_officer_doc = mongo.users.find_one({"email": "safety.officer@coalgov.in"})
    safety_officer_id = str(safety_officer_doc["_id"])

    # 6. Seed Compliance Requirements
    compliance_items = [
        {
            "title": "Monthly Airborne Dust Survey (CMR Reg 104)",
            "description": "Statutory gravimetric dust sampling at pit face and transfer points",
            "category": "Safety",
            "applicable_mine": primary_mine_id,
            "responsible_role": "SAFETY_OFFICER",
            "frequency": "MONTHLY",
            "due_date": now + datetime.timedelta(days=12),
            "status": "DUE_SOON",
            "evidence": [],
            "statutory_reference": "CMR 2017 Reg. 104",
            "is_demo": True,
            "created_at": now,
            "updated_at": now
        },
        {
            "title": "Highwall Bench Slope Stability Radar Audit",
            "description": "Digital laser prism scan of active quarry bench faces",
            "category": "Safety",
            "applicable_mine": primary_mine_id,
            "responsible_role": "SAFETY_OFFICER",
            "frequency": "WEEKLY",
            "due_date": now + datetime.timedelta(days=2),
            "status": "COMPLIANT",
            "evidence": ["/api/documents/file/evidence/slope_scan_verified.pdf"],
            "statutory_reference": "DGMS Circular 03/2021",
            "is_demo": True,
            "created_at": now,
            "updated_at": now
        },
        {
            "title": "Quarterly Ambient Air & Water Quality Clearance",
            "description": "MoEFCC continuous emission monitoring report submission",
            "category": "Environment",
            "applicable_mine": primary_mine_id,
            "responsible_role": "ENVIRONMENTAL_OFFICER",
            "frequency": "QUARTERLY",
            "due_date": now - datetime.timedelta(days=3),
            "status": "OVERDUE",
            "evidence": [],
            "statutory_reference": "Environment Protection Act 1986",
            "is_demo": True,
            "created_at": now,
            "updated_at": now
        }
    ]
    for c in compliance_items:
        mongo.compliance_requirements.update_one({"title": c["title"], "applicable_mine": c["applicable_mine"]}, {"$set": c}, upsert=True)

    # 7. Seed Sample Violations & Corrective Actions (CAPA)
    violations_to_seed = [
        # Rajmahal (4 violations: 1 Critical, 2 High, 1 Medium)
        {
            "mine_id": primary_mine_id,
            "zone": "Pit 1 - Primary Coal Extraction Bench",
            "category": "PPE_VIOLATION",
            "description": "3 dumper spotters observed without safety helmets during coal loading operations.",
            "severity": "HIGH",
            "source": "AI_DETECTION",
            "evidence": ["/api/documents/file/evidence/annotated_sample_ppe.jpg"],
            "latitude": 25.0485,
            "longitude": 87.3785,
            "detected_by": "AI_DETECTION_ENGINE",
            "assigned_to": safety_officer_id,
            "deadline": now + datetime.timedelta(hours=20),
            "status": "ASSIGNED",
            "is_demo": True,
            "created_at": now,
            "updated_at": now
        },
        {
            "mine_id": primary_mine_id,
            "zone": "North Haul Road & Heavy Vehicle Transit",
            "category": "SLOPE_STABILITY",
            "description": "Haul road safety berm height measured below 1.5m along hazardous incline ramp.",
            "severity": "CRITICAL",
            "source": "FIELD_REPORT",
            "evidence": [],
            "latitude": 25.0460,
            "longitude": 87.3760,
            "detected_by": safety_officer_id,
            "assigned_to": safety_officer_id,
            "deadline": now + datetime.timedelta(hours=12),
            "status": "DETECTED",
            "is_demo": True,
            "created_at": now,
            "updated_at": now
        },
        {
            "mine_id": primary_mine_id,
            "zone": "Pit 1 - Extraction Bench",
            "category": "EQUIPMENT_SAFETY",
            "description": "Excavator EX-201 reverse audio-visual alarm (AVRA) failed pre-shift inspection.",
            "severity": "HIGH",
            "source": "INSPECTION",
            "evidence": [],
            "latitude": 25.0475,
            "longitude": 87.3770,
            "detected_by": safety_officer_id,
            "assigned_to": safety_officer_id,
            "deadline": now + datetime.timedelta(hours=24),
            "status": "CORRECTIVE_ACTION",
            "is_demo": True,
            "created_at": now,
            "updated_at": now
        },
        {
            "mine_id": primary_mine_id,
            "zone": "North Haul Road",
            "category": "VENTILATION_DUST",
            "description": "Continuous water bowser dust suppression delayed on main coal transit road.",
            "severity": "MEDIUM",
            "source": "FIELD_REPORT",
            "evidence": [],
            "latitude": 25.0455,
            "longitude": 87.3755,
            "detected_by": safety_officer_id,
            "assigned_to": safety_officer_id,
            "deadline": now + datetime.timedelta(hours=48),
            "status": "ASSIGNED",
            "is_demo": True,
            "created_at": now,
            "updated_at": now
        },
        # Kusunda (2 violations: 1 High, 1 Medium)
        {
            "mine_id": kusunda_id,
            "zone": "Sector 3 Highwall Bench",
            "category": "SLOPE_STABILITY",
            "description": "Coal bench face slope angle exceeds 45 degrees without continuous radar monitoring.",
            "severity": "HIGH",
            "source": "INSPECTION",
            "evidence": [],
            "latitude": 23.7745,
            "longitude": 86.4168,
            "detected_by": "DGMS_INSPECTION",
            "assigned_to": safety_officer_id,
            "deadline": now + datetime.timedelta(hours=24),
            "status": "DETECTED",
            "is_demo": True,
            "created_at": now,
            "updated_at": now
        },
        {
            "mine_id": kusunda_id,
            "zone": "Substation Switchyard",
            "category": "ELECTRICAL_SAFETY",
            "description": "Surface rainwater accumulation near 3.3kV mobile transformer unit.",
            "severity": "MEDIUM",
            "source": "FIELD_REPORT",
            "evidence": [],
            "latitude": 23.7750,
            "longitude": 86.4170,
            "detected_by": safety_officer_id,
            "assigned_to": safety_officer_id,
            "deadline": now + datetime.timedelta(hours=48),
            "status": "ASSIGNED",
            "is_demo": True,
            "created_at": now,
            "updated_at": now
        },
        # Sonepur Bazari (1 violation: 1 Medium)
        {
            "mine_id": secondary_mine_id,
            "zone": "Main Coal Washery & Stockpile",
            "category": "FIRE_SAFETY",
            "description": "Workshop bay 2 missing monthly dry chemical fire extinguisher inspection tags.",
            "severity": "MEDIUM",
            "source": "INSPECTION",
            "evidence": [],
            "latitude": 23.6840,
            "longitude": 87.2140,
            "detected_by": safety_officer_id,
            "assigned_to": safety_officer_id,
            "deadline": now + datetime.timedelta(hours=48),
            "status": "ASSIGNED",
            "is_demo": True,
            "created_at": now,
            "updated_at": now
        },
        # Moonidih (1 violation: 1 High)
        {
            "mine_id": moonidih_id,
            "zone": "Return Airway Panel 4B",
            "category": "VENTILATION_DUST",
            "description": "Return airway panel 4B telemetry delay for air velocity monitoring.",
            "severity": "HIGH",
            "source": "AI_DETECTION",
            "evidence": [],
            "latitude": 23.7385,
            "longitude": 86.3485,
            "detected_by": "AI_DETECTION_ENGINE",
            "assigned_to": safety_officer_id,
            "deadline": now + datetime.timedelta(hours=24),
            "status": "DETECTED",
            "is_demo": True,
            "created_at": now,
            "updated_at": now
        }
    ]

    first_v_id = None
    for v_item in violations_to_seed:
        v_res = mongo.violations.insert_one(v_item)
        if not first_v_id:
            first_v_id = str(v_res.inserted_id)

    capa_doc = {
        "violation_id": first_v_id,
        "mine_id": primary_mine_id,
        "assigned_to": safety_officer_id,
        "description": "Issue approved safety helmets, conduct on-site briefing, and log biometric compliance check.",
        "deadline": now + datetime.timedelta(hours=20),
        "evidence": [],
        "completion_date": None,
        "verification_status": "PENDING",
        "escalation_tier": 0,
        "is_demo": True,
        "created_at": now,
        "updated_at": now
    }
    mongo.corrective_actions.insert_one(capa_doc)

    # 8. Seed Sample Inspection
    insp_doc = {
        "mine_id": primary_mine_id,
        "officer_id": safety_officer_id,
        "inspection_type": "ROUTINE_SAFETY",
        "location": "North Haul Road & Pit Crest",
        "latitude": 25.0475,
        "longitude": 87.3775,
        "scheduled_date": (now - datetime.timedelta(days=1)).isoformat(),
        "timestamp": now,
        "observations": [
            {"item": "Haul Road Berms", "status": "SATISFACTORY", "remarks": "Berm height maintained at 2.5m"},
            {"item": "Dust Suppression", "status": "ACTION_REQUIRED", "remarks": "Water bowser deployment delayed on segment 4"}
        ],
        "photos": [],
        "videos": [],
        "severity": "MEDIUM",
        "status": "IN_PROGRESS",
        "remarks": "Mid-shift surprise safety inspection",
        "is_demo": True,
        "created_at": now,
        "updated_at": now
    }
    mongo.inspections.insert_one(insp_doc)

    # 9. Seed Registered Contractors
    contractor_doc = {
        "company_name": "ABC Earthmovers & Mining Infra Ltd (DEMO DATA)",
        "registration_number": "CON-ECL-2026-088",
        "mine_id": primary_mine_id,
        "contact_person": "Shri Rajesh Gupta",
        "contact_email": "contractor@abcexcavators.com",
        "contact_phone": "+91-9831104433",
        "workers_count": 85,
        "contract_start": (now - datetime.timedelta(days=60)).isoformat(),
        "contract_end": (now + datetime.timedelta(days=305)).isoformat(),
        "compliance_status": "COMPLIANT",
        "documents": [],
        "risk_score": 25,
        "risk_level": "LOW",
        "risk_factors": ["Normal operations. 1 minor PPE warning addressed."],
        "is_demo": True,
        "created_at": now,
        "updated_at": now
    }
    mongo.contractors.insert_one(contractor_doc)

    # 10. Seed Incident
    inc_doc = {
        "mine_id": primary_mine_id,
        "location": "Haul Road Segment 3",
        "latitude": 25.0465,
        "longitude": 87.3765,
        "incident_type": "MACHINERY_COLLISION",
        "severity": "MEDIUM",
        "description": "Dumper rear bumper brushed auxiliary water tanker during reversing maneuver. No injuries recorded.",
        "persons_involved": ["Driver D-104", "Operator W-09"],
        "evidence": [],
        "reported_by": safety_officer_id,
        "reported_at": now - datetime.timedelta(days=4),
        "investigation_status": "ROOT_CAUSE_ANALYSIS",
        "root_cause": "Faulty Audio-Visual Reverse Alarm (AVRA) on dumper D-104.",
        "corrective_action": "Mandatory pre-shift alarm verification before machine leaves workshop bay.",
        "closure_status": "OPEN",
        "is_demo": True,
        "created_at": now,
        "updated_at": now
    }
    mongo.incidents.insert_one(inc_doc)

    # 11. Seed Sample OCR Documents (Contractor Agreement, Mine SOP, Safety Rules)
    sample_docs = [
        {
            "original_filename": "ABC_Earthmovers_Mining_Contract_2026.pdf",
            "file_path": "documents/ABC_Earthmovers_Mining_Contract_2026.pdf",
            "file_url": "/api/documents/file/documents/ABC_Earthmovers_Mining_Contract_2026.pdf",
            "file_size": 245760,
            "document_type": "CONTRACTOR_AGREEMENT",
            "mine_id": primary_mine_id,
            "document_number": "CON-AGR-ECL-2026-088",
            "authority": "Eastern Coalfields Limited & DGMS",
            "issue_date": now - datetime.timedelta(days=60),
            "expiry_date": now + datetime.timedelta(days=305),
            "extracted_text": (
                "CONTRACTOR STATUTORY SAFETY & OPERATIONAL AGREEMENT\n"
                "Contract Reference: CON-AGR-ECL-2026-088\n"
                "Contractor: ABC Earthmovers & Mining Infra Ltd\n"
                "Registration No: CON-ECL-2026-088 | Mine: Rajmahal Open Cast Project\n"
                "Contract Period: 01/01/2026 to 31/12/2026\n"
                "Total Contract Value: INR 14.50 Crores\n"
                "Deployed Statutory Workers: 85 Personnel\n"
                "Scope of Work: Overburden removal, coal seam excavation, and truck transport along North Haul Road.\n"
                "MANDATORY STATUTORY SAFETY CLAUSES:\n"
                "Clause 4.1: Contractor shall provide DGMS-approved safety footwear, helmets, and high-visibility vests at no charge to all 85 workers (CMR 2017 Reg. 191).\n"
                "Clause 4.2: All heavy machinery (dumpers, excavators) deployed must possess functional Audio-Visual Reverse Alarms (AVRA) and proximity sensors (CMR 2017 Reg. 228).\n"
                "Clause 9.3: Penalty of INR 50,000 per recurring safety infraction and immediate contract suspension upon any critical safety breach.\n"
                "Clause 11.2: Third-party worker accident insurance coverage of minimum INR 15 Lakhs per deployed worker mandatory before entering operational benches."
            ),
            "ocr_mode": "pypdf_native",
            "status": "ACTIVE",
            "requires_manual_verification": False,
            "upload_user": safety_officer_id,
            "is_demo": True,
            "created_at": now,
            "updated_at": now
        },
        {
            "original_filename": "SOP_04_Haul_Road_and_Slope_Stability.pdf",
            "file_path": "documents/SOP_04_Haul_Road_and_Slope_Stability.pdf",
            "file_url": "/api/documents/file/documents/SOP_04_Haul_Road_and_Slope_Stability.pdf",
            "file_size": 184320,
            "document_type": "MINE_SOP",
            "mine_id": primary_mine_id,
            "document_number": "SOP-RJM-2026-04",
            "authority": "DGMS & CIL Safety Directorate",
            "issue_date": now - datetime.timedelta(days=45),
            "expiry_date": now + datetime.timedelta(days=685),
            "extracted_text": (
                "MINE STANDARD OPERATING PROCEDURE (SOP)\n"
                "SOP Number: SOP-RJM-2026-04\n"
                "Title: Safe Operation of Heavy Earth Moving Machinery and Haul Road Transit\n"
                "Mine: Rajmahal Open Cast Project | Authority: DGMS & CIL Safety Board\n"
                "Date of Issue: 15/01/2026 | Effective Validity: 31/12/2027\n"
                "OPERATING PARAMETERS & SAFETY RULES:\n"
                "1. Speed Limits: Maximum 20 km/h on active pit ramps; maximum 30 km/h on main haulage corridors.\n"
                "2. Safety Berms: Berm height along outer edges must equal or exceed 2.5 meters (at least half the wheel diameter of the largest dump truck).\n"
                "3. Slope Stability: Coal bench slope angle must not exceed 45 degrees without continuous slope stability radar monitoring.\n"
                "4. Dust Control: Wet mist spraying using dedicated water bowsers required at least once every 2 hours.\n"
                "5. Emergency Evacuation: In case of audible siren (3 continuous blasts), all personnel must evacuate to designated Muster Station Alpha."
            ),
            "ocr_mode": "pypdf_native",
            "status": "ACTIVE",
            "requires_manual_verification": False,
            "upload_user": safety_officer_id,
            "is_demo": True,
            "created_at": now,
            "updated_at": now
        },
        {
            "original_filename": "Mine_Safety_Rules_and_Emergency_Action_Plan.pdf",
            "file_path": "documents/Mine_Safety_Rules_and_Emergency_Action_Plan.pdf",
            "file_url": "/api/documents/file/documents/Mine_Safety_Rules_and_Emergency_Action_Plan.pdf",
            "file_size": 310240,
            "document_type": "SAFETY_RULES",
            "mine_id": primary_mine_id,
            "document_number": "SAFE-RULE-ECL-2026-01",
            "authority": "Directorate General of Mines Safety (DGMS)",
            "issue_date": now - datetime.timedelta(days=90),
            "expiry_date": now + datetime.timedelta(days=275),
            "extracted_text": (
                "MINE STATUTORY SAFETY RULES & EMERGENCY RESPONSE PLAN\n"
                "Document No: SAFE-RULE-ECL-2026-01\n"
                "Applicable Code: Coal Mines Regulations 2017 & Mines Act 1952\n"
                "Mine: All Operational Pits and Processing Plants\n"
                "STATUTORY MANDATES:\n"
                "1. Daily Pre-Shift Breathalyzer and Biometric PPE Inspection at Turnstile Gates.\n"
                "2. Audio-Visual Reverse Alarms (AVRA) inspection logged every 24 hours in Form VI.\n"
                "3. Immediate statutory accident telegraphic notification within 24 hours under Section 23 of Mines Act 1952.\n"
                "4. Continuous carbon monoxide monitoring and automatic emergency siren testing every Monday at 08:00 hrs."
            ),
            "ocr_mode": "pypdf_native",
            "status": "ACTIVE",
            "requires_manual_verification": False,
            "upload_user": safety_officer_id,
            "is_demo": True,
            "created_at": now,
            "updated_at": now
        }
    ]

    for s_doc in sample_docs:
        mongo.documents.update_one(
            {"document_number": s_doc["document_number"]},
            {"$set": s_doc},
            upsert=True
        )

    logger.info("[Seed] Database seeding completed successfully. All 8 role accounts and demo assets ready.")
    return True
