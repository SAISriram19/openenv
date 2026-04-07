"""
Typed Pydantic models for the Regulatory Compliance Document Review OpenEnv.

Domain: An agent acts as a compliance analyst reviewing business documents
(contracts, policies, loan applications, privacy notices) against regulatory
rules (GDPR, SOX, KYC/AML, HIPAA-like, lending regulations).

The agent reads documents, extracts relevant clauses, checks them against
applicable regulations, and produces a compliance verdict with citations.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ActionType(str, Enum):
    """All actions an agent can take during compliance review."""
    READ_DOCUMENT = "read_document"
    READ_SECTION = "read_section"
    READ_REGULATION = "read_regulation"
    SEARCH_DOCUMENT = "search_document"
    CROSS_REFERENCE = "cross_reference"
    FLAG_VIOLATION = "flag_violation"
    FLAG_COMPLIANT = "flag_compliant"
    REQUEST_CLARIFICATION = "request_clarification"
    ADD_NOTE = "add_note"
    SUBMIT_REVIEW = "submit_review"
    NOOP = "noop"


class Severity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    OBSERVATION = "observation"


class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NEEDS_REVIEW = "needs_review"
    NOT_APPLICABLE = "not_applicable"


class DocumentType(str, Enum):
    CONTRACT = "contract"
    PRIVACY_POLICY = "privacy_policy"
    LOAN_APPLICATION = "loan_application"
    EMPLOYEE_HANDBOOK = "employee_handbook"
    FINANCIAL_REPORT = "financial_report"
    VENDOR_AGREEMENT = "vendor_agreement"
    DATA_PROCESSING_AGREEMENT = "data_processing_agreement"


class RegulationDomain(str, Enum):
    DATA_PRIVACY = "data_privacy"           # GDPR-like
    FINANCIAL_REPORTING = "financial_reporting"  # SOX-like
    ANTI_MONEY_LAUNDERING = "aml_kyc"       # KYC/AML
    LENDING_COMPLIANCE = "lending"           # Fair lending
    EMPLOYMENT_LAW = "employment"            # Labor regulations
    CONSUMER_PROTECTION = "consumer_protection"


# ---------------------------------------------------------------------------
# Action model
# ---------------------------------------------------------------------------

class Action(BaseModel):
    """A single agent action in the compliance review environment."""
    action_type: ActionType = Field(..., description="The type of action to perform")
    target: Optional[str] = Field(None, description="Target document, section, or regulation ID")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional parameters for the action",
    )

    model_config = {"json_schema_extra": {
        "examples": [
            {"action_type": "read_document", "target": "contract_001", "parameters": {}},
            {"action_type": "read_section", "target": "contract_001", "parameters": {"section": "data_handling"}},
            {"action_type": "read_regulation", "target": "REG-DP-003", "parameters": {}},
            {"action_type": "search_document", "target": "contract_001", "parameters": {"query": "data retention"}},
            {"action_type": "flag_violation", "target": "contract_001", "parameters": {
                "section": "clause_7", "regulation": "REG-DP-003",
                "severity": "major", "description": "No data retention period specified"
            }},
            {"action_type": "submit_review", "target": None, "parameters": {
                "overall_status": "non_compliant",
                "summary": "Contract missing mandatory data retention and breach notification clauses"
            }},
        ]
    }}


# ---------------------------------------------------------------------------
# Observation sub-models
# ---------------------------------------------------------------------------

class RegulationRule(BaseModel):
    """A single regulatory rule that must be checked."""
    rule_id: str
    domain: RegulationDomain
    title: str
    description: str
    requirement: str
    severity_if_violated: Severity
    keywords: List[str] = Field(default_factory=list)
    examples_of_compliance: str = ""
    examples_of_violation: str = ""


class DocumentSection(BaseModel):
    """A section within a business document."""
    section_id: str
    title: str
    content: str
    page_number: int = 1


class DocumentInfo(BaseModel):
    """Metadata about a document under review."""
    doc_id: str
    doc_type: DocumentType
    title: str
    parties: List[str] = Field(default_factory=list)
    date: str = ""
    section_ids: List[str] = Field(default_factory=list)
    summary: str = ""


class ViolationFlag(BaseModel):
    """A violation flagged by the agent."""
    section_id: str
    regulation_id: str
    severity: Severity
    description: str
    suggested_fix: str = ""


class ActionResult(BaseModel):
    """Result returned after executing an action."""
    success: bool
    message: str
    data: Any = None


# ---------------------------------------------------------------------------
# Observation model
# ---------------------------------------------------------------------------

class Observation(BaseModel):
    """Everything the agent sees after each step."""
    # Task context
    task_description: str = ""
    documents: List[DocumentInfo] = Field(default_factory=list)
    applicable_regulations: List[str] = Field(default_factory=list)

    # Current state
    action_result: Optional[ActionResult] = None
    violations_flagged: List[ViolationFlag] = Field(default_factory=list)
    compliant_flags: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)

    # Metadata
    step_number: int = 0
    max_steps: int = 20
    review_submitted: bool = False

    # Live scoring (like insurance adjuster dashboard)
    regulations_investigated: int = 0
    sections_investigated: int = 0
    process_quality_score: float = 0.0

    # Hints and guidance
    hints: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Reward model
# ---------------------------------------------------------------------------

class Reward(BaseModel):
    """Reward signal returned each step."""
    total: float = Field(..., ge=-1.0, le=1.0)
    detection_score: float = Field(0.0, ge=0.0, le=1.0, description="Did agent find violations?")
    accuracy_score: float = Field(0.0, ge=0.0, le=1.0, description="Were flags correct?")
    completeness_score: float = Field(0.0, ge=0.0, le=1.0, description="All violations found?")
    false_positive_penalty: float = Field(0.0, ge=-1.0, le=0.0, description="Penalty for wrong flags")
    efficiency_bonus: float = Field(0.0, ge=-0.5, le=0.5)
    breakdown: Dict[str, float] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# State model
# ---------------------------------------------------------------------------

class EnvironmentState(BaseModel):
    """Full internal state returned by state()."""
    task_id: str
    step_number: int
    max_steps: int
    done: bool
    observation: Observation
    cumulative_reward: float
    actions_taken: List[Dict[str, Any]]
    violations_flagged: List[ViolationFlag]
    compliant_flags: List[str]
    notes: List[str]
    review_submitted: bool
    overall_status: Optional[str] = None
    review_summary: Optional[str] = None
    ground_truth_violations: int = 0
    detected_correctly: int = 0
    false_positives: int = 0
    missed_violations: int = 0
    process_quality: float = 0.0
    regs_read: int = 0
    sections_read: int = 0
    correct_compliant_flags: int = 0
    confidence_calibration: float = 0.0
    risk_score: Optional[int] = None
