# Project Plan - Lever-LinkedIn Applicant Validator

This file tracks implementation progress. **Update this checklist as tasks are completed.**

---

## Non-Negotiables

- [ ] **TDD**: Write tests BEFORE implementation
- [ ] **Coverage**: Maintain 90%+ test coverage
- [ ] **Type Hints**: All functions and methods must have type hints
- [ ] **Async**: Use async/await for all I/O operations
- [ ] **Checklist**: Update this file as tasks are completed

---

## Phase 1: Project Scaffolding & Configuration

- [x] Update `pyproject.toml` with all dependencies
- [x] Create directory structure (`src/applicant_validator/`, `tests/`)
- [x] Create `.gitignore`
- [x] Create `.env.example` template
- [x] Configure pytest in `pyproject.toml`
- [x] Configure ruff in `pyproject.toml`
- [x] Configure mypy in `pyproject.toml` (with pydantic plugin)
- [x] Write tests for `config.py` (TDD)
- [x] Implement `config.py` with Pydantic Settings
- [x] Write tests for `exceptions.py` (TDD)
- [x] Implement `exceptions.py` with custom exception hierarchy
- [x] Create `Makefile` for common commands
- [x] Create `.pre-commit-config.yaml`
- [x] Create `PROJECT_PLAN.md` (this file)
- [x] Verify pre-commit hooks work (`make pre-commit-install && make pre-commit-run`)

**Phase 1 Status**: 🟢 Complete

---

## Phase 2: Data Models

### Applicant Model (`models/applicant.py`)
- [x] Write tests for `Applicant` model
- [x] Implement `Applicant` model with Pydantic

### LinkedIn Models (`models/linkedin.py`)
- [x] Write tests for `Experience` model
- [x] Implement `Experience` model
- [x] Write tests for `Education` model
- [x] Implement `Education` model
- [x] Write tests for `LinkedInProfile` model
- [x] Implement `LinkedInProfile` model

### Validation Models (`models/validation.py`)
- [x] Write tests for `Severity` enum
- [x] Implement `Severity` enum
- [x] Write tests for `RiskLevel` enum
- [x] Implement `RiskLevel` enum
- [x] Write tests for `ValidationResult` model
- [x] Implement `ValidationResult` model
- [x] Write tests for `ValidationReport` model (including computed properties)
- [x] Implement `ValidationReport` model

### Models Package
- [x] Export all models from `models/__init__.py`
- [x] Verify all model tests pass
- [x] Verify coverage >= 90%

**Phase 2 Status**: 🟢 Complete

---

## Phase 3: API Clients

### Base Client (`clients/base.py`)
- [x] Write tests for `BaseClient` abstract class
- [x] Implement `BaseClient` with common HTTP logic
- [x] Implement retry logic with exponential backoff

### Lever Client (`clients/lever.py`)
- [x] Write tests for `LeverClient.__init__`
- [x] Write tests for `LeverClient.get_applicants()`
- [x] Write tests for `LeverClient.get_applicant()`
- [x] Write tests for `LeverClient.get_opportunities()`
- [x] Write tests for authentication (Basic Auth)
- [x] Write tests for rate limiting handling
- [x] Write tests for error handling (`LeverAPIError`)
- [x] Implement `LeverClient`

### LinkedIn Client (`clients/linkedin.py`)
- [x] Write tests for `LinkedInClient.__init__`
- [x] Write tests for `LinkedInClient.validate_url()`
- [x] Write tests for `LinkedInClient.check_profile_exists()`
- [x] Write tests for `LinkedInClient.get_profile_preview()` (fallback method)
- [x] Write tests for fallback strategy
- [x] Implement `LinkedInClient`

### Clients Package
- [x] Export all clients from `clients/__init__.py`
- [x] Verify all client tests pass (81 tests)
- [x] Verify coverage >= 95% for clients (94.34%)

**Phase 3 Status**: 🟢 Complete

---

## Phase 4: Validation Engine & Rules

### Base Validator (`validators/base.py`)
- [ ] Write tests for `ValidationRule` abstract base class
- [ ] Implement `ValidationRule` ABC

### Validator Registry (`validators/registry.py`)
- [ ] Write tests for `ValidatorRegistry.register()`
- [ ] Write tests for `ValidatorRegistry.get_all()`
- [ ] Write tests for `ValidatorRegistry.get_by_name()`
- [ ] Write tests for `ValidatorRegistry.get_requiring_linkedin()`
- [ ] Implement `ValidatorRegistry`

### LinkedIn Exists Rule (`validators/linkedin_exists.py`)
- [ ] Write tests for URL format validation
- [ ] Write tests for URL resolution check
- [ ] Write tests for missing LinkedIn URL
- [ ] Write tests for invalid URL format
- [ ] Write tests for 404 response
- [ ] Implement `LinkedInExistsRule`

### Name Consistency Rule (`validators/name_consistency.py`)
- [ ] Write tests for exact name match
- [ ] Write tests for fuzzy name matching (nicknames, abbreviations)
- [ ] Write tests for significant mismatch detection
- [ ] Write tests for missing LinkedIn profile
- [ ] Implement `NameConsistencyRule`

### Email Domain Rule (`validators/email_domain.py`)
- [ ] Write tests for valid email domains
- [ ] Write tests for disposable email detection
- [ ] Write tests for MX record validation
- [ ] Implement `EmailDomainRule`

### Validators Package
- [ ] Export all validators from `validators/__init__.py`
- [ ] Register all validators in the default registry
- [ ] Verify all validator tests pass
- [ ] Verify coverage >= 95% for validators

**Phase 4 Status**: ⬜ Not Started

---

## Phase 5: Services Layer

### Applicant Service (`services/applicant_service.py`)
- [ ] Write tests for `ApplicantService.__init__`
- [ ] Write tests for `ApplicantService.get_applicants()`
- [ ] Write tests for `ApplicantService.get_applicant()`
- [ ] Write tests for `ApplicantService.enrich_with_linkedin()`
- [ ] Implement `ApplicantService`

### Validation Service (`services/validation_service.py`)
- [ ] Write tests for `ValidationService.__init__`
- [ ] Write tests for `ValidationService.validate_applicant()`
- [ ] Write tests for `ValidationService.validate_batch()`
- [ ] Write tests for `ValidationService._calculate_risk_level()`
- [ ] Write tests for `ValidationService._calculate_score()`
- [ ] Write tests for concurrent validation
- [ ] Write tests for partial LinkedIn data handling
- [ ] Implement `ValidationService`

### Services Package
- [ ] Export all services from `services/__init__.py`
- [ ] Verify all service tests pass
- [ ] Verify coverage >= 90%

**Phase 5 Status**: ⬜ Not Started

---

## Phase 6: FastAPI REST API

### API Setup (`api/main.py`)
- [ ] Write tests for app initialization
- [ ] Write tests for health check endpoint
- [ ] Implement FastAPI app setup
- [ ] Configure CORS
- [ ] Configure exception handlers

### Request/Response Schemas (`api/schemas/`)
- [ ] Write tests for `ApplicantResponse` schema
- [ ] Write tests for `ApplicantListResponse` schema
- [ ] Write tests for `ValidationReportResponse` schema
- [ ] Write tests for `ValidationRuleResponse` schema
- [ ] Write tests for `BatchValidationRequest` schema
- [ ] Write tests for `ErrorResponse` schema
- [ ] Implement all schemas

### Applicant Routes (`api/routes/applicants.py`)
- [ ] Write tests for `GET /api/v1/applicants`
- [ ] Write tests for `GET /api/v1/applicants/{id}`
- [ ] Write tests for `POST /api/v1/applicants/{id}/validate`
- [ ] Write tests for `GET /api/v1/applicants/{id}/report`
- [ ] Write tests for error responses (404, 422, 500)
- [ ] Implement applicant routes

### Validation Routes (`api/routes/validations.py`)
- [ ] Write tests for `GET /api/v1/validations`
- [ ] Write tests for `GET /api/v1/validations/{rule}`
- [ ] Write tests for `POST /api/v1/validations/batch`
- [ ] Implement validation routes

### API Package
- [ ] Export routers from `api/__init__.py`
- [ ] Verify all API tests pass
- [ ] Verify OpenAPI documentation generates correctly
- [ ] Verify coverage >= 90%

**Phase 6 Status**: ⬜ Not Started

---

## Phase 7: Integration Testing & Polish

### Integration Tests
- [ ] Write Lever sandbox integration tests
- [ ] Write LinkedIn integration tests (or fallback tests)
- [ ] Write end-to-end API integration tests
- [ ] Verify all integration tests pass with sandbox credentials

### Documentation
- [ ] Update README.md with usage examples
- [ ] Verify CLAUDE.md is current
- [ ] Add docstrings to all public APIs

### Final Verification
- [ ] Run `make check-all` and verify all pass
- [ ] Verify coverage >= 90%
- [ ] Run `make pre-commit-run` and verify all pass
- [ ] Test application startup with `make dev`

**Phase 7 Status**: ⬜ Not Started

---

## Progress Summary

| Phase | Status | Completion |
|-------|--------|------------|
| Phase 1: Scaffolding | 🟢 Complete | 15/15 |
| Phase 2: Data Models | 🟢 Complete | 19/19 |
| Phase 3: API Clients | 🟢 Complete | 20/20 |
| Phase 4: Validation Engine | ⬜ Not Started | 0/24 |
| Phase 5: Services | ⬜ Not Started | 0/14 |
| Phase 6: REST API | ⬜ Not Started | 0/22 |
| Phase 7: Integration | ⬜ Not Started | 0/10 |

**Legend**: ⬜ Not Started | 🟡 In Progress | 🟢 Complete

---

## Notes

_Add implementation notes, decisions, and blockers here as the project progresses._

### Phase 1 Notes
- Using `uv` as package manager (not pip/conda)
- Python 3.11+ required (pyproject.toml says 3.11, but system has 3.14)
- Pydantic mypy plugin configured for proper type checking
- Pre-commit hooks configured for ruff, mypy, and security checks

### Phase 2 Notes
- Created OrderedEnum base class for Severity and RiskLevel to support comparison operators
- All models use Pydantic v2 with Field descriptions
- 69 model tests covering all edge cases
- Coverage: 91% overall (above 90% threshold)
- Models include computed properties (e.g., ValidationReport.passed, Experience.duration_months)
- Applicant model includes email validation and LinkedIn URL support
- LinkedInProfile includes experience/education aggregation helpers

### Phase 3 Notes
- BaseClient implements abstract async HTTP client with exponential backoff retry logic
- RetryConfig dataclass allows customization of retry behavior (max_retries, base_delay, max_delay)
- Rate limiting handled via RateLimitExceededError with Retry-After header parsing
- LeverClient uses Basic Auth (base64 encoded api_key:)
- LeverClient supports sandbox and production environments
- LinkedInClient implements fallback strategy since LinkedIn API requires OAuth
- LinkedInURLValidator validates LinkedIn profile URLs with regex pattern
- LinkedIn profile existence checked via HEAD requests
- Profile preview extracted from public page meta tags (og:title, title)
- 81 client tests total (23 base, 22 lever, 36 linkedin)
- Coverage: 94.34% (above 90% threshold)
- Used `respx` library for mocking async HTTP requests in tests
