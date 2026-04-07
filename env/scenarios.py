"""
Compliance Review Scenarios — Realistic business documents with embedded
regulatory violations (and compliant sections) for grading.

Difficulty tiers:
  EASY   — One document, one regulation domain, obvious violations
  MEDIUM — Two documents, cross-referencing needed, subtle violations
  HARD   — Multiple docs, multiple regulation domains, ambiguous clauses,
           some compliant sections that look suspicious (traps for false positives)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class GroundTruthViolation:
    """A known violation embedded in the scenario for grading."""
    section_id: str
    regulation_id: str
    severity: str
    description: str
    keywords: List[str] = field(default_factory=list)


@dataclass
class Scenario:
    """Full compliance review scenario definition."""
    task_id: str
    title: str
    difficulty: str
    description: str
    task_prompt: str

    # Documents under review
    documents: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # doc_id -> { "type", "title", "parties", "date", "sections": {sec_id -> {"title","content","page"}} }

    # Applicable regulations
    regulations: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # reg_id -> { "domain", "title", "description", "requirement", "severity", "keywords", ... }

    # Ground truth
    ground_truth_violations: List[GroundTruthViolation] = field(default_factory=list)
    expected_overall_status: str = "non_compliant"

    max_steps: int = 20
    hints: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# EASY: Privacy Policy missing GDPR requirements
# ═══════════════════════════════════════════════════════════════════════════

EASY_SCENARIO = Scenario(
    task_id="easy_privacy_review",
    title="Privacy Policy Compliance Review",
    difficulty="easy",
    description="Review a company's privacy policy against data protection regulations.",
    task_prompt=(
        "You are a compliance analyst at a consulting firm. Your client, ShopFast Inc., "
        "has asked you to review their customer-facing privacy policy against applicable "
        "data privacy regulations before they launch in the EU market. "
        "Read the policy, check each applicable regulation, flag any violations, "
        "and submit your review."
    ),
    documents={
        "privacy_policy_001": {
            "type": "privacy_policy",
            "title": "ShopFast Inc. — Customer Privacy Policy",
            "parties": ["ShopFast Inc.", "Customers"],
            "date": "2025-09-15",
            "summary": "Customer-facing privacy policy for e-commerce platform",
            "sections": {
                "sec_purpose": {
                    "title": "1. Purpose and Scope",
                    "content": (
                        "This Privacy Policy describes how ShopFast Inc. ('we', 'us') collects, "
                        "uses, and shares personal information when you use our e-commerce platform. "
                        "This policy applies to all users of shopfast.com and our mobile applications."
                    ),
                    "page": 1,
                },
                "sec_collection": {
                    "title": "2. Information We Collect",
                    "content": (
                        "We collect the following personal data: full name, email address, "
                        "shipping address, phone number, payment card details, browsing history, "
                        "purchase history, device identifiers, IP address, and location data. "
                        "We may also collect biometric data from our facial recognition login feature. "
                        "Data is collected automatically when you visit our site through cookies "
                        "and similar tracking technologies."
                    ),
                    "page": 1,
                },
                "sec_usage": {
                    "title": "3. How We Use Your Information",
                    "content": (
                        "We use your personal information for: processing orders, personalizing "
                        "your shopping experience, sending marketing communications, improving our "
                        "services, fraud prevention, and sharing with our advertising partners "
                        "to show you relevant ads across the internet. We may also use your data "
                        "for automated decision-making, including credit scoring for our Buy Now "
                        "Pay Later service."
                    ),
                    "page": 2,
                },
                "sec_sharing": {
                    "title": "4. Data Sharing",
                    "content": (
                        "We share your personal data with: payment processors, shipping carriers, "
                        "our advertising partners (Google, Meta, TikTok), data brokers for "
                        "analytics enrichment, our parent company GlobalRetail Corp and all its "
                        "subsidiaries worldwide, and any third party as we deem necessary for "
                        "business purposes. We do not sell your data, but we do share it "
                        "for targeted advertising which may constitute a 'sale' under certain laws."
                    ),
                    "page": 2,
                },
                "sec_retention": {
                    "title": "5. Data Retention",
                    "content": (
                        "We retain your personal data for as long as necessary to fulfill the "
                        "purposes described in this policy, or as required by law."
                    ),
                    "page": 3,
                },
                "sec_rights": {
                    "title": "6. Your Rights",
                    "content": (
                        "You may request access to your data by emailing privacy@shopfast.com. "
                        "We will respond within a reasonable timeframe."
                    ),
                    "page": 3,
                },
                "sec_security": {
                    "title": "7. Security",
                    "content": (
                        "We use industry-standard security measures to protect your data."
                    ),
                    "page": 3,
                },
                "sec_changes": {
                    "title": "8. Changes to This Policy",
                    "content": (
                        "We may update this policy at any time. Continued use of our services "
                        "constitutes acceptance of the updated policy."
                    ),
                    "page": 3,
                },
            },
        },
    },
    regulations={
        "REG-DP-001": {
            "domain": "data_privacy",
            "title": "Lawful Basis for Processing",
            "description": "Organizations must establish and document a lawful basis for processing personal data.",
            "requirement": (
                "The privacy policy must clearly state the legal basis for each type of data processing "
                "(e.g., consent, legitimate interest, contractual necessity). Collecting biometric data "
                "requires explicit consent. Automated decision-making must disclose logic and allow opt-out."
            ),
            "severity": "critical",
            "keywords": ["lawful basis", "legal basis", "consent", "legitimate interest", "biometric"],
            "examples_of_compliance": "We process your data based on: (a) your consent for marketing, (b) contractual necessity for orders...",
            "examples_of_violation": "Policy lists data collection and uses but never states the legal basis for any processing activity.",
        },
        "REG-DP-002": {
            "domain": "data_privacy",
            "title": "Data Subject Rights",
            "description": "Individuals must be informed of their full rights regarding their personal data.",
            "requirement": (
                "The policy must enumerate all data subject rights: right of access, rectification, "
                "erasure ('right to be forgotten'), restriction of processing, data portability, "
                "objection to processing, and rights related to automated decision-making. "
                "Must provide a clear mechanism to exercise each right and specify response timeframe (max 30 days)."
            ),
            "severity": "major",
            "keywords": ["right to access", "erasure", "portability", "rectification", "objection", "30 days"],
            "examples_of_compliance": "You have the right to: (1) access your data, (2) correct inaccurate data, (3) request deletion...",
            "examples_of_violation": "Only mentions 'you can email us' without listing specific rights or response timeline.",
        },
        "REG-DP-003": {
            "domain": "data_privacy",
            "title": "Data Retention Limits",
            "description": "Data must not be retained longer than necessary. Specific retention periods must be stated.",
            "requirement": (
                "The policy must specify concrete retention periods for each category of personal data, "
                "or the criteria used to determine retention. Vague statements like 'as long as necessary' "
                "are insufficient."
            ),
            "severity": "major",
            "keywords": ["retention period", "how long", "deleted after", "specific period"],
            "examples_of_compliance": "We retain purchase history for 7 years for tax compliance, account data for 2 years after closure...",
            "examples_of_violation": "We retain data 'as long as necessary' or 'as required by law' with no specifics.",
        },
        "REG-DP-004": {
            "domain": "data_privacy",
            "title": "Third-Party Data Sharing Transparency",
            "description": "All third-party data recipients must be identified with specific purpose for sharing.",
            "requirement": (
                "The policy must identify specific categories of third-party recipients, the purpose "
                "of each sharing arrangement, and whether data is transferred outside the jurisdiction. "
                "Blanket statements about sharing with 'business partners' or 'as we deem necessary' "
                "are non-compliant. Data broker sharing must be explicitly disclosed."
            ),
            "severity": "critical",
            "keywords": ["third party", "data broker", "transfer", "purpose of sharing", "jurisdiction"],
            "examples_of_compliance": "We share order data with FedEx for shipping, payment data with Stripe for processing...",
            "examples_of_violation": "Shares with 'any third party as we deem necessary for business purposes'.",
        },
        "REG-DP-005": {
            "domain": "data_privacy",
            "title": "Breach Notification Commitment",
            "description": "Policy must include commitment to notify affected individuals in case of a data breach.",
            "requirement": (
                "The policy MUST contain a data breach notification clause — check every section. "
                "If NO section mentions breach notification, that is a violation against the section "
                "that covers security (typically the security section). Required elements: "
                "notify affected individuals and supervisory authority within 72 hours, "
                "describe the notification process. ABSENCE of this clause = violation."
            ),
            "severity": "major",
            "keywords": ["breach", "notification", "72 hours", "supervisory authority"],
            "examples_of_compliance": "In the event of a data breach, we will notify affected users within 72 hours...",
            "examples_of_violation": "No mention of breach notification at all in the policy.",
        },
    },
    ground_truth_violations=[
        GroundTruthViolation(
            section_id="sec_collection",
            regulation_id="REG-DP-001",
            severity="critical",
            description="Biometric data (facial recognition) collected without stating explicit consent as legal basis. "
                        "No lawful basis stated for any processing activity.",
            keywords=["biometric", "consent", "lawful basis", "legal basis", "facial"],
        ),
        GroundTruthViolation(
            section_id="sec_usage",
            regulation_id="REG-DP-001",
            severity="major",
            description="Automated decision-making (credit scoring) disclosed but no opt-out mechanism or logic explanation provided.",
            keywords=["automated", "decision", "credit", "opt-out", "scoring"],
        ),
        GroundTruthViolation(
            section_id="sec_rights",
            regulation_id="REG-DP-002",
            severity="major",
            description="Only mentions right of access via email. Missing: rectification, erasure, portability, "
                        "restriction, objection rights. No response timeframe specified.",
            keywords=["rights", "erasure", "portability", "rectification", "30 days"],
        ),
        GroundTruthViolation(
            section_id="sec_retention",
            regulation_id="REG-DP-003",
            severity="major",
            description="Retention policy uses vague 'as long as necessary' language. No specific retention periods "
                        "for any data category.",
            keywords=["retention", "as long as necessary", "specific", "period"],
        ),
        GroundTruthViolation(
            section_id="sec_sharing",
            regulation_id="REG-DP-004",
            severity="critical",
            description="Shares data with 'data brokers' and 'any third party as we deem necessary' — "
                        "blanket sharing without specific purpose. No mention of cross-border transfers.",
            keywords=["data broker", "any third party", "deem necessary", "transfer"],
        ),
        GroundTruthViolation(
            section_id="sec_security",
            regulation_id="REG-DP-005",
            severity="major",
            description="No breach notification commitment anywhere in the policy. Missing 72-hour notification requirement.",
            keywords=["breach", "notification", "72 hours"],
        ),
    ],
    expected_overall_status="non_compliant",
    max_steps=20,
    hints=[
        "Start by reading the full document to understand its structure.",
        "Then read each applicable regulation to know what to check for.",
        "Check each document section against relevant regulations.",
        "Be efficient — flag violations as you find them, don't re-read regulations.",
    ],
)


# ═══════════════════════════════════════════════════════════════════════════
# MEDIUM: Loan application with fair lending + KYC violations
# ═══════════════════════════════════════════════════════════════════════════

MEDIUM_SCENARIO = Scenario(
    task_id="medium_lending_review",
    title="Loan Application Compliance Review",
    difficulty="medium",
    description="Review a loan application package against fair lending and KYC/AML regulations.",
    task_prompt=(
        "You are a compliance officer at SecureBank. Review a small-business loan application "
        "from QuickBuild Construction LLC. The package includes the loan application form and "
        "the bank's internal lending policy. Check both documents against fair lending and "
        "KYC/AML regulations. Some violations span across documents — you'll need to "
        "cross-reference to find them."
    ),
    documents={
        "loan_app_001": {
            "type": "loan_application",
            "title": "Small Business Loan Application — QuickBuild Construction LLC",
            "parties": ["QuickBuild Construction LLC", "SecureBank"],
            "date": "2026-02-20",
            "summary": "Application for $450,000 commercial construction loan",
            "sections": {
                "sec_borrower": {
                    "title": "1. Borrower Information",
                    "content": (
                        "Business Name: QuickBuild Construction LLC\n"
                        "Owner: Rajesh Patel\n"
                        "Business Address: 1847 Industrial Pkwy, Houston, TX 77032\n"
                        "Years in Business: 8\n"
                        "Annual Revenue: $2.1M\n"
                        "Number of Employees: 23\n"
                        "Owner Ethnicity: South Asian (noted by loan officer)\n"
                        "Owner Religion: Hindu (noted by loan officer)\n"
                        "Neighborhood Classification: Zone C (High-Risk per internal matrix)"
                    ),
                    "page": 1,
                },
                "sec_financials": {
                    "title": "2. Financial Summary",
                    "content": (
                        "Requested Amount: $450,000\n"
                        "Purpose: Equipment purchase and working capital\n"
                        "Collateral: Construction equipment valued at $380,000\n"
                        "Current Debt: $120,000 (equipment lease)\n"
                        "Credit Score: 742\n"
                        "Debt-to-Income Ratio: 28%\n"
                        "Proposed Interest Rate: 11.2% (Prime + 5.7%)\n"
                        "Standard rate for similar risk profile: 7.5% (Prime + 2.0%)\n"
                        "Loan Officer Note: 'Applied Zone C risk premium per internal policy.'"
                    ),
                    "page": 2,
                },
                "sec_identity": {
                    "title": "3. Identity Verification",
                    "content": (
                        "ID Provided: Texas Driver's License\n"
                        "ID Number: [RECORDED]\n"
                        "SSN: [RECORDED]\n"
                        "Verification Status: 'Visual check performed. Docs look okay.'\n"
                        "PEP Screening: Not performed\n"
                        "Sanctions List Check: Not performed\n"
                        "Source of Funds: Not documented"
                    ),
                    "page": 3,
                },
                "sec_decision": {
                    "title": "4. Loan Decision",
                    "content": (
                        "Decision: APPROVED WITH CONDITIONS\n"
                        "Conditions: Additional 2% risk surcharge for Zone C location.\n"
                        "Final Rate: 11.2%\n"
                        "Loan Officer: James Thompson\n"
                        "Approval Note: 'Good financials but location and demographic risk warrant premium.'"
                    ),
                    "page": 3,
                },
            },
        },
        "lending_policy_001": {
            "type": "employee_handbook",
            "title": "SecureBank Internal Lending Policy v4.2",
            "parties": ["SecureBank"],
            "date": "2025-06-01",
            "summary": "Internal policy governing commercial lending decisions",
            "sections": {
                "sec_lp_zones": {
                    "title": "Section 3.4 — Geographic Risk Zones",
                    "content": (
                        "SecureBank classifies lending areas into Zones A, B, and C based on "
                        "historical default rates and property values.\n\n"
                        "Zone A: Default rate <2%, standard pricing.\n"
                        "Zone B: Default rate 2-5%, +1% premium.\n"
                        "Zone C: Default rate >5%, +3-6% premium. Zone C areas include: "
                        "ZIP codes 77032, 77033, 77034, 77078, 77016.\n\n"
                        "Note: Zone C areas are predominantly minority-populated neighborhoods "
                        "per latest census data. The correlation between Zone C and minority "
                        "population exceeds 85%."
                    ),
                    "page": 8,
                },
                "sec_lp_kyc": {
                    "title": "Section 5.1 — Customer Due Diligence",
                    "content": (
                        "For all commercial loans above $50,000:\n"
                        "- Verify identity via government-issued photo ID\n"
                        "- Perform PEP (Politically Exposed Person) screening\n"
                        "- Check OFAC sanctions list\n"
                        "- Document source of funds for amounts exceeding $100,000\n"
                        "- File CTR for cash transactions over $10,000\n\n"
                        "Note: Expedited processing available for 'preferred customers' "
                        "at branch manager discretion — KYC steps may be abbreviated."
                    ),
                    "page": 12,
                },
                "sec_lp_pricing": {
                    "title": "Section 4.1 — Loan Pricing",
                    "content": (
                        "Standard pricing: Prime rate + risk margin based on credit score:\n"
                        "- Credit score 750+: Prime + 1.5%\n"
                        "- Credit score 700-749: Prime + 2.0%\n"
                        "- Credit score 650-699: Prime + 3.5%\n"
                        "- Credit score <650: Prime + 5.0%\n\n"
                        "Geographic premiums are additive per Section 3.4."
                    ),
                    "page": 10,
                },
            },
        },
    },
    regulations={
        "REG-FL-001": {
            "domain": "lending",
            "title": "Prohibition on Discriminatory Lending (Fair Lending)",
            "description": "Lending decisions must not discriminate based on race, ethnicity, religion, national origin, or neighborhood demographics.",
            "requirement": (
                "Loan pricing, terms, and approval decisions must be based solely on creditworthiness, "
                "collateral, and financial risk factors. Geographic risk zones that serve as proxies for "
                "racial or ethnic composition (redlining) are prohibited. Recording applicant ethnicity or "
                "religion in decision notes is a prohibited practice. Any pricing disparity must be "
                "justified by objective financial risk factors alone."
            ),
            "severity": "critical",
            "keywords": ["discrimination", "redlining", "ethnicity", "race", "religion", "proxy", "disparate impact"],
        },
        "REG-AML-001": {
            "domain": "aml_kyc",
            "title": "Customer Due Diligence Requirements",
            "description": "Financial institutions must perform adequate KYC checks on all customers.",
            "requirement": (
                "For commercial loans above $50,000: identity must be verified against government databases "
                "(not just visual inspection), PEP screening must be performed and documented, OFAC sanctions "
                "list must be checked, and source of funds must be documented for amounts over $100,000. "
                "No exceptions or abbreviations permitted regardless of customer status."
            ),
            "severity": "critical",
            "keywords": ["KYC", "PEP", "sanctions", "OFAC", "source of funds", "due diligence"],
        },
        "REG-AML-002": {
            "domain": "aml_kyc",
            "title": "Prohibition on Abbreviated Due Diligence",
            "description": "KYC procedures cannot be waived or abbreviated for any customer class.",
            "requirement": (
                "All KYC steps are mandatory. Internal policies that allow 'expedited' or 'abbreviated' "
                "KYC for preferred customers violate anti-money-laundering regulations. Any such policy "
                "provision must be flagged."
            ),
            "severity": "major",
            "keywords": ["expedited", "abbreviated", "waived", "preferred", "exception"],
        },
        "REG-FL-002": {
            "domain": "lending",
            "title": "Pricing Justification Requirements",
            "description": "Any deviation from standard pricing must be justified with objective financial criteria.",
            "requirement": (
                "If the offered rate exceeds the standard rate for the applicant's credit profile, "
                "the lender must document specific, objective financial risk factors justifying the premium. "
                "Geographic location alone is not sufficient justification if the zone classification "
                "correlates with protected demographic characteristics."
            ),
            "severity": "critical",
            "keywords": ["rate", "premium", "justification", "standard rate", "deviation", "objective"],
        },
    },
    ground_truth_violations=[
        GroundTruthViolation(
            section_id="sec_borrower",
            regulation_id="REG-FL-001",
            severity="critical",
            description="Loan officer recorded applicant ethnicity ('South Asian') and religion ('Hindu') "
                        "in the application — prohibited data collection for lending decisions.",
            keywords=["ethnicity", "religion", "prohibited", "discrimination"],
        ),
        GroundTruthViolation(
            section_id="sec_decision",
            regulation_id="REG-FL-001",
            severity="critical",
            description="Approval note references 'demographic risk' as factor in pricing premium — "
                        "explicit use of protected characteristics in lending decision.",
            keywords=["demographic", "risk", "premium", "decision"],
        ),
        GroundTruthViolation(
            section_id="sec_lp_zones",
            regulation_id="REG-FL-001",
            severity="critical",
            description="Zone C classification correlates >85% with minority neighborhoods — "
                        "geographic pricing is a proxy for racial discrimination (redlining).",
            keywords=["zone c", "minority", "redlining", "proxy", "correlation"],
        ),
        GroundTruthViolation(
            section_id="sec_financials",
            regulation_id="REG-FL-002",
            severity="critical",
            description="Rate of 11.2% is 3.7% above standard rate for credit score 742. "
                        "Only justification is Zone C premium, which is a demographic proxy.",
            keywords=["rate", "11.2", "premium", "zone c", "standard", "7.5"],
        ),
        GroundTruthViolation(
            section_id="sec_identity",
            regulation_id="REG-AML-001",
            severity="critical",
            description="Identity verification was 'visual check' only — not verified against government databases. "
                        "PEP screening not performed. Sanctions list not checked. "
                        "Source of funds not documented for $450K loan.",
            keywords=["visual check", "PEP", "sanctions", "source of funds", "not performed"],
        ),
        GroundTruthViolation(
            section_id="sec_lp_kyc",
            regulation_id="REG-AML-002",
            severity="major",
            description="Internal policy allows 'abbreviated' KYC for preferred customers — "
                        "this exception violates AML requirements.",
            keywords=["expedited", "abbreviated", "preferred", "exception"],
        ),
    ],
    expected_overall_status="non_compliant",
    max_steps=20,
    hints=[
        "This task requires cross-referencing between the loan application and the internal policy.",
        "Look at both the application data AND the policy provisions for issues.",
        "Pay attention to how pricing was determined — compare offered rate to standard rate.",
    ],
)


# ═══════════════════════════════════════════════════════════════════════════
# HARD: Vendor data processing agreement with GDPR + consumer protection
#       issues, PLUS some compliant sections that look suspicious (traps)
# ═══════════════════════════════════════════════════════════════════════════

HARD_SCENARIO = Scenario(
    task_id="hard_vendor_dpa_review",
    title="Vendor Data Processing Agreement — Multi-Regulation Review",
    difficulty="hard",
    description=(
        "Review a data processing agreement with a third-party analytics vendor, "
        "the vendor's sub-processor list, and a related marketing consent form. "
        "Multiple regulation domains apply. Some clauses are deliberately ambiguous — "
        "some are actually compliant despite looking suspicious."
    ),
    task_prompt=(
        "You are senior compliance counsel at MediCare Plus, a health insurance company. "
        "Your firm is about to sign a data processing agreement with AnalyticsPro Ltd., "
        "a third-party analytics vendor who will process policyholder data for fraud detection. "
        "Review the DPA, sub-processor list, and marketing consent form against data privacy "
        "AND consumer protection regulations. Be precise — flag real violations but do NOT "
        "flag compliant clauses as violations. Your accuracy matters."
    ),
    documents={
        "dpa_001": {
            "type": "data_processing_agreement",
            "title": "Data Processing Agreement — MediCare Plus & AnalyticsPro Ltd.",
            "parties": ["MediCare Plus", "AnalyticsPro Ltd."],
            "date": "2026-03-01",
            "summary": "Agreement for processing policyholder data for fraud analytics",
            "sections": {
                "sec_dpa_scope": {
                    "title": "1. Scope of Processing",
                    "content": (
                        "AnalyticsPro shall process personal data of MediCare Plus policyholders "
                        "solely for the purpose of insurance fraud detection and prevention. "
                        "Data categories include: policyholder names, policy numbers, claim history, "
                        "medical diagnosis codes (ICD-10), treatment records, prescription data, "
                        "and provider information."
                    ),
                    "page": 1,
                },
                "sec_dpa_subprocessors": {
                    "title": "2. Sub-Processors",
                    "content": (
                        "AnalyticsPro may engage sub-processors to assist in data processing. "
                        "A current list of sub-processors is maintained at analyticspro.com/sub-processors "
                        "and updated quarterly. MediCare Plus will be notified of changes via email "
                        "within 30 days of any new sub-processor being engaged. MediCare Plus may "
                        "object to any new sub-processor within 14 days of notification."
                    ),
                    "page": 2,
                },
                "sec_dpa_transfers": {
                    "title": "3. International Data Transfers",
                    "content": (
                        "Data may be transferred to AnalyticsPro's processing centers in the EU, "
                        "United States, and India. For transfers outside the EU, AnalyticsPro relies "
                        "on 'internal corporate policies' as the transfer mechanism. No Standard "
                        "Contractual Clauses (SCCs) or adequacy decisions are referenced."
                    ),
                    "page": 2,
                },
                "sec_dpa_security": {
                    "title": "4. Security Measures",
                    "content": (
                        "AnalyticsPro implements appropriate technical and organizational measures "
                        "including: encryption at rest (AES-256), encryption in transit (TLS 1.3), "
                        "role-based access control, annual penetration testing by independent auditors, "
                        "SOC 2 Type II certification, and 24/7 security monitoring. "
                        "Incident response plan with 48-hour breach notification to controller."
                    ),
                    "page": 3,
                },
                "sec_dpa_retention": {
                    "title": "5. Data Retention and Deletion",
                    "content": (
                        "Processed data shall be retained for 24 months after the analysis is complete. "
                        "Upon contract termination, AnalyticsPro shall delete all personal data within "
                        "90 days, unless retention is required by applicable law. AnalyticsPro shall "
                        "provide certification of deletion upon request."
                    ),
                    "page": 3,
                },
                "sec_dpa_liability": {
                    "title": "6. Liability and Indemnification",
                    "content": (
                        "AnalyticsPro's total aggregate liability under this agreement shall not "
                        "exceed the fees paid by MediCare Plus in the 12 months preceding the claim. "
                        "AnalyticsPro shall not be liable for any indirect, consequential, or "
                        "punitive damages, including regulatory fines imposed on MediCare Plus."
                    ),
                    "page": 4,
                },
                "sec_dpa_purpose_limitation": {
                    "title": "7. Purpose Limitation",
                    "content": (
                        "AnalyticsPro shall process data only for the purposes specified in Section 1. "
                        "However, AnalyticsPro reserves the right to use anonymized and aggregated "
                        "data derived from the processing for product improvement, benchmarking, "
                        "and marketing of AnalyticsPro services."
                    ),
                    "page": 4,
                },
            },
        },
        "subprocessor_list": {
            "type": "vendor_agreement",
            "title": "AnalyticsPro Sub-Processor List (Q1 2026)",
            "parties": ["AnalyticsPro Ltd."],
            "date": "2026-01-15",
            "summary": "Current list of sub-processors used by AnalyticsPro",
            "sections": {
                "sec_sp_list": {
                    "title": "Active Sub-Processors",
                    "content": (
                        "1. CloudStore Inc. (USA) — Cloud infrastructure and storage\n"
                        "2. DataVault Systems (Ireland) — Encrypted backup and disaster recovery\n"
                        "3. InsightML Corp (India) — Machine learning model training and inference\n"
                        "4. QuickTranslate Ltd (China) — Medical terminology translation services\n"
                        "5. MarketBoost LLC (USA) — 'Analytics dashboard and reporting'\n\n"
                        "Note: MarketBoost LLC is a subsidiary of AnalyticsPro Ltd."
                    ),
                    "page": 1,
                },
            },
        },
        "consent_form_001": {
            "type": "contract",
            "title": "MediCare Plus — Policyholder Data Usage Consent Form",
            "parties": ["MediCare Plus", "Policyholders"],
            "date": "2025-11-01",
            "summary": "Consent form presented to policyholders for data processing",
            "sections": {
                "sec_consent_text": {
                    "title": "Consent Statement",
                    "content": (
                        "By signing below, I consent to MediCare Plus sharing my personal and "
                        "medical information with its service providers for claim processing, "
                        "fraud prevention, and service improvement purposes. I understand that "
                        "my data may be shared with third-party partners and their affiliates. "
                        "This consent cannot be withdrawn after claim submission."
                    ),
                    "page": 1,
                },
                "sec_consent_scope": {
                    "title": "Scope of Consent",
                    "content": (
                        "This consent covers: processing of medical records including diagnosis codes, "
                        "treatment history, prescription data, and provider information. Data may be "
                        "used for analytics, fraud detection, service optimization, and marketing of "
                        "related insurance products. Data may be transferred internationally."
                    ),
                    "page": 1,
                },
            },
        },
    },
    regulations={
        "REG-DP-010": {
            "domain": "data_privacy",
            "title": "International Transfer Safeguards",
            "description": "Personal data transfers outside the originating jurisdiction require adequate safeguards.",
            "requirement": (
                "Transfers of personal data to countries without an adequacy decision must be protected "
                "by Standard Contractual Clauses (SCCs), Binding Corporate Rules (BCRs), or another "
                "recognized mechanism. 'Internal corporate policies' alone are not a valid transfer mechanism."
            ),
            "severity": "critical",
            "keywords": ["SCC", "adequacy", "transfer", "BCR", "safeguard", "mechanism"],
        },
        "REG-DP-011": {
            "domain": "data_privacy",
            "title": "Purpose Limitation for Processors",
            "description": "Data processors may only process data for purposes specified by the controller.",
            "requirement": (
                "A processor must not use personal data for its own purposes, even if anonymized or aggregated, "
                "unless the controller has given explicit written authorization. Using derived data for "
                "'product improvement' or 'marketing' without explicit controller consent is a violation."
            ),
            "severity": "major",
            "keywords": ["purpose limitation", "processor", "own purposes", "anonymized", "derived"],
        },
        "REG-DP-012": {
            "domain": "data_privacy",
            "title": "Sub-Processor Due Diligence",
            "description": "Controllers must have visibility into the full processing chain.",
            "requirement": (
                "Sub-processor lists must clearly state the processing purpose for each sub-processor. "
                "Vague descriptions are insufficient. Controllers must be able to assess whether each "
                "sub-processor's access is necessary and proportionate."
            ),
            "severity": "major",
            "keywords": ["sub-processor", "purpose", "proportionate", "necessary"],
        },
        "REG-CP-001": {
            "domain": "consumer_protection",
            "title": "Withdrawal of Consent",
            "description": "Consumers must be able to withdraw consent at any time.",
            "requirement": (
                "Consent for data processing must be freely given and withdrawable at any time. "
                "Statements that consent 'cannot be withdrawn' after a certain action are invalid. "
                "Withdrawal must be as easy as giving consent."
            ),
            "severity": "critical",
            "keywords": ["withdraw", "consent", "freely given", "cannot be withdrawn"],
        },
        "REG-CP-002": {
            "domain": "consumer_protection",
            "title": "Consent Specificity",
            "description": "Consent must be specific to each processing purpose.",
            "requirement": (
                "Bundled consent (single checkbox for multiple unrelated purposes like fraud detection "
                "AND marketing) is not valid. Each distinct processing purpose requires separate, "
                "granular consent."
            ),
            "severity": "major",
            "keywords": ["bundled", "specific", "granular", "separate consent", "purpose"],
        },
        "REG-DP-013": {
            "domain": "data_privacy",
            "title": "Processor Liability for Regulatory Fines",
            "description": "Processors cannot contractually exclude liability for fines resulting from their actions.",
            "requirement": (
                "Contractual clauses that exclude processor liability for regulatory fines imposed on "
                "the controller due to the processor's breach are unenforceable and indicate inadequate "
                "data protection commitment."
            ),
            "severity": "major",
            "keywords": ["liability", "fines", "exclude", "indemnification", "regulatory"],
        },
    },
    ground_truth_violations=[
        GroundTruthViolation(
            section_id="sec_dpa_transfers",
            regulation_id="REG-DP-010",
            severity="critical",
            description="International transfers to US and India rely on 'internal corporate policies' — "
                        "not a valid transfer mechanism. No SCCs or BCRs referenced.",
            keywords=["internal corporate policies", "SCC", "transfer", "India", "United States"],
        ),
        GroundTruthViolation(
            section_id="sec_dpa_purpose_limitation",
            regulation_id="REG-DP-011",
            severity="major",
            description="AnalyticsPro reserves right to use derived data for own product improvement and marketing — "
                        "processor exceeding purpose limitation without explicit controller authorization.",
            keywords=["anonymized", "product improvement", "marketing", "own purposes"],
        ),
        GroundTruthViolation(
            section_id="sec_sp_list",
            regulation_id="REG-DP-012",
            severity="major",
            description="MarketBoost LLC's purpose is vaguely described as 'analytics dashboard and reporting' "
                        "but it is an AnalyticsPro subsidiary — potential conflict. QuickTranslate in China "
                        "processes medical terminology without adequate transfer safeguard.",
            keywords=["MarketBoost", "vague", "subsidiary", "QuickTranslate", "China"],
        ),
        GroundTruthViolation(
            section_id="sec_consent_text",
            regulation_id="REG-CP-001",
            severity="critical",
            description="Consent form states 'consent cannot be withdrawn after claim submission' — "
                        "invalid restriction on right to withdraw consent.",
            keywords=["cannot be withdrawn", "withdraw", "consent"],
        ),
        GroundTruthViolation(
            section_id="sec_consent_scope",
            regulation_id="REG-CP-002",
            severity="major",
            description="Single consent covers fraud detection AND marketing of insurance products — "
                        "bundled consent for unrelated purposes is not valid.",
            keywords=["marketing", "fraud detection", "bundled", "single consent"],
        ),
        GroundTruthViolation(
            section_id="sec_dpa_liability",
            regulation_id="REG-DP-013",
            severity="major",
            description="DPA excludes AnalyticsPro liability for regulatory fines imposed on MediCare Plus — "
                        "processor attempting to avoid accountability for its own breaches.",
            keywords=["liability", "regulatory fines", "exclude", "not liable"],
        ),
    ],
    expected_overall_status="non_compliant",
    max_steps=30,
    hints=[
        "Three documents to review — start with the DPA, then cross-reference the sub-processor list and consent form.",
        "Multiple regulation domains apply — check data privacy AND consumer protection rules.",
        "Be careful: some clauses look suspicious but are actually compliant (e.g., security measures, retention with deletion cert).",
        "Be efficient — read a section, check the relevant regulation, flag or clear, move on. Don't re-read.",
    ],
)


# ═══════════════════════════════════════════════════════════════════════════
# SCENARIO REGISTRY
# ═══════════════════════════════════════════════════════════════════════════

SCENARIOS = {
    "easy_privacy_review": EASY_SCENARIO,
    "medium_lending_review": MEDIUM_SCENARIO,
    "hard_vendor_dpa_review": HARD_SCENARIO,
}

# Placeholder — Task 4 and 5 will be appended below


# ═══════════════════════════════════════════════════════════════════════════
# TASK 4: Employment handbook with labor law violations
# ═══════════════════════════════════════════════════════════════════════════

EMPLOYMENT_SCENARIO = Scenario(
    task_id="medium_employment_review",
    title="Employee Handbook Compliance Review",
    difficulty="medium",
    description="Review a startup's employee handbook against employment and labor regulations.",
    task_prompt=(
        "You are an HR compliance consultant. TechStartup Inc. is preparing for a Series B "
        "fundraise and needs their employee handbook reviewed for legal compliance before "
        "due diligence. Review the handbook against applicable employment regulations."
    ),
    documents={
        "handbook_001": {
            "type": "employee_handbook",
            "title": "TechStartup Inc. — Employee Handbook v2.1",
            "parties": ["TechStartup Inc.", "Employees"],
            "date": "2025-08-01",
            "summary": "Company-wide employee policies and procedures",
            "sections": {
                "sec_overtime": {
                    "title": "4.2 Overtime Policy",
                    "content": (
                        "TechStartup Inc. operates on a results-oriented work culture. "
                        "All employees are classified as exempt professionals regardless of role. "
                        "Overtime compensation is not provided as all positions are salaried. "
                        "Employees are expected to work the hours necessary to meet their objectives, "
                        "which typically ranges from 45-60 hours per week."
                    ),
                    "page": 12,
                },
                "sec_leave": {
                    "title": "5.1 Leave Policy",
                    "content": (
                        "Employees receive 10 days of Paid Time Off (PTO) per year, inclusive of "
                        "sick leave and personal days. PTO does not carry over to the next year. "
                        "Unused PTO is forfeited and not paid out upon termination. "
                        "Employees must provide 4 weeks advance notice for any leave longer than 2 days. "
                        "Medical leave requires a doctor's note for any absence, including single-day illness."
                    ),
                    "page": 15,
                },
                "sec_termination": {
                    "title": "7.1 Termination",
                    "content": (
                        "TechStartup Inc. reserves the right to terminate any employee at any time, "
                        "for any reason, without notice or severance. By accepting employment, "
                        "employees waive any right to challenge their termination through legal "
                        "proceedings or arbitration. Employees who are terminated must sign a "
                        "non-disparagement agreement before receiving their final paycheck."
                    ),
                    "page": 20,
                },
                "sec_noncompete": {
                    "title": "8.1 Non-Compete Agreement",
                    "content": (
                        "All employees agree to a 24-month non-compete clause covering any "
                        "technology company globally. During this period, former employees may not "
                        "work for, consult for, or invest in any company that could be considered "
                        "a competitor. Violation results in liquidated damages of $500,000. "
                        "This agreement applies to all roles including interns and contractors."
                    ),
                    "page": 22,
                },
                "sec_ip": {
                    "title": "9.1 Intellectual Property",
                    "content": (
                        "All intellectual property created by employees, whether during work hours "
                        "or personal time, using company resources or not, is the exclusive property "
                        "of TechStartup Inc. This includes side projects, open-source contributions, "
                        "and inventions unrelated to the company's business."
                    ),
                    "page": 24,
                },
                "sec_whistleblower": {
                    "title": "10.1 Reporting Concerns",
                    "content": (
                        "Employees who have concerns about company practices should report them "
                        "directly to their immediate supervisor. All reports are kept confidential "
                        "within management. Employees who report concerns to external parties "
                        "(media, regulators, social media) before exhausting internal channels "
                        "will be subject to disciplinary action up to and including termination."
                    ),
                    "page": 26,
                },
            },
        },
    },
    regulations={
        "REG-EL-001": {
            "domain": "employment",
            "title": "Overtime Classification Requirements",
            "description": "Employees must be correctly classified as exempt or non-exempt for overtime purposes.",
            "requirement": (
                "Only employees meeting specific duties tests (executive, administrative, professional, "
                "computer, outside sales) AND earning above the salary threshold may be classified exempt. "
                "Blanket classification of all employees as exempt is prohibited. Non-exempt employees "
                "must receive overtime pay (1.5x) for hours worked over 40 per week."
            ),
            "severity": "critical",
            "keywords": ["exempt", "overtime", "classification", "non-exempt", "salary", "40 hours"],
        },
        "REG-EL-002": {
            "domain": "employment",
            "title": "Leave and Sick Time Requirements",
            "description": "Employers must provide minimum sick leave and cannot impose unreasonable conditions.",
            "requirement": (
                "Employers must provide a minimum of 5 separate sick days not drawn from PTO. "
                "Requiring a doctor's note for single-day absences is prohibited in most jurisdictions. "
                "PTO payout on termination is required in states where it is considered earned wages. "
                "Advance notice requirements exceeding 2 weeks for leave requests are considered unreasonable."
            ),
            "severity": "major",
            "keywords": ["sick leave", "PTO", "doctor's note", "payout", "termination", "advance notice"],
        },
        "REG-EL-003": {
            "domain": "employment",
            "title": "Termination Rights",
            "description": "Employees cannot be forced to waive statutory rights as a condition of employment or final pay.",
            "requirement": (
                "Conditioning final paycheck on signing any agreement (non-disparagement, release) is "
                "prohibited — earned wages must be paid regardless. Requiring employees to waive the right "
                "to legal proceedings or regulatory complaints is unenforceable. At-will termination does not "
                "override anti-discrimination or whistleblower protections."
            ),
            "severity": "critical",
            "keywords": ["final paycheck", "waive", "non-disparagement", "legal proceedings", "wages"],
        },
        "REG-EL-004": {
            "domain": "employment",
            "title": "Non-Compete Reasonableness",
            "description": "Non-compete agreements must be reasonable in scope, duration, and geography.",
            "requirement": (
                "Non-compete clauses exceeding 12 months are presumptively unreasonable. "
                "Global geographic scope is unreasonable. Applying non-competes to interns and contractors "
                "is prohibited in most jurisdictions. Liquidated damages clauses must reflect actual harm, "
                "not be punitive."
            ),
            "severity": "major",
            "keywords": ["non-compete", "24 months", "global", "interns", "unreasonable", "liquidated damages"],
        },
        "REG-EL-005": {
            "domain": "employment",
            "title": "Intellectual Property Assignment Limits",
            "description": "Employers cannot claim ownership of all employee inventions without limits.",
            "requirement": (
                "IP assignment clauses must be limited to work created within the scope of employment "
                "or using company resources. Claiming ownership of personal-time inventions unrelated "
                "to the company's business is unenforceable. Many states have specific statutes "
                "protecting employee inventions."
            ),
            "severity": "major",
            "keywords": ["intellectual property", "personal time", "side projects", "scope of employment", "inventions"],
        },
        "REG-EL-006": {
            "domain": "employment",
            "title": "Whistleblower Protection",
            "description": "Employees must be free to report concerns to regulators without retaliation.",
            "requirement": (
                "Policies that require internal reporting before external reporting, or that threaten "
                "discipline for contacting regulators, violate whistleblower protection laws. "
                "Employees must be informed of their right to report to external agencies. "
                "Retaliation for protected whistleblowing activity is prohibited."
            ),
            "severity": "critical",
            "keywords": ["whistleblower", "retaliation", "regulators", "external", "disciplinary", "report"],
        },
    },
    ground_truth_violations=[
        GroundTruthViolation(
            section_id="sec_overtime", regulation_id="REG-EL-001", severity="critical",
            description="All employees blanket-classified as exempt regardless of role or duties test.",
            keywords=["exempt", "classification", "overtime", "blanket"],
        ),
        GroundTruthViolation(
            section_id="sec_leave", regulation_id="REG-EL-002", severity="major",
            description="Sick leave bundled into PTO, doctor's note required for single-day absence, "
                        "4-week advance notice unreasonable, PTO forfeited on termination.",
            keywords=["sick leave", "PTO", "doctor's note", "advance notice", "forfeited"],
        ),
        GroundTruthViolation(
            section_id="sec_termination", regulation_id="REG-EL-003", severity="critical",
            description="Final paycheck conditioned on signing non-disparagement. "
                        "Employees forced to waive right to legal proceedings.",
            keywords=["final paycheck", "non-disparagement", "waive", "legal"],
        ),
        GroundTruthViolation(
            section_id="sec_noncompete", regulation_id="REG-EL-004", severity="major",
            description="24-month global non-compete applied to all including interns. "
                        "$500K liquidated damages is punitive.",
            keywords=["24", "global", "interns", "non-compete", "liquidated"],
        ),
        GroundTruthViolation(
            section_id="sec_ip", regulation_id="REG-EL-005", severity="major",
            description="IP assignment covers personal-time inventions and side projects "
                        "unrelated to company business.",
            keywords=["personal time", "side projects", "intellectual property", "unrelated"],
        ),
        GroundTruthViolation(
            section_id="sec_whistleblower", regulation_id="REG-EL-006", severity="critical",
            description="Policy threatens discipline for reporting to external parties/regulators "
                        "before exhausting internal channels. Violates whistleblower protections.",
            keywords=["whistleblower", "external", "disciplinary", "regulators", "retaliation"],
        ),
    ],
    expected_overall_status="non_compliant",
    max_steps=20,
    hints=[
        "Review each section of the handbook against the applicable employment regulation.",
        "Look for overbroad clauses, missing employee protections, and illegal conditions.",
    ],
)


# ═══════════════════════════════════════════════════════════════════════════
# TASK 5: Financial report with SOX-like violations
# ═══════════════════════════════════════════════════════════════════════════

FINANCIAL_SCENARIO = Scenario(
    task_id="hard_financial_reporting",
    title="Financial Report & Internal Controls Review",
    difficulty="hard",
    description="Review a company's quarterly financial report and internal controls memo against financial reporting regulations.",
    task_prompt=(
        "You are an external auditor reviewing GlobalTech Corp's Q3 2025 financial report "
        "and internal controls memorandum against financial reporting regulations. The company "
        "is publicly traded and subject to SOX-like requirements. Review both documents for "
        "compliance issues. Be precise — some disclosures look unusual but are technically compliant."
    ),
    documents={
        "fin_report_001": {
            "type": "financial_report",
            "title": "GlobalTech Corp — Q3 2025 Quarterly Financial Report",
            "parties": ["GlobalTech Corp", "Shareholders"],
            "date": "2025-10-15",
            "summary": "Quarterly financial report for public company",
            "sections": {
                "sec_revenue": {
                    "title": "Revenue Recognition",
                    "content": (
                        "Q3 revenue: $847M (up 23% YoY). Revenue includes $120M from a multi-year "
                        "enterprise license agreement signed September 28, 2025. The full contract value "
                        "was recognized in Q3 as the customer took delivery of the software. "
                        "Channel partner rebates of $34M were netted against marketing expenses "
                        "rather than revenue. A $15M payment received from a related-party entity "
                        "(CEO's family office) for 'strategic consulting services' was recorded as revenue."
                    ),
                    "page": 4,
                },
                "sec_expenses": {
                    "title": "Operating Expenses",
                    "content": (
                        "Total operating expenses: $612M. R&D expenses of $180M include $45M in "
                        "capitalized software development costs. Stock-based compensation of $78M "
                        "is disclosed in the footnotes but excluded from the non-GAAP adjusted EBITDA "
                        "presented as the headline metric in the earnings release. Restructuring charges "
                        "of $23M from the Q2 layoff were reversed in Q3 after management determined "
                        "the original estimate was too high."
                    ),
                    "page": 6,
                },
                "sec_related_party": {
                    "title": "Related Party Transactions",
                    "content": (
                        "The company leases its headquarters from a real estate trust owned by the CEO's spouse "
                        "at $4.2M/year. An independent appraisal confirmed the rate is at market value. "
                        "The board audit committee reviewed and approved this arrangement annually. "
                        "The $15M consulting payment to the CEO's family office is disclosed in Note 14."
                    ),
                    "page": 12,
                },
                "sec_cash_flow": {
                    "title": "Cash Flow Statement",
                    "content": (
                        "Operating cash flow: $156M. The company reclassified $40M of vendor financing "
                        "payments from operating activities to financing activities in Q3, improving "
                        "reported operating cash flow. The prior quarter has not been restated. "
                        "A $28M loan to an executive officer was classified as 'other investing activities.'"
                    ),
                    "page": 15,
                },
            },
        },
        "controls_memo_001": {
            "type": "financial_report",
            "title": "GlobalTech Corp — Internal Controls Memorandum Q3 2025",
            "parties": ["GlobalTech Corp"],
            "date": "2025-10-10",
            "summary": "Internal controls assessment and management certification",
            "sections": {
                "sec_controls_revenue": {
                    "title": "Revenue Recognition Controls",
                    "content": (
                        "Revenue recognition for enterprise licenses is approved by the VP of Sales "
                        "and the CFO. For contracts over $50M, board approval is required. "
                        "The $120M license deal was approved by the CFO alone as it was structured "
                        "as two separate $60M contracts to stay below the board approval threshold."
                    ),
                    "page": 3,
                },
                "sec_controls_audit": {
                    "title": "Audit Committee Independence",
                    "content": (
                        "The audit committee consists of three board members. Two members are independent "
                        "directors with financial expertise. The third member is the company's General "
                        "Counsel, who also serves as Corporate Secretary. The committee meets quarterly "
                        "and reviews all related-party transactions."
                    ),
                    "page": 5,
                },
                "sec_controls_cfo": {
                    "title": "CFO Certification",
                    "content": (
                        "The CFO certifies that the financial statements fairly present the company's "
                        "financial condition. Note: The CFO's annual bonus is tied to meeting the "
                        "non-GAAP adjusted EBITDA target of $235M. Q3 adjusted EBITDA was $235.2M."
                    ),
                    "page": 7,
                },
            },
        },
    },
    regulations={
        "REG-FR-001": {
            "domain": "financial_reporting",
            "title": "Revenue Recognition Standards",
            "description": "Revenue must be recognized when performance obligations are satisfied, not prematurely.",
            "requirement": (
                "Multi-year contracts must have revenue recognized over the service period unless "
                "the entire obligation is fulfilled at a point in time. Recognizing full multi-year "
                "contract value upon delivery of software alone, without considering ongoing obligations, "
                "may be premature. Channel rebates must be netted against revenue, not classified as "
                "marketing expenses. Related-party revenue must be at arm's length and substantiated."
            ),
            "severity": "critical",
            "keywords": ["revenue recognition", "multi-year", "channel rebates", "related-party", "premature"],
        },
        "REG-FR-002": {
            "domain": "financial_reporting",
            "title": "Cash Flow Classification",
            "description": "Cash flows must be consistently classified and comparative periods restated.",
            "requirement": (
                "Reclassifying cash flows between categories requires restatement of prior periods "
                "for comparability. Loans to executive officers are prohibited for public companies "
                "and cannot be disguised as investing activities."
            ),
            "severity": "critical",
            "keywords": ["reclassify", "restatement", "prior period", "executive loan", "prohibited"],
        },
        "REG-FR-003": {
            "domain": "financial_reporting",
            "title": "Internal Controls Over Financial Reporting",
            "description": "Internal controls must prevent circumvention and ensure proper authorization.",
            "requirement": (
                "Structuring transactions to avoid approval thresholds (e.g., splitting one deal into two) "
                "is a control circumvention and a material weakness. All significant transactions must "
                "go through appropriate approval channels based on their true economic substance."
            ),
            "severity": "critical",
            "keywords": ["circumvention", "splitting", "threshold", "material weakness", "approval"],
        },
        "REG-FR-004": {
            "domain": "financial_reporting",
            "title": "Audit Committee Composition",
            "description": "Audit committees of public companies must be fully independent.",
            "requirement": (
                "All audit committee members must be independent directors. Company officers "
                "(including General Counsel) cannot serve on the audit committee. At least one member "
                "must be a financial expert."
            ),
            "severity": "critical",
            "keywords": ["independent", "audit committee", "officer", "General Counsel"],
        },
        "REG-FR-005": {
            "domain": "financial_reporting",
            "title": "Management Compensation Conflicts",
            "description": "Management certifications must be free from conflicts of interest.",
            "requirement": (
                "When a certifying officer's compensation is directly tied to the specific financial "
                "metric they are certifying, this creates a conflict of interest that must be disclosed "
                "and mitigated. The audit committee must review and approve any such arrangements."
            ),
            "severity": "major",
            "keywords": ["conflict", "compensation", "bonus", "certification", "EBITDA", "tied"],
        },
    },
    ground_truth_violations=[
        GroundTruthViolation(
            section_id="sec_revenue", regulation_id="REG-FR-001", severity="critical",
            description="Full $120M multi-year contract recognized in Q3. Channel rebates netted against "
                        "marketing not revenue. Related-party $15M consulting payment recorded as revenue.",
            keywords=["revenue", "multi-year", "channel rebates", "related-party", "120M"],
        ),
        GroundTruthViolation(
            section_id="sec_cash_flow", regulation_id="REG-FR-002", severity="critical",
            description="$40M vendor financing reclassified without restating prior period. "
                        "$28M executive loan disguised as investing activity — prohibited for public companies.",
            keywords=["reclassify", "restatement", "executive loan", "prior period", "prohibited"],
        ),
        GroundTruthViolation(
            section_id="sec_controls_revenue", regulation_id="REG-FR-003", severity="critical",
            description="$120M deal structured as two $60M contracts to circumvent board approval threshold. "
                        "Material weakness in internal controls.",
            keywords=["circumvention", "splitting", "threshold", "60M", "board approval"],
        ),
        GroundTruthViolation(
            section_id="sec_controls_audit", regulation_id="REG-FR-004", severity="critical",
            description="General Counsel (company officer) serves on audit committee — not independent.",
            keywords=["independent", "General Counsel", "officer", "audit committee"],
        ),
        GroundTruthViolation(
            section_id="sec_controls_cfo", regulation_id="REG-FR-005", severity="major",
            description="CFO's bonus directly tied to non-GAAP EBITDA target that they certify. "
                        "Conflict of interest in certification.",
            keywords=["conflict", "bonus", "EBITDA", "certification", "compensation"],
        ),
    ],
    expected_overall_status="non_compliant",
    max_steps=25,
    hints=[
        "Two documents to review — the financial report and the internal controls memo.",
        "Cross-reference the controls memo with the financial report for inconsistencies.",
        "Some related-party transactions (the office lease) are actually compliant — don't flag them.",
        "Look for structural issues: transaction splitting, independence violations, conflicts of interest.",
    ],
)


# Update the registry
SCENARIOS["medium_employment_review"] = EMPLOYMENT_SCENARIO
SCENARIOS["hard_financial_reporting"] = FINANCIAL_SCENARIO
