from typing import List, Dict, Any

STATUTORY_KNOWLEDGE_CORPUS: List[Dict[str, Any]] = [
    {
        "doc_id": "CMR-2017-REG-191",
        "title": "Coal Mines Regulations 2017 - Regulation 191: Protective Footwear and Helmets",
        "regulation": "CMR 2017 Reg. 191",
        "authority": "Directorate General of Mines Safety (DGMS)",
        "category": "Safety / PPE",
        "content": (
            "Regulation 191 dictates that no person shall go into, or be allowed to go into, "
            "or work in any mine unless he wears a safety helmet and protective footwear of a type approved by the Chief Inspector. "
            "It is the duty of the mine owner, agent, and manager to provide suitable PPE free of charge to all workers. "
            "Failure to wear or ensure PPE compliance incurs strict penalties under the Mines Act 1952."
        )
    },
    {
        "doc_id": "CMR-2017-REG-104",
        "title": "Coal Mines Regulations 2017 - Regulation 104: Precautions Against Inflammable Gas and Coal Dust",
        "regulation": "CMR 2017 Reg. 104",
        "authority": "DGMS",
        "category": "Ventilation & Dust",
        "content": (
            "Regulation 104 mandates regular mist spraying and wet dust suppression at all loading, unloading, and coal transfer points. "
            "Airborne dust concentration surveys must be recorded at least once every calendar month. "
            "No dry drilling shall be conducted without an approved dust extraction or collection device."
        )
    },
    {
        "doc_id": "CMR-2017-REG-110",
        "title": "Coal Mines Regulations 2017 - Regulation 110: Precautions Against Spontaneous Combustion and Fire",
        "regulation": "CMR 2017 Reg. 110",
        "authority": "DGMS",
        "category": "Fire Safety",
        "content": (
            "Regulation 110 specifies that in coal seams liable to spontaneous heating, panels shall be isolated by explosion-proof "
            "stopping seals once extraction is completed. Continuous carbon monoxide monitoring with automated alarms is required "
            "at return airways and coal stockyards."
        )
    },
    {
        "doc_id": "CMR-2017-REG-228",
        "title": "Coal Mines Regulations 2017 - Regulation 228: Code of Safe Practices for Heavy Earth Moving Machinery (HEMM)",
        "regulation": "CMR 2017 Reg. 228",
        "authority": "DGMS",
        "category": "Equipment Safety",
        "content": (
            "Regulation 228 requires that every mine deploying dumpers, excavators, and draglines maintain a written Code of Safe Practice. "
            "Every dump truck must be equipped with audio-visual reverse alarms (AVRA), blind-spot mirrors, rear cameras, "
            "and proximity warning devices. Haul roads must maintain a width of not less than three times the width of the largest machine."
        )
    },
    {
        "doc_id": "MINES-ACT-1952-SEC-23",
        "title": "Mines Act 1952 - Section 23: Notice of Accidents",
        "regulation": "Mines Act 1952 Sec. 23",
        "authority": "Ministry of Labour & Employment / DGMS",
        "category": "Incident Reporting",
        "content": (
            "Section 23 establishes that whenever there occurs in or about a mine an accident causing loss of life, serious bodily injury, "
            "explosion, ignition, outbreak of fire, or inrush of water, the owner, agent, or manager shall forthwith give notice thereof "
            "to the Chief Inspector and the District Magistrate within 24 hours in statutory Form IV-A."
        )
    },
    {
        "doc_id": "DGMS-CIRCULAR-03-2021",
        "title": "DGMS Technical Circular 03/2021: Slope Stability Monitoring in Opencast Mines",
        "regulation": "DGMS Circular 03/2021",
        "authority": "DGMS",
        "category": "Slope Stability",
        "content": (
            "Recommends continuous radar or prism-based real-time slope monitoring systems for highwall benches exceeding 30 meters depth. "
            "Daily inspections of bench toe crests, tension cracks, and drainage diversion channels must be documented by the mine surveyor."
        )
    },
    {
        "doc_id": "MOEFCC-AIR-WATER-NOC",
        "title": "MoEFCC Environmental Clearance Compliance Guidelines for Coal Mining",
        "regulation": "Environment (Protection) Act 1986",
        "authority": "MoEFCC / CPCB",
        "category": "Environmental Compliance",
        "content": (
            "Mines must maintain continuous ambient air quality monitoring stations (CAAQMS) transmitting PM10 and PM2.5 data live to SPCB servers. "
            "Effluent treatment plants (ETP) and oil-grease traps at mine workshops must be operated continuously with zero liquid discharge (ZLD) adherence."
        )
    }
]
