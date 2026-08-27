from odoo import Command, fields


QUALITY_AREA_DEFINITIONS = [
    (10, "LEAD", "Leadership & Governance", "Direction, accountability, scope, and operating model for the QMS."),
    (20, "PLAN", "Planning & Performance", "Risk, objectives, metrics, and planned performance control."),
    (30, "SUPPORT", "Support & Documented Information", "Resources, competence, communication, documents, and records."),
    (40, "OPERATE", "Operational Management", "Customer, design, purchasing, production, release, and change execution."),
    (50, "EVALUATE", "Evaluation & Review", "Monitoring, audit, customer feedback, and leadership review."),
    (60, "IMPROVE", "Improvement System", "Nonconformity, root cause, corrective action, and improvement flow."),
]


def _quality_area_code(control_data):
    category = control_data.get("category")
    capability = control_data.get("capability")
    domain = control_data.get("domain", "")
    if category == "governance":
        return "LEAD"
    if category == "training" or domain in {
        "Documented Information",
        "Document Control",
        "Records",
        "Competence & Awareness",
        "Communication",
        "Infrastructure & Environment",
        "Monitoring Resources",
        "Knowledge",
    }:
        return "SUPPORT"
    if category == "supplier" or capability in {"Operations", "Supplier Management", "Design Control", "Change Management"}:
        return "OPERATE"
    if capability in {"Internal Audit", "Management Review", "Customer Performance"}:
        return "EVALUATE"
    if category == "improvement" or capability in {"NCR", "CAPA", "Improvement"}:
        return "IMPROVE"
    if category == "performance" or capability in {"Objectives and KPIs", "Performance Data"}:
        return "PLAN"
    return "PLAN"


def _quality_guidance_values(control_data):
    name = control_data["name"]
    activity_names = ", ".join(activity[0] for activity in control_data["activities"])
    evidence_names = ", ".join(item[0] for item in control_data["evidence"])
    return {
        "guidance_purpose": f"Use {name} to make the expected quality behavior visible, assigned, and reviewable.",
        "guidance_why": f"This control reduces ambiguity by turning {control_data['domain'].lower()} into owned work, objective evidence, and repeatable review points.",
        "implementation_guidance": "Start with the current process, identify the owner and decision points, then configure the simplest Perfect Match record that proves the method is operating. Keep the method practical for the organization before adding extra approval layers.",
        "recommended_steps": f"1. Confirm owner and scope.\n2. Compare current practice with the control objective.\n3. Complete these starter activities: {activity_names}.\n4. Attach or create evidence before marking the control implemented.",
        "recommended_tools": f"Use the implementation project, generated activities, evidence records, and the operational Perfect Match capability: {control_data['capability']}.",
        "evidence_guidance": f"Accept evidence when it is current, owned, traceable to the organization, and sufficient to show the method is in use. Starter evidence type: {evidence_names}.",
        "practical_notes": "Favor small working records over decorative documentation. Client-specific decisions belong on the implementation control instance, not on the reusable framework control.",
    }


def _evidence_acceptance_criteria(evidence_type):
    label = evidence_type.replace("_", " ")
    return "\n".join(
        [
            "The evidence set identifies the applicable control and implementation scope.",
            "The evidence set identifies an accountable owner and a relevant date or revision marker.",
            f"The evidence set contains a current {label} source or an equivalent traceable source.",
            "The reviewer can retrieve the source and confirm that the set is complete for the claimed scope.",
            "The evidence is internally consistent and supports the implementation decision being reviewed.",
        ]
    )


def _find_or_adopt_evidence_requirement(env, control, name, definition_key):
    Requirement = env["pm.qms.evidence.requirement"]
    keyed = Requirement.search([("definition_key", "=", definition_key)])
    if len(keyed) > 1:
        raise ValueError(f"Duplicate evidence requirement definition {definition_key} exists.")
    if keyed:
        if keyed.control_id != control:
            raise ValueError(f"Evidence requirement definition {definition_key} belongs to another control.")
        return keyed
    legacy = Requirement.search([("control_id", "=", control.id), ("name", "=", name)])
    if len(legacy) > 1:
        raise ValueError(f"Duplicate legacy evidence requirement {name} exists.")
    if legacy:
        if legacy.definition_key and legacy.definition_key != definition_key:
            raise ValueError(f"Legacy evidence requirement {name} has an incompatible definition key.")
        legacy.write({"definition_key": definition_key})
        return legacy
QUALITY_CONTROLS = [
    {
        "code": "PM-QMP-ORG-001",
        "name": "Organization Context Register",
        "domain": "Organization & Context",
        "process_code": "PM-QMP-DOM-ORG",
        "category": "governance",
        "capability": "QMS Framework",
        "objective": "Maintain a practical understanding of internal and external conditions that can affect the quality management system.",
        "description": "Perfect Match method for keeping business context visible during QMS planning and review without copying external requirement language.",
        "activities": [
            ("Identify context inputs", "Context inputs and owners identified.", "QMS Manager"),
            ("Review context changes", "Context review cadence defined.", "Leadership Team"),
        ],
        "evidence": [("Context register", "record", "Current register of relevant context factors and review notes.")],
    },
    {
        "code": "PM-QMP-ORG-002",
        "name": "Interested Party Needs Register",
        "domain": "Organization & Context",
        "process_code": "PM-QMP-DOM-ORG",
        "category": "governance",
        "capability": "QMS Framework",
        "objective": "Identify parties whose needs affect quality commitments, operating priorities, or QMS planning.",
        "description": "Perfect Match method for turning stakeholder expectations into maintainable planning inputs.",
        "activities": [
            ("Identify interested parties", "Interested parties and relevant needs listed.", "QMS Manager"),
            ("Assign review ownership", "Stakeholder review responsibility assigned.", "Leadership Team"),
        ],
        "evidence": [("Interested party register", "record", "Current register with owners and review dates.")],
    },
    {
        "code": "PM-QMP-SCOPE-001",
        "name": "QMS Scope Statement",
        "domain": "QMS Scope",
        "process_code": "PM-QMP-DOM-SCOPE",
        "category": "governance",
        "capability": "QMS Framework",
        "objective": "Define the organizational, product, service, and process boundaries of the quality management system.",
        "description": "Perfect Match method for documenting what the QMS covers and why any boundaries or exclusions are justified.",
        "activities": [
            ("Draft QMS scope", "Scope statement drafted for management review.", "QMS Manager"),
            ("Confirm applicability decisions", "Applicability rationale recorded for scoped boundaries.", "Leadership Team"),
        ],
        "evidence": [("Approved QMS scope statement", "document", "Approved scope statement or equivalent controlled record.")],
    },
    {
        "code": "PM-QMP-PROC-001",
        "name": "Process Architecture",
        "domain": "Process Management",
        "process_code": "PM-QMP-DOM-PROC",
        "category": "process",
        "capability": "Process Management",
        "objective": "Define the process structure, interactions, inputs, outputs, and ownership needed to operate the QMS.",
        "description": "Perfect Match method for building a process model that can be implemented, measured, audited, and improved.",
        "activities": [
            ("Map QMS processes", "Process map or process inventory drafted.", "Process Owner"),
            ("Define interactions", "Inputs, outputs, and interactions identified.", "Process Owner"),
        ],
        "evidence": [("Process map", "document", "Current process map or process interaction record.")],
    },
    {
        "code": "PM-QMP-GOV-001",
        "name": "Leadership Accountability",
        "domain": "Governance & Leadership",
        "process_code": "PM-QMP-DOM-GOV",
        "category": "governance",
        "capability": "Leadership",
        "objective": "Make leadership accountability for quality direction, QMS support, and performance follow-up explicit.",
        "description": "Perfect Match method for keeping quality leadership visible through responsibilities, decisions, and review cadence.",
        "activities": [
            ("Confirm leadership responsibilities", "Leadership responsibilities documented.", "Leadership Team"),
            ("Schedule QMS leadership review", "Leadership review rhythm defined.", "QMS Manager"),
        ],
        "evidence": [("Leadership responsibility record", "record", "Responsibility record, meeting minutes, or equivalent approval evidence.")],
    },
    {
        "code": "PM-QMP-ROLE-001",
        "name": "Responsibility And Authority Matrix",
        "domain": "Roles & Responsibilities",
        "process_code": "PM-QMP-DOM-GOV",
        "category": "governance",
        "capability": "Leadership",
        "objective": "Define QMS roles, authorities, backups, and escalation paths for quality-critical work.",
        "description": "Perfect Match method for reducing ambiguity in QMS ownership and execution.",
        "activities": [
            ("Build responsibility matrix", "QMS roles and authorities listed.", "QMS Manager"),
            ("Confirm role acceptance", "Role owners acknowledge assigned responsibilities.", "Process Owner"),
        ],
        "evidence": [("Responsibility matrix", "record", "Approved matrix or role assignment record.")],
    },
    {
        "code": "PM-QMP-POL-001",
        "name": "Quality Policy Direction",
        "domain": "Policy & Direction",
        "process_code": "PM-QMP-DOM-GOV",
        "category": "governance",
        "capability": "Leadership",
        "objective": "Set a clear quality direction that can guide objectives, process behavior, and improvement priorities.",
        "description": "Perfect Match method for publishing and maintaining a practical quality policy.",
        "activities": [
            ("Draft quality direction", "Quality policy language drafted in organization voice.", "Leadership Team"),
            ("Plan communication", "Communication and awareness method selected.", "QMS Manager"),
        ],
        "evidence": [("Approved quality policy", "document", "Controlled or otherwise approved quality policy record.")],
    },
    {
        "code": "PM-QMP-RISK-001",
        "name": "Risk And Opportunity Planning",
        "domain": "Risks & Opportunities",
        "process_code": "PM-QMP-DOM-RISK",
        "category": "improvement",
        "capability": "Risk Management",
        "objective": "Identify quality risks and opportunities, assign responses, and review whether actions remain effective.",
        "description": "Perfect Match method that uses the existing risk and opportunity module for operational execution.",
        "activities": [
            ("Configure risk ownership", "Risk owners and review frequency defined.", "QMS Manager"),
            ("Create initial risk register", "Initial quality risk and opportunity records created.", "Process Owner"),
        ],
        "evidence": [("Risk and opportunity register", "record", "Current risk/opportunity records from the QMS risk capability.")],
    },
    {
        "code": "PM-QMP-OBJ-001",
        "name": "Quality Objective Deployment",
        "domain": "Objectives & Performance",
        "process_code": "PM-QMP-DOM-PERF",
        "category": "performance",
        "capability": "Objectives and KPIs",
        "objective": "Translate quality direction into measurable objectives with owners, targets, and review cadence.",
        "description": "Perfect Match method that uses the existing objective and KPI capabilities for operational tracking.",
        "activities": [
            ("Define quality objectives", "Objectives documented with owners and target dates.", "Leadership Team"),
            ("Link objectives to measures", "Each objective linked to one or more measures where practical.", "QMS Manager"),
        ],
        "evidence": [("Quality objectives register", "record", "Current objective records with owners and status.")],
    },
    {
        "code": "PM-QMP-RES-001",
        "name": "Resource Planning",
        "domain": "Resources",
        "process_code": "PM-QMP-DOM-RES",
        "category": "process",
        "capability": "Resource Planning",
        "objective": "Identify resources needed to operate and improve quality-critical processes.",
        "description": "Perfect Match method for planning people, tools, infrastructure, environment, and support resources.",
        "activities": [
            ("Identify resource needs", "Resource needs listed by process or capability.", "Process Owner"),
            ("Assign resource actions", "Gaps assigned to owners with target dates.", "Leadership Team"),
        ],
        "evidence": [("Resource planning record", "record", "Resource plan, action list, or management review input.")],
    },
    {
        "code": "PM-QMP-CMP-001",
        "name": "Competence Management",
        "domain": "Competence & Training",
        "process_code": "PM-QMP-DOM-COMP",
        "category": "training",
        "capability": "Competence and Training",
        "objective": "Define competence needs for quality-impacting roles and retain evidence of qualification or training.",
        "description": "Perfect Match method for linking role expectations to training, experience, qualification, and records.",
        "activities": [
            ("Define competence needs", "Competence needs listed for quality-impacting roles.", "QMS Manager"),
            ("Collect competence evidence", "Training or qualification records identified.", "Process Owner"),
        ],
        "evidence": [("Competence matrix", "training", "Competence matrix or training/qualification records.")],
    },
    {
        "code": "PM-QMP-AWR-001",
        "name": "Quality Awareness",
        "domain": "Awareness",
        "process_code": "PM-QMP-DOM-COMP",
        "category": "training",
        "capability": "Competence and Training",
        "objective": "Ensure people understand quality direction, relevant responsibilities, and consequences of ineffective work.",
        "description": "Perfect Match method for practical awareness communication without turning awareness into a paperwork exercise.",
        "activities": [
            ("Plan awareness topics", "Awareness topics and audience identified.", "QMS Manager"),
            ("Record awareness delivery", "Awareness communication evidence retained.", "Process Owner"),
        ],
        "evidence": [("Awareness record", "training", "Training, communication, or acknowledgement records.")],
    },
    {
        "code": "PM-QMP-COM-001",
        "name": "QMS Communication Plan",
        "domain": "Communication",
        "process_code": "PM-QMP-DOM-COM",
        "category": "process",
        "capability": "Communication",
        "objective": "Define what quality information is communicated, by whom, to whom, when, and through which channel.",
        "description": "Perfect Match method for keeping quality communication intentional and reviewable.",
        "activities": [
            ("Define QMS communications", "Communication matrix or plan drafted.", "QMS Manager"),
            ("Assign communication owners", "Owners assigned for recurring quality communications.", "Leadership Team"),
        ],
        "evidence": [("QMS communication plan", "document", "Communication plan, matrix, or recurring meeting record.")],
    },
    {
        "code": "PM-QMP-DOC-001",
        "name": "Controlled Document Authorization",
        "domain": "Document Control",
        "process_code": "PM-QMP-DOM-DOC",
        "category": "document_control",
        "capability": "Document Control",
        "objective": "Ensure managed operational documents are reviewed and authorized before controlled release.",
        "description": "Perfect Match method for preparation, review, approval, revision, release, and obsolete document handling.",
        "activities": [
            ("Define document approval flow", "Document approval roles and steps defined.", "Document Owner"),
            ("Create controlled document register", "Controlled document register or equivalent view established.", "QMS Manager"),
        ],
        "evidence": [("Approved current revision", "approval", "Approved document revision or authorization record.")],
    },
    {
        "code": "PM-QMP-REC-001",
        "name": "Record And Evidence Control",
        "domain": "Record / Evidence Control",
        "process_code": "PM-QMP-DOM-DOC",
        "category": "evidence",
        "capability": "Evidence Management",
        "objective": "Define how QMS records and implementation evidence are retained, reviewed, and protected.",
        "description": "Perfect Match method that uses the evidence module for actual implementation evidence records.",
        "activities": [
            ("Define evidence expectations", "Evidence expectations listed for quality controls.", "QMS Manager"),
            ("Set record retention ownership", "Record retention owners and storage locations identified.", "Process Owner"),
        ],
        "evidence": [("Record control method", "document", "Record control procedure, matrix, or evidence review configuration.")],
    },
    {
        "code": "PM-QMP-CUST-001",
        "name": "Customer Requirement Capture",
        "domain": "Customer Management",
        "process_code": "PM-QMP-DOM-CUST",
        "category": "process",
        "capability": "Customer Management",
        "objective": "Capture customer needs and commitments in a way that can be reviewed before acceptance.",
        "description": "Perfect Match method for making customer requirements visible to operational planning and delivery.",
        "activities": [
            ("Define customer intake method", "Customer requirement intake method documented.", "Customer Owner"),
            ("Identify requirement records", "Customer requirement record sources identified.", "Process Owner"),
        ],
        "evidence": [("Customer requirement record", "record", "Order, contract, request, intake form, or equivalent requirement record.")],
    },
    {
        "code": "PM-QMP-REQ-001",
        "name": "Requirements Review And Commitment",
        "domain": "Requirements Review",
        "process_code": "PM-QMP-DOM-CUST",
        "category": "process",
        "capability": "Customer Management",
        "objective": "Review customer, operational, and applicable obligation details before committing to deliver.",
        "description": "Perfect Match method for confirming capability, exceptions, changes, and communication before acceptance.",
        "activities": [
            ("Define review criteria", "Requirements review criteria established.", "Customer Owner"),
            ("Record acceptance decision", "Acceptance or exception record retained.", "Process Owner"),
        ],
        "evidence": [("Requirements review record", "approval", "Reviewed order, quote, contract, or equivalent approval record.")],
    },
    {
        "code": "PM-QMP-DSG-001",
        "name": "Design And Development Control",
        "domain": "Design & Development",
        "process_code": "PM-QMP-DOM-DESIGN",
        "category": "process",
        "capability": "Design and Development",
        "objective": "Control design or development work when the organization is responsible for defining new or changed outputs.",
        "description": "Perfect Match method for planning design work, reviewing progress, verifying outputs, and approving release when applicable.",
        "activities": [
            ("Determine design applicability", "Design responsibility applicability decision recorded.", "QMS Manager"),
            ("Define design review points", "Design review and approval points identified.", "Design Owner"),
        ],
        "evidence": [("Design control record", "record", "Design plan, review, verification, approval, or applicability record.")],
    },
    {
        "code": "PM-QMP-SUP-001",
        "name": "Supplier Qualification",
        "domain": "Purchasing & Supplier Management",
        "process_code": "PM-QMP-DOM-SUP",
        "category": "supplier",
        "capability": "Supplier Performance",
        "objective": "Define how external suppliers are evaluated and approved before they support quality-impacting work.",
        "description": "Perfect Match method that reuses Odoo partner master data and supplier-performance records.",
        "activities": [
            ("Define supplier approval criteria", "Supplier approval criteria documented.", "Purchasing Owner"),
            ("Create approved supplier record", "Approved supplier record source established.", "Purchasing Owner"),
        ],
        "evidence": [("Supplier qualification record", "record", "Approved supplier list, evaluation, or qualification record.")],
    },
    {
        "code": "PM-QMP-SUP-002",
        "name": "Supplier Performance Monitoring",
        "domain": "Purchasing & Supplier Management",
        "process_code": "PM-QMP-DOM-SUP",
        "category": "supplier",
        "capability": "Supplier Performance",
        "objective": "Monitor supplier quality, delivery, and issue trends to support purchasing decisions and improvement.",
        "description": "Perfect Match method using existing supplier performance and supplier evaluation capabilities.",
        "activities": [
            ("Define supplier metrics", "Supplier performance metrics and review cadence defined.", "Purchasing Owner"),
            ("Review supplier actions", "Supplier follow-up actions assigned where needed.", "QMS Manager"),
        ],
        "evidence": [("Supplier performance record", "metric", "Supplier performance measurement or evaluation record.")],
    },
    {
        "code": "PM-QMP-OPS-001",
        "name": "Operational Planning And Criteria",
        "domain": "Operational Planning",
        "process_code": "PM-QMP-DOM-OPS",
        "category": "process",
        "capability": "Operations",
        "objective": "Plan quality-critical operational work with criteria, resources, responsibilities, and records.",
        "description": "Perfect Match method for turning process intent into controlled execution criteria.",
        "activities": [
            ("Define operational criteria", "Operational criteria documented for key processes.", "Process Owner"),
            ("Identify required records", "Execution and verification records identified.", "Process Owner"),
        ],
        "evidence": [("Operational planning record", "document", "Procedure, control plan, workflow, or work criteria record.")],
    },
    {
        "code": "PM-QMP-OPS-002",
        "name": "Work Instruction Control",
        "domain": "Production / Service Delivery",
        "process_code": "PM-QMP-DOM-OPS",
        "category": "document_control",
        "capability": "Operations",
        "objective": "Provide controlled instructions where consistent execution depends on defined steps or criteria.",
        "description": "Perfect Match method for keeping work instructions current, accessible, and aligned with actual operations.",
        "activities": [
            ("Identify instruction needs", "Processes requiring work instructions identified.", "Process Owner"),
            ("Authorize work instructions", "Work instruction approval route confirmed.", "Document Owner"),
        ],
        "evidence": [("Approved work instruction", "document", "Current authorized work instruction or equivalent execution guide.")],
    },
    {
        "code": "PM-QMP-REL-001",
        "name": "Verification And Release Control",
        "domain": "Release / Verification",
        "process_code": "PM-QMP-DOM-OPS",
        "category": "process",
        "capability": "Operations",
        "objective": "Define how outputs are verified and released before delivery or completion.",
        "description": "Perfect Match method for release checks, acceptance evidence, and authorization records.",
        "activities": [
            ("Define release criteria", "Release criteria and authority documented.", "Process Owner"),
            ("Identify release evidence", "Release evidence source identified.", "QMS Manager"),
        ],
        "evidence": [("Release verification record", "approval", "Inspection, verification, approval, or release record.")],
    },
    {
        "code": "PM-QMP-TRC-001",
        "name": "Identification And Traceability",
        "domain": "Identification & Traceability",
        "process_code": "PM-QMP-DOM-OPS",
        "category": "process",
        "capability": "Operations",
        "objective": "Maintain identification and traceability where needed to control status, history, or customer commitments.",
        "description": "Perfect Match method for deciding and documenting traceability levels appropriate to the organization.",
        "activities": [
            ("Determine traceability needs", "Traceability needs and applicability documented.", "Process Owner"),
            ("Define status identification", "Status identification method defined where applicable.", "Process Owner"),
        ],
        "evidence": [("Traceability record", "record", "Traceability log, label, status record, or applicability decision.")],
    },
    {
        "code": "PM-QMP-PROP-001",
        "name": "Customer Or External Property Care",
        "domain": "Customer / External Property",
        "process_code": "PM-QMP-DOM-OPS",
        "category": "process",
        "capability": "Operations",
        "objective": "Control customer or externally owned property while it is under the organization's responsibility.",
        "description": "Perfect Match method for identifying, protecting, reporting, and recording issues with external property.",
        "activities": [
            ("Identify external property flows", "External property touchpoints identified.", "Process Owner"),
            ("Define property issue reporting", "Issue reporting method defined.", "Customer Owner"),
        ],
        "evidence": [("External property record", "record", "Property log, receipt, condition record, or issue communication.")],
    },
    {
        "code": "PM-QMP-PRE-001",
        "name": "Preservation And Handling",
        "domain": "Preservation",
        "process_code": "PM-QMP-DOM-OPS",
        "category": "process",
        "capability": "Operations",
        "objective": "Protect quality-impacting outputs, materials, information, or deliverables during handling, storage, and delivery.",
        "description": "Perfect Match method for defining preservation controls suited to the organization's outputs.",
        "activities": [
            ("Identify preservation risks", "Preservation risks and control points listed.", "Process Owner"),
            ("Define handling controls", "Handling, storage, or delivery controls documented.", "Process Owner"),
        ],
        "evidence": [("Preservation control record", "record", "Handling instruction, storage log, delivery record, or applicability decision.")],
    },
    {
        "code": "PM-QMP-CHG-001",
        "name": "Controlled Change Management",
        "domain": "Change Management",
        "process_code": "PM-QMP-DOM-CHANGE",
        "category": "process",
        "capability": "Change Management",
        "objective": "Evaluate, approve, communicate, and verify changes that can affect quality outcomes.",
        "description": "Perfect Match method for avoiding uncontrolled process, product, service, supplier, or document changes.",
        "activities": [
            ("Define change trigger criteria", "Change trigger criteria documented.", "QMS Manager"),
            ("Assign change approval route", "Approval and verification path assigned.", "Process Owner"),
        ],
        "evidence": [("Change approval record", "approval", "Change request, approval, verification, or communication record.")],
    },
    {
        "code": "PM-QMP-NCO-001",
        "name": "Nonconforming Output Handling",
        "domain": "Nonconforming Outputs",
        "process_code": "PM-QMP-DOM-NCR",
        "category": "improvement",
        "capability": "NCR",
        "objective": "Identify, control, disposition, and verify outputs that do not meet defined criteria.",
        "description": "Perfect Match method that uses the existing NCR capability for operational control and traceability.",
        "activities": [
            ("Define nonconforming output flow", "Containment and disposition flow documented.", "QMS Manager"),
            ("Configure NCR ownership", "NCR owners and verification roles assigned.", "Process Owner"),
        ],
        "evidence": [("Nonconforming output record", "record", "NCR, disposition, containment, or verification record.")],
    },
    {
        "code": "PM-QMP-SAT-001",
        "name": "Customer Feedback And Satisfaction",
        "domain": "Customer Satisfaction",
        "process_code": "PM-QMP-DOM-CUST",
        "category": "performance",
        "capability": "Customer Performance",
        "objective": "Collect and review customer feedback and satisfaction information to identify performance trends and improvement needs.",
        "description": "Perfect Match method using existing customer performance and satisfaction records.",
        "activities": [
            ("Define feedback channels", "Feedback channels and review cadence documented.", "Customer Owner"),
            ("Set satisfaction measures", "Satisfaction measure ownership and frequency defined.", "QMS Manager"),
        ],
        "evidence": [("Customer satisfaction record", "metric", "Customer feedback, satisfaction measurement, or performance summary.")],
    },
    {
        "code": "PM-QMP-KPI-001",
        "name": "Quality KPI System",
        "domain": "KPI & Performance Evaluation",
        "process_code": "PM-QMP-DOM-PERF",
        "category": "performance",
        "capability": "Objectives and KPIs",
        "objective": "Define quality measures that show whether processes and QMS outcomes are performing as intended.",
        "description": "Perfect Match method using existing KPI definitions, measurements, targets, trends, and schedules.",
        "activities": [
            ("Define KPI ownership", "KPI owners and data sources assigned.", "QMS Manager"),
            ("Configure measurement cadence", "Measurement frequency and target rules configured.", "Process Owner"),
        ],
        "evidence": [("KPI measurement record", "metric", "KPI definition and measurement records with status.")],
    },
    {
        "code": "PM-QMP-AUD-001",
        "name": "Internal Audit Program",
        "domain": "Internal Audit",
        "process_code": "PM-QMP-DOM-AUD",
        "category": "improvement",
        "capability": "Internal Audit",
        "objective": "Plan and execute internal audits that evaluate QMS implementation, process performance, and improvement needs.",
        "description": "Perfect Match method using the existing internal audit program, audit, evidence, and finding capabilities.",
        "activities": [
            ("Establish audit program", "Audit program scope and cadence defined.", "Audit Owner"),
            ("Assign audit responsibilities", "Auditor and reviewer responsibilities assigned.", "QMS Manager"),
        ],
        "evidence": [("Internal audit program record", "record", "Audit program, audit plan, evidence, or finding records.")],
    },
    {
        "code": "PM-QMP-MRV-001",
        "name": "Management Review Cycle",
        "domain": "Management Review",
        "process_code": "PM-QMP-DOM-MRV",
        "category": "governance",
        "capability": "Management Review",
        "objective": "Review QMS performance, risks, resources, audit results, customer feedback, supplier trends, and improvement actions with leadership.",
        "description": "Perfect Match method using the existing management review snapshot, decision, and action capabilities.",
        "activities": [
            ("Plan management review cycle", "Review frequency, participants, and inputs defined.", "Leadership Team"),
            ("Prepare review input sources", "Input sources assigned to data owners.", "QMS Manager"),
        ],
        "evidence": [("Management review record", "meeting", "Completed review record with inputs, decisions, and actions.")],
    },
    {
        "code": "PM-QMP-NCR-001",
        "name": "Nonconformity Management",
        "domain": "NCR",
        "process_code": "PM-QMP-DOM-NCR",
        "category": "improvement",
        "capability": "NCR",
        "objective": "Record, contain, investigate, verify, and close quality nonconformities through a controlled workflow.",
        "description": "Perfect Match method using the existing NCR module for operational execution.",
        "activities": [
            ("Define NCR reporting rules", "NCR reporting triggers and owners defined.", "QMS Manager"),
            ("Confirm verification responsibility", "NCR verification authority assigned.", "Process Owner"),
        ],
        "evidence": [("NCR workflow record", "record", "NCR record with containment, disposition, verification, or closure data.")],
    },
    {
        "code": "PM-QMP-RCA-001",
        "name": "Root Cause Analysis",
        "domain": "Root Cause",
        "process_code": "PM-QMP-DOM-CAPA",
        "category": "improvement",
        "capability": "CAPA",
        "objective": "Analyze recurring or significant quality issues to identify credible causes before assigning corrective action.",
        "description": "Perfect Match method using structured cause analysis inside the CAPA capability where appropriate.",
        "activities": [
            ("Define cause-analysis triggers", "Root cause trigger criteria documented.", "QMS Manager"),
            ("Document analysis method", "Cause analysis method and participants identified.", "CAPA Owner"),
        ],
        "evidence": [("Root cause analysis record", "record", "Cause analysis record linked to NCR, audit finding, risk, or CAPA.")],
    },
    {
        "code": "PM-QMP-CAPA-001",
        "name": "Corrective Action Effectiveness",
        "domain": "CAPA",
        "process_code": "PM-QMP-DOM-CAPA",
        "category": "improvement",
        "capability": "CAPA",
        "objective": "Plan, implement, verify, and review corrective actions for effectiveness before closure.",
        "description": "Perfect Match method using the existing CAPA header, action, cause, and effectiveness workflow.",
        "activities": [
            ("Define CAPA action planning", "CAPA action planning expectations documented.", "CAPA Owner"),
            ("Set effectiveness review criteria", "Effectiveness review criteria and timing assigned.", "QMS Manager"),
        ],
        "evidence": [("CAPA effectiveness record", "record", "CAPA action and effectiveness review records.")],
    },
    {
        "code": "PM-QMP-CI-001",
        "name": "Continual Improvement Pipeline",
        "domain": "Continual Improvement",
        "process_code": "PM-QMP-DOM-CI",
        "category": "improvement",
        "capability": "Improvement",
        "objective": "Maintain a visible pipeline of improvement inputs, actions, decisions, and results.",
        "description": "Perfect Match method for connecting risks, KPIs, audits, NCR, CAPA, customer feedback, and management review actions.",
        "activities": [
            ("Identify improvement sources", "Improvement input sources identified.", "QMS Manager"),
            ("Review improvement actions", "Improvement action review cadence defined.", "Leadership Team"),
        ],
        "evidence": [("Improvement action record", "record", "Improvement log, action list, CAPA, management review action, or KPI record.")],
    },
    {
        "code": "PM-QMP-DATA-001",
        "name": "Quality Data Integrity",
        "domain": "KPI & Performance Evaluation",
        "process_code": "PM-QMP-DOM-PERF",
        "category": "performance",
        "capability": "Performance Data",
        "objective": "Protect quality data used for decisions so it remains traceable, reviewable, and fit for operational use.",
        "description": "Perfect Match method for defining data owners, review points, corrections, and retention for quality records and metrics.",
        "activities": [
            ("Assign data owners", "Quality data owners and review points assigned.", "QMS Manager"),
            ("Define correction handling", "Data correction and retention approach documented.", "Process Owner"),
        ],
        "evidence": [("Quality data control record", "record", "Data ownership, correction, retention, or review record.")],
    },
]


def _find_or_create(env, model_name, domain, values):
    record = env[model_name].search(domain, limit=1)
    if record:
        return record
    return env[model_name].create(values)


def seed_quality_pack(env):
    company = env.ref("base.main_company")
    today = fields.Date.context_today(env["res.company"])
    organization = _find_or_create(
        env,
        "pm.qms.organization",
        [("code", "=", "PM-QMS-FRAMEWORK"), ("company_id", "=", company.id)],
        {
            "name": "Perfect Match QMS Framework Library",
            "code": "PM-QMS-FRAMEWORK",
            "description": "Perfect Match proprietary framework library for reusable QMS implementation controls.",
            "organization_kind": "framework",
            "company_id": company.id,
        },
    )

    process_by_code = {}
    for control_data in QUALITY_CONTROLS:
        process_code = control_data["process_code"]
        if process_code not in process_by_code:
            process_by_code[process_code] = _find_or_create(
                env,
                "pm.qms.process",
                [("code", "=", process_code), ("company_id", "=", company.id)],
                {
                    "name": control_data["domain"],
                    "code": process_code,
                    "organization_id": organization.id,
                    "company_id": company.id,
                    "process_type": "support",
                    "description": f"Perfect Match implementation domain: {control_data['domain']}.",
                },
            )

    controls = []
    for control_data in QUALITY_CONTROLS:
        control = env["pm.qms.control"].search(
            [("code", "=", control_data["code"]), ("company_id", "=", company.id)],
            limit=1,
        )
        if not control:
            control = env["pm.qms.control"].create(
                {
                    "name": control_data["name"],
                    "code": control_data["code"],
                    "objective": control_data["objective"],
                    "description": control_data["description"],
                    "process_id": process_by_code[control_data["process_code"]].id,
                    "category": control_data["category"],
                    "pm_control_domain": control_data["domain"],
                    "pm_supported_capability": control_data["capability"],
                    "state": "active",
                }
            )
        control.write(_quality_guidance_values(control_data))
        controls.append(control)
        for sequence, (name, expected_output, role) in enumerate(control_data["activities"], start=1):
            existing_activity = env["pm.qms.activity"].search(
                [("control_id", "=", control.id), ("name", "=", name)],
                limit=1,
            )
            if not existing_activity:
                env["pm.qms.activity"].create(
                    {
                        "control_id": control.id,
                        "sequence": sequence * 10,
                        "name": name,
                        "responsible_role": role,
                        "expected_output": expected_output,
                        "description": expected_output,
                    }
                )
        for sequence, (name, evidence_type, description) in enumerate(control_data["evidence"], start=1):
            definition_key = f"PM-QMS-EVID-{control_data['code']}"
            existing_requirement = _find_or_adopt_evidence_requirement(
                env, control, name, definition_key
            )
            values = {
                "control_id": control.id,
                "sequence": sequence * 10,
                "name": name,
                "definition_key": definition_key,
                "evidence_type": evidence_type,
                "description": description,
                "acceptance_criteria": _evidence_acceptance_criteria(evidence_type),
                "mandatory": True,
            }
            if existing_requirement:
                existing_requirement.write({
                    "definition_key": definition_key,
                    "acceptance_criteria": values["acceptance_criteria"],
                })
            else:
                env["pm.qms.evidence.requirement"].create(values)

    pack = env["pm.qms.framework.pack"].search(
        [
            ("code", "=", "PM-QMS-QUALITY"),
            ("version", "=", "1.0"),
            ("company_id", "=", company.id),
        ],
        limit=1,
    )
    if not pack:
        pack = env["pm.qms.framework.pack"].create(
            {
                "name": "Perfect Match Quality Management Pack",
                "code": "PM-QMS-QUALITY",
                "version": "1.0",
                "company_id": company.id,
                "description": "Perfect Match proprietary quality-management implementation pack with external reference mapping available as metadata.",
                "pack_type": "standard",
            }
        )
    if pack.state == "draft":
        existing_control_ids = set(pack.control_line_ids.mapped("control_id").ids)
        for sequence, control in enumerate(controls, start=1):
            if control.id not in existing_control_ids:
                env["pm.qms.framework.pack.control"].create(
                    {
                        "pack_id": pack.id,
                        "control_id": control.id,
                        "sequence": sequence * 10,
                        "required": True,
                    }
                )
        pack.action_activate()

    seed_quality_guided_readiness(env)

def seed_quality_guided_readiness(env):
    company = env.ref("base.main_company")
    pack = env["pm.qms.framework.pack"].search(
        [
            ("code", "=", "PM-QMS-QUALITY"),
            ("version", "=", "1.0"),
            ("company_id", "=", company.id),
        ],
        limit=1,
    )
    if not pack:
        return
    seed_env = env(context=dict(env.context, module="pm_qms_pack_quality"))
    pack = seed_env["pm.qms.framework.pack"].browse(pack.id)
    areas_by_code = {}
    for sequence, code, name, description in QUALITY_AREA_DEFINITIONS:
        area = seed_env["pm.qms.framework.area"].search([("pack_id", "=", pack.id), ("code", "=", code)], limit=1)
        values = {
            "name": name,
            "code": code,
            "pack_id": pack.id,
            "sequence": sequence,
            "description": description,
            "active": True,
        }
        if area:
            area.write(values)
        else:
            area = seed_env["pm.qms.framework.area"].create(values)
        areas_by_code[code] = area

    for sequence, control_data in enumerate(QUALITY_CONTROLS, start=1):
        control = seed_env["pm.qms.control"].search(
            [("code", "=", control_data["code"]), ("company_id", "=", company.id)],
            limit=1,
        )
        if not control:
            continue
        control.write(_quality_guidance_values(control_data))
        line = seed_env["pm.qms.framework.pack.control"].search(
            [("pack_id", "=", pack.id), ("control_id", "=", control.id)],
            limit=1,
        )
        area = areas_by_code[_quality_area_code(control_data)]
        if line:
            line.write({"area_id": area.id, "sequence": sequence * 10, "required": True, "active": True})

    projects = seed_env["pm.qms.implementation.project"].search(
        [
            ("company_id", "=", company.id),
            ("pack_ids", "in", [pack.id]),
            ("state", "not in", ("completed", "cancelled")),
        ]
    )
    for project in projects:
        project.sudo().action_sync_framework()
