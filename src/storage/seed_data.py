"""
VERITY Baseline Compliance Frameworks and Knowledge Ontologies Seeding
"""

import json
import logging
from src.storage.db import DatabaseManager

logger = logging.getLogger("verity.seed")


def seed_baseline_data_if_empty(db: DatabaseManager) -> None:
    """
    Ensures default compliance frameworks (SOC 2, ISO 27001) and baseline
    knowledge nodes exist in the database for immediate audit readiness.
    """
    # 1. Seed SOC 2
    soc2 = db.get_framework("SOC2")
    if not soc2:
        logger.info("Seeding baseline framework: SOC2")
        db.insert_framework(
            framework_id="SOC2",
            name="SOC 2 Trust Services Criteria",
            version="2026",
            description="AICPA SOC 2 Type II Security, Availability, and Confidentiality Criteria.",
        )
        requirements_soc2 = [
            (
                "soc2_cc61",
                "CC6.1",
                "Logical Access and Authentication",
                "The entity restricts logical access to registered personnel and enforces multi-factor authentication (MFA).",
                "Access Control",
                1,
            ),
            (
                "soc2_cc66",
                "CC6.6",
                "Boundary Protection & Encryption",
                "The entity implements logical boundary controls, firewalls, and cryptographic protection at rest and in transit.",
                "Cryptography",
                1,
            ),
            (
                "soc2_cc67",
                "CC6.7",
                "Transmission Security",
                "The entity restricts data transmission to secure channels utilizing TLS 1.2 or higher protocols.",
                "Network Security",
                2,
            ),
            (
                "soc2_cc71",
                "CC7.1",
                "Vulnerability Detection & Management",
                "The entity maintains automated vulnerability scanning, vulnerability remediation, and annual penetration testing.",
                "Vulnerability Management",
                2,
            ),
            (
                "soc2_cc81",
                "CC8.1",
                "Change Management Authorization",
                "The entity authorizes, designs, develops or acquires, configures, tests, approves, and implements changes.",
                "Change Management",
                2,
            ),
        ]
        for req_id, code, title, desc, cat, sev in requirements_soc2:
            db.insert_requirement(
                req_id=req_id,
                framework_id="SOC2",
                req_code=code,
                title=title,
                description=desc,
                category=cat,
                severity_level=sev,
            )

    # 2. Seed ISO 27001
    iso = db.get_framework("ISO27001")
    if not iso:
        logger.info("Seeding baseline framework: ISO27001")
        db.insert_framework(
            framework_id="ISO27001",
            name="ISO/IEC 27001:2022",
            version="2022",
            description="International standard for information security management systems (ISMS).",
        )
        requirements_iso = [
            (
                "iso_a92",
                "A.9.2",
                "User Access Provisioning",
                "A formal user registration and de-registration process shall be implemented for granting and revoking access.",
                "Access Control",
                1,
            ),
            (
                "iso_a101",
                "A.10.1",
                "Cryptographic Controls",
                "A policy on the use of cryptographic controls for protection of information shall be developed and implemented.",
                "Cryptography",
                1,
            ),
            (
                "iso_a121",
                "A.12.1",
                "Operational Procedures & Responsibilities",
                "Operating procedures shall be documented and made available to all users who need them.",
                "Operations Security",
                2,
            ),
            (
                "iso_a126",
                "A.12.6",
                "Management of Technical Vulnerabilities",
                "Information about technical vulnerabilities of information systems being used shall be obtained in a timely fashion.",
                "Vulnerability Management",
                2,
            ),
        ]
        for req_id, code, title, desc, cat, sev in requirements_iso:
            db.insert_requirement(
                req_id=req_id,
                framework_id="ISO27001",
                req_code=code,
                title=title,
                description=desc,
                category=cat,
                severity_level=sev,
            )

    # 3. Seed Baseline Knowledge Graph Nodes
    default_nodes = [
        (
            "logical-access-control",
            "Logical Access Control Standard",
            "control",
            (
                "# Logical Access Control Standard\n\n"
                "Defines mandatory multi-factor authentication (MFA) and RBAC segregation across all corporate systems.\n\n"
                "Related controls: [[soc2-cc6.1]] and [[mfa-policy]]."
            ),
            {"framework": "SOC2", "category": "Access Control"},
        ),
        (
            "soc2-cc6.1",
            "SOC 2 CC6.1 Control Specification",
            "requirement",
            (
                "# SOC 2 CC6.1 Control Specification\n\n"
                "Requires strict credential hygiene, automated deprovisioning, and FIDO2 MFA enforcement.\n\n"
                "Implemented by [[logical-access-control]]."
            ),
            {"framework": "SOC2", "category": "Compliance"},
        ),
        (
            "mfa-policy",
            "Multi-Factor Authentication Policy",
            "document",
            (
                "# Multi-Factor Authentication Policy\n\n"
                "All remote and administrative access requires hardware security keys or authenticator apps.\n\n"
                "Referenced in [[logical-access-control]] and [[iso-27001-a.9]]."
            ),
            {"framework": "Enterprise Standard", "category": "Policy"},
        ),
        (
            "incident-response-plan",
            "Security Incident Response Plan",
            "document",
            (
                "# Security Incident Response Plan\n\n"
                "Procedures for reporting, containing, eradicating, and recovering from cybersecurity incidents.\n\n"
                "Linked to [[soc2-cc7.1]]."
            ),
            {"framework": "SOC2", "category": "Operations"},
        ),
        (
            "iso-27001-a.9",
            "ISO 27001 Annex A.9 Access Control",
            "requirement",
            (
                "# ISO 27001 Annex A.9 Access Control\n\n"
                "Ensures business requirements for access control are established and documented.\n\n"
                "Cross-referenced with [[mfa-policy]] and [[logical-access-control]]."
            ),
            {"framework": "ISO27001", "category": "Access Control"},
        ),
    ]

    for slug, title, ntype, content, fm in default_nodes:
        existing = db.get_knowledge_node(slug)
        if not existing:
            db.insert_knowledge_node(
                node_id=f"node_{slug.replace('-', '_')}",
                slug=slug,
                title=title,
                node_type=ntype,
                content_markdown=content,
                frontmatter_json=json.dumps(fm),
            )

    logger.info("Baseline frameworks and knowledge graph seeding verified.")
