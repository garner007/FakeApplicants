"""Validation rules API routes."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from applicant_validator.services.validation import ALL_RULES

router = APIRouter(prefix="/rules", tags=["rules"])


class ValidationRuleResponse(BaseModel):
    """Response model for a validation rule."""

    name: str
    description: str
    category: str
    severity: str
    version: str
    checks_fields: list[str] = Field(default_factory=list)
    trigger_examples: list[str] = Field(default_factory=list)
    rationale: str = ""
    is_active: bool = True


class ValidationRulesListResponse(BaseModel):
    """Response with list of all validation rules."""

    rules: list[ValidationRuleResponse]
    total: int


@router.get("", response_model=ValidationRulesListResponse)
async def list_validation_rules() -> ValidationRulesListResponse:
    """Get list of all validation rules with their metadata.

    This endpoint returns information about all active validation rules,
    including what they check, their severity, and examples of triggers.
    """
    rules = []

    for rule in ALL_RULES:
        rules.append(
            ValidationRuleResponse(
                name=rule.name,
                description=rule.description,
                category=rule.category,
                severity=rule.default_severity.value,
                version=rule.version,
                checks_fields=getattr(rule, "checks_fields", []),
                trigger_examples=getattr(rule, "trigger_examples", []),
                rationale=getattr(rule, "rationale", ""),
                is_active=True,
            )
        )

    return ValidationRulesListResponse(rules=rules, total=len(rules))
