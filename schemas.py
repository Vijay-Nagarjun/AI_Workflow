"""
Shared pydantic schemas for every LLM call that's supposed to return JSON.

Validating against these catches a malformed or partial response (a score
of "high" instead of 7, a missing field, an account_type that isn't one of
the three allowed buckets) before it reaches downstream code — instead of
silently writing garbage into the output JSON.
"""
from typing import List

from pydantic import BaseModel, Field, field_validator

ALLOWED_ACCOUNT_TYPES = {"Systems Integrator (SI)", "ISV", "Enterprise End-User"}


class CompanyCandidate(BaseModel):
    full_name: str
    descriptor: str  # one-line disambiguator, e.g. "fintech payments app, India"
    confidence: float = Field(ge=0.0, le=1.0)


class DisambiguationResult(BaseModel):
    ambiguous: bool
    candidates: List[CompanyCandidate]

    @field_validator("candidates")
    @classmethod
    def at_least_one_candidate(cls, v: List[CompanyCandidate]) -> List[CompanyCandidate]:
        if not v:
            raise ValueError("candidates list must not be empty")
        return v


class ClassificationResult(BaseModel):
    account_type: str
    platforms: List[str]
    pain_point: str
    decision_maker_title: str
    recent_signal: str

    @field_validator("account_type")
    @classmethod
    def account_type_known(cls, v: str) -> str:
        if v not in ALLOWED_ACCOUNT_TYPES:
            raise ValueError(f"account_type {v!r} must be one of {sorted(ALLOWED_ACCOUNT_TYPES)}")
        return v


class QualityResult(BaseModel):
    specificity_score: int = Field(ge=0, le=10)
    relevance_score: int = Field(ge=0, le=10)
    tone_score: int = Field(ge=0, le=10)
    generic_phrases_flagged: List[str] = Field(default_factory=list)
    suggested_improvement: str


class GroundingResult(BaseModel):
    """
    Catches the Titan-ERP-number failure mode: the writer stating a
    specific, checkable "fact" (a dollar figure, a plant name, a
    case-study stat) that isn't actually anywhere in the account intel.
    """
    ungrounded_claims: List[str] = Field(default_factory=list)
