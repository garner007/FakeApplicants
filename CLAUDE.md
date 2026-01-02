# Lever-LinkedIn Applicant Validator

## Project Overview

A Python-based applicant validation system that integrates with Lever (ATS) and LinkedIn APIs to identify potentially fraudulent job applicants. The system reads applicant data from Lever, enriches it with LinkedIn profile data, and applies configurable validation rules to flag suspicious applications.

---

## Project Goals

1. **Primary Goal**: Build an extensible applicant validation pipeline that detects fake/fraudulent job applicants
2. **Integration**: Seamlessly connect Lever ATS and LinkedIn APIs
3. **Extensibility**: Design a plugin-based architecture for easy addition of new validation rules
4. **Quality**: Maintain 90%+ test coverage with TDD methodology
5. **Scalability**: Support future React/Next.js frontend integration

---

## Architecture

### High-Level System Design

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Frontend (Future)                              │
│                         React / Next.js                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            REST API Layer                                │
│                         FastAPI / Flask                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Orchestration Layer                              │
│                    ApplicantValidationService                            │
└─────────────────────────────────────────────────────────────────────────┘
                    │                               │
                    ▼                               ▼
┌───────────────────────────────┐   ┌───────────────────────────────┐
│      Integration Layer         │   │      Validation Engine         │
│  ┌─────────────────────────┐  │   │  ┌─────────────────────────┐  │
│  │    LeverClient          │  │   │  │   ValidationRule (ABC)  │  │
│  │    - get_applicants()   │  │   │  │   - validate()          │  │
│  │    - get_applicant()    │  │   │  │   - get_name()          │  │
│  │    - get_opportunities()│  │   │  │   - get_severity()      │  │
│  └─────────────────────────┘  │   │  └─────────────────────────┘  │
│  ┌─────────────────────────┐  │   │              │                │
│  │    LinkedInClient       │  │   │              ▼                │
│  │    - get_profile()      │  │   │  ┌─────────────────────────┐  │
│  │    - search_person()    │  │   │  │  Concrete Rules:        │  │
│  │    - get_connections()  │  │   │  │  - LinkedInExistsRule   │  │
│  └─────────────────────────┘  │   │  │  - ProfileConsistency   │  │
└───────────────────────────────┘   │  │  - EmploymentHistoryRule│  │
                                    │  │  - (Extensible...)      │  │
                                    │  └─────────────────────────┘  │
                                    └───────────────────────────────┘
                                                    │
                                                    ▼
                                    ┌───────────────────────────────┐
                                    │        Data Layer             │
                                    │  ┌─────────────────────────┐  │
                                    │  │   Models / DTOs         │  │
                                    │  │   - Applicant           │  │
                                    │  │   - LinkedInProfile     │  │
                                    │  │   - ValidationResult    │  │
                                    │  │   - ValidationReport    │  │
                                    │  └─────────────────────────┘  │
                                    │  ┌─────────────────────────┐  │
                                    │  │   Repository (Future)   │  │
                                    │  │   - PostgreSQL/SQLite   │  │
                                    │  └─────────────────────────┘  │
                                    └───────────────────────────────┘
```

### Directory Structure

```
lever-linkedin-applicant-validator/
├── CLAUDE.md                    # This file - project specification
├── README.md                    # User-facing documentation
├── pyproject.toml               # Project configuration & dependencies
├── pytest.ini                   # Pytest configuration
├── .env.example                 # Environment variable template
├── .env                         # Local environment variables (gitignored)
├── .gitignore
│
├── src/
│   └── applicant_validator/
│       ├── __init__.py
│       ├── config.py            # Configuration management
│       │
│       ├── clients/             # External API integrations
│       │   ├── __init__.py
│       │   ├── base.py          # Base client abstract class
│       │   ├── lever.py         # Lever API client
│       │   └── linkedin.py      # LinkedIn API client
│       │
│       ├── models/              # Data models / DTOs
│       │   ├── __init__.py
│       │   ├── applicant.py     # Applicant data model
│       │   ├── linkedin.py      # LinkedIn profile model
│       │   └── validation.py    # Validation result models
│       │
│       ├── validators/          # Validation rules (plugin architecture)
│       │   ├── __init__.py
│       │   ├── base.py          # Abstract base validator
│       │   ├── registry.py      # Validator registration/discovery
│       │   ├── linkedin_exists.py
│       │   ├── profile_consistency.py
│       │   ├── employment_history.py
│       │   └── ... (extensible)
│       │
│       ├── services/            # Business logic orchestration
│       │   ├── __init__.py
│       │   ├── applicant_service.py
│       │   └── validation_service.py
│       │
│       └── api/                 # REST API (FastAPI)
│           ├── __init__.py
│           ├── main.py          # FastAPI app entry point
│           ├── routes/
│           │   ├── __init__.py
│           │   ├── applicants.py
│           │   └── validations.py
│           └── schemas/         # Pydantic request/response schemas
│               ├── __init__.py
│               └── ...
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared fixtures
│   │
│   ├── unit/                    # Unit tests (mocked dependencies)
│   │   ├── __init__.py
│   │   ├── clients/
│   │   │   ├── test_lever.py
│   │   │   └── test_linkedin.py
│   │   ├── validators/
│   │   │   ├── test_linkedin_exists.py
│   │   │   ├── test_profile_consistency.py
│   │   │   └── ...
│   │   └── services/
│   │       ├── test_applicant_service.py
│   │       └── test_validation_service.py
│   │
│   ├── integration/             # Integration tests (sandbox APIs)
│   │   ├── __init__.py
│   │   ├── test_lever_client.py
│   │   └── test_linkedin_client.py
│   │
│   └── fixtures/                # Test data fixtures
│       ├── lever_responses/
│       │   ├── applicant.json
│       │   └── opportunities.json
│       └── linkedin_responses/
│           └── profile.json
│
└── scripts/
    ├── setup_sandbox.py         # Sandbox environment setup
    └── seed_test_data.py        # Seed test data to sandboxes
```

---

## Technology Stack

### Backend
- **Python 3.11+**
- **FastAPI** - REST API framework
- **Pydantic v2** - Data validation and settings management
- **httpx** - Async HTTP client for API calls
- **python-dotenv** - Environment variable management

### Testing
- **pytest** - Test framework
- **pytest-cov** - Coverage reporting
- **pytest-asyncio** - Async test support
- **pytest-mock** - Mocking utilities
- **responses** or **respx** - HTTP request mocking
- **factory-boy** - Test data factories
- **hypothesis** - Property-based testing (optional)

### Development Tools
- **ruff** - Linting and formatting
- **mypy** - Static type checking
- **pre-commit** - Git hooks

### Future Frontend
- **React 18+**
- **Next.js 14+**
- **TypeScript**
- **TailwindCSS**

---

## API Integration Details

### Lever API

**Documentation**: https://hire.lever.co/developer/documentation

**Sandbox Environment**:
- Lever provides a sandbox environment for testing
- Request sandbox access at: https://hire.lever.co/developer/sandbox
- Sandbox base URL: `https://api.sandbox.lever.co/v1`
- Production base URL: `https://api.lever.co/v1`

**Authentication**:
- API Key authentication (Basic Auth with API key as username, empty password)
- OAuth 2.0 also available for production

**Key Endpoints**:
```
GET  /opportunities                    # List all opportunities (job postings)
GET  /opportunities/{id}               # Get specific opportunity
GET  /opportunities/{id}/applications  # Get applications for opportunity
GET  /candidates                       # List all candidates
GET  /candidates/{id}                  # Get specific candidate
```

**Rate Limits**:
- 10 requests per second
- Implement exponential backoff

**Required Scopes**:
- `candidates:read`
- `opportunities:read`
- `applications:read`

### LinkedIn API

**Documentation**: https://learn.microsoft.com/en-us/linkedin/

**Sandbox/Testing**:
- LinkedIn uses "Development" mode for testing
- Apply for API access via LinkedIn Developer Portal: https://www.linkedin.com/developers/
- Development apps have limited data access
- For profile data, need Marketing Developer Platform or Talent Solutions Partner access

**Authentication**:
- OAuth 2.0 (3-legged for user data, 2-legged for some endpoints)

**Relevant APIs**:
1. **Profile API** (requires Member Data Portability or specific partnership)
   - `GET /v2/me` - Get authenticated user profile

2. **People Search** (Talent Solutions only)
   - Requires LinkedIn Recruiter or Talent Solutions license

3. **Alternative: Data scraping concerns**
   - LinkedIn has strict anti-scraping policies
   - Consider using verified LinkedIn URL validation only initially

**Important Considerations**:
- LinkedIn API access is heavily restricted
- Full profile data requires partnership agreements
- Initial implementation may be limited to:
  - Validating LinkedIn URL format
  - Checking if LinkedIn URL returns 200 (public profile exists)
  - Matching name from Lever to LinkedIn public profile name

**Fallback Strategy**:
If full LinkedIn API access unavailable:
1. Validate LinkedIn URL format
2. HTTP HEAD request to check URL validity
3. Use profile preview data if available
4. Flag for manual review if LinkedIn verification needed

---

## Data Models

### Applicant (from Lever)

```python
@dataclass
class Applicant:
    id: str
    name: str
    email: str
    phone: str | None
    linkedin_url: str | None
    resume_url: str | None
    location: str | None
    company: str | None
    headline: str | None
    sources: list[str]
    created_at: datetime
    opportunity_id: str
    stage: str

    # Enriched data
    linkedin_profile: LinkedInProfile | None = None
```

### LinkedInProfile

```python
@dataclass
class LinkedInProfile:
    id: str
    url: str
    name: str
    headline: str | None
    location: str | None
    current_company: str | None
    connections_count: int | None
    profile_picture_url: str | None
    experience: list[Experience]
    education: list[Education]
    skills: list[str]

    # Metadata
    is_public: bool
    last_fetched: datetime
```

### ValidationResult

```python
@dataclass
class ValidationResult:
    rule_name: str
    passed: bool
    severity: Severity  # LOW, MEDIUM, HIGH, CRITICAL
    message: str
    details: dict[str, Any]

class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
```

### ValidationReport

```python
@dataclass
class ValidationReport:
    applicant_id: str
    applicant_name: str
    timestamp: datetime
    results: list[ValidationResult]
    overall_score: float  # 0-100, higher = more trustworthy
    risk_level: RiskLevel  # LOW, MEDIUM, HIGH
    flags: list[str]

    @property
    def passed(self) -> bool:
        return self.risk_level != RiskLevel.HIGH
```

---

## Validation Rules System

### Base Validator Interface

```python
from abc import ABC, abstractmethod

class ValidationRule(ABC):
    """Base class for all validation rules."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this rule."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this rule checks."""
        pass

    @property
    @abstractmethod
    def severity(self) -> Severity:
        """Default severity level for failures."""
        pass

    @abstractmethod
    async def validate(
        self,
        applicant: Applicant,
        linkedin_profile: LinkedInProfile | None
    ) -> ValidationResult:
        """Execute validation and return result."""
        pass

    @property
    def requires_linkedin(self) -> bool:
        """Whether this rule requires LinkedIn data."""
        return False
```

### Planned Validation Rules

#### Phase 1 (MVP)

1. **LinkedInExistsRule**
   - Severity: MEDIUM
   - Check: Applicant has a LinkedIn URL that resolves
   - Flags: Missing LinkedIn, invalid URL, 404 response

2. **NameConsistencyRule**
   - Severity: HIGH
   - Check: Name on application matches LinkedIn profile name
   - Flags: Significant name mismatches (allows for nicknames/abbreviations)

3. **EmailDomainRule**
   - Severity: LOW
   - Check: Email domain reputation and validity
   - Flags: Disposable email domains, suspicious patterns

#### Phase 2 (Enhanced)

4. **EmploymentHistoryRule**
   - Severity: MEDIUM
   - Check: Current company on application matches LinkedIn
   - Flags: Company mismatch, no current employment listed

5. **ProfileAgeRule**
   - Severity: MEDIUM
   - Check: LinkedIn profile age and activity
   - Flags: Very new profiles (<6 months), low connection count

6. **LocationConsistencyRule**
   - Severity: LOW
   - Check: Location on application matches LinkedIn location
   - Flags: Major geographic discrepancies

7. **SkillsRelevanceRule**
   - Severity: LOW
   - Check: LinkedIn skills align with job requirements
   - Flags: No relevant skills for position

#### Phase 3 (Advanced)

8. **DuplicateApplicantRule**
   - Severity: HIGH
   - Check: Multiple applications with similar data patterns
   - Flags: Same LinkedIn, similar emails, matching phone numbers

9. **ProfilePictureRule**
   - Severity: MEDIUM
   - Check: Profile picture exists and passes AI detection
   - Flags: No picture, stock photo, AI-generated face

10. **ResumeConsistencyRule**
    - Severity: HIGH
    - Check: Resume content matches LinkedIn profile
    - Flags: Conflicting dates, different companies, mismatched education

### Adding New Rules

New validation rules should:

1. Inherit from `ValidationRule` base class
2. Implement all abstract methods
3. Include comprehensive unit tests
4. Be registered in the `ValidatorRegistry`
5. Have clear documentation

```python
# Example: Adding a new rule
# File: src/applicant_validator/validators/new_rule.py

from .base import ValidationRule, ValidationResult, Severity

class NewCustomRule(ValidationRule):
    @property
    def name(self) -> str:
        return "new_custom_rule"

    @property
    def description(self) -> str:
        return "Description of what this rule validates"

    @property
    def severity(self) -> Severity:
        return Severity.MEDIUM

    async def validate(self, applicant, linkedin_profile) -> ValidationResult:
        # Implementation
        pass

# Register in validators/__init__.py or via decorator
```

---

## Testing Strategy

### TDD Workflow

**CRITICAL**: All code must be developed using Test-Driven Development:

1. **Write Test First**: Before any implementation, write a failing test
2. **Run Test (Red)**: Confirm the test fails
3. **Implement Code**: Write minimal code to pass the test
4. **Run Test (Green)**: Confirm the test passes
5. **Refactor**: Clean up code while keeping tests green
6. **Repeat**: Continue for next piece of functionality

### Test Categories

#### Unit Tests (`tests/unit/`)
- Test individual components in isolation
- Mock all external dependencies
- Fast execution (<1 second per test)
- Target: 90%+ coverage

```python
# Example: Unit test for LeverClient
class TestLeverClient:
    async def test_get_applicants_success(self, mock_httpx):
        # Arrange
        mock_httpx.get("/candidates").respond(200, json=FIXTURE_DATA)
        client = LeverClient(api_key="test")

        # Act
        applicants = await client.get_applicants()

        # Assert
        assert len(applicants) == 2
        assert applicants[0].name == "John Doe"
```

#### Integration Tests (`tests/integration/`)
- Test against sandbox APIs
- Verify actual API contract compliance
- Run separately from unit tests
- Marked with `@pytest.mark.integration`

```python
@pytest.mark.integration
class TestLeverClientIntegration:
    async def test_fetch_real_applicants(self, sandbox_client):
        applicants = await sandbox_client.get_applicants(limit=5)
        assert len(applicants) <= 5
        for applicant in applicants:
            assert applicant.id is not None
```

#### End-to-End Tests (`tests/e2e/`) - Future
- Full workflow testing
- API endpoint testing
- Frontend integration (when added)

### Test Fixtures

Use realistic test data fixtures:

```python
# tests/conftest.py
@pytest.fixture
def sample_applicant():
    return Applicant(
        id="abc123",
        name="John Doe",
        email="john.doe@example.com",
        linkedin_url="https://linkedin.com/in/johndoe",
        # ...
    )

@pytest.fixture
def sample_linkedin_profile():
    return LinkedInProfile(
        id="xyz789",
        url="https://linkedin.com/in/johndoe",
        name="John Doe",
        # ...
    )
```

### Coverage Requirements

- Minimum overall coverage: 90%
- Critical paths (validators, clients): 95%+
- Run coverage with: `pytest --cov=src --cov-report=html`

---

## Configuration

### Environment Variables

```bash
# .env.example

# Lever API Configuration
LEVER_API_KEY=your_lever_api_key
LEVER_ENVIRONMENT=sandbox  # sandbox | production
LEVER_SANDBOX_URL=https://api.sandbox.lever.co/v1
LEVER_PRODUCTION_URL=https://api.lever.co/v1

# LinkedIn API Configuration
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret
LINKEDIN_REDIRECT_URI=http://localhost:8000/callback
LINKEDIN_ENVIRONMENT=development  # development | production

# Application Configuration
APP_ENV=development
LOG_LEVEL=DEBUG
API_HOST=0.0.0.0
API_PORT=8000

# Feature Flags
ENABLE_LINKEDIN_INTEGRATION=true
ENABLE_ADVANCED_VALIDATORS=false
```

### Configuration Management

```python
# src/applicant_validator/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Lever
    lever_api_key: str
    lever_environment: str = "sandbox"

    # LinkedIn
    linkedin_client_id: str
    linkedin_client_secret: str

    # App
    app_env: str = "development"
    log_level: str = "INFO"

    @property
    def lever_base_url(self) -> str:
        if self.lever_environment == "sandbox":
            return "https://api.sandbox.lever.co/v1"
        return "https://api.lever.co/v1"

    class Config:
        env_file = ".env"
```

---

## Development Phases

### Phase 1: Foundation (Week 1-2)

- [ ] Project scaffolding and configuration
- [ ] Data models (Applicant, LinkedInProfile, ValidationResult)
- [ ] Lever API client with full test coverage
- [ ] Basic LinkedIn URL validation
- [ ] 3 core validation rules

**Deliverables**:
- Working Lever integration (sandbox)
- Unit tests for all components
- Basic validation pipeline

### Phase 2: LinkedIn Integration (Week 3-4)

- [ ] LinkedIn API client (or alternative approach)
- [ ] Profile enrichment service
- [ ] Enhanced validation rules
- [ ] Validation orchestration service

**Deliverables**:
- LinkedIn profile fetching (based on API access)
- 5+ validation rules
- End-to-end validation workflow

### Phase 3: API Layer (Week 5-6)

- [ ] FastAPI REST endpoints
- [ ] Request/response schemas
- [ ] Error handling and logging
- [ ] API documentation (OpenAPI)

**Deliverables**:
- Complete REST API
- Interactive API docs
- Integration test suite

### Phase 4: Production Readiness (Week 7-8)

- [ ] Production configuration
- [ ] Monitoring and alerting
- [ ] Rate limiting and caching
- [ ] Performance optimization

**Deliverables**:
- Production deployment guide
- Monitoring dashboards
- Performance benchmarks

### Phase 5: Frontend (Future)

- [ ] Next.js project setup
- [ ] API integration
- [ ] Dashboard UI
- [ ] Applicant review workflow

---

## API Endpoints (Planned)

### Applicants

```
GET    /api/v1/applicants                 # List applicants from Lever
GET    /api/v1/applicants/{id}            # Get specific applicant
POST   /api/v1/applicants/{id}/validate   # Run validation on applicant
GET    /api/v1/applicants/{id}/report     # Get validation report
```

### Validations

```
GET    /api/v1/validations                # List all validation rules
GET    /api/v1/validations/{rule}         # Get rule details
POST   /api/v1/validations/batch          # Batch validate multiple applicants
```

### Reports

```
GET    /api/v1/reports                    # List validation reports
GET    /api/v1/reports/{id}               # Get specific report
GET    /api/v1/reports/summary            # Dashboard summary statistics
```

---

## Error Handling

### Custom Exceptions

```python
class ApplicantValidatorError(Exception):
    """Base exception for all application errors."""
    pass

class LeverAPIError(ApplicantValidatorError):
    """Lever API related errors."""
    pass

class LinkedInAPIError(ApplicantValidatorError):
    """LinkedIn API related errors."""
    pass

class ValidationError(ApplicantValidatorError):
    """Validation processing errors."""
    pass

class ConfigurationError(ApplicantValidatorError):
    """Configuration/setup errors."""
    pass
```

### HTTP Error Responses

```python
{
    "error": {
        "code": "LEVER_API_ERROR",
        "message": "Failed to fetch applicants from Lever",
        "details": {
            "status_code": 429,
            "retry_after": 60
        }
    }
}
```

---

## Logging

Use structured logging throughout:

```python
import structlog

logger = structlog.get_logger()

# Example usage
logger.info(
    "applicant_validated",
    applicant_id=applicant.id,
    rules_passed=10,
    rules_failed=2,
    risk_level="medium"
)
```

---

## Security Considerations

1. **API Keys**: Never commit API keys; use environment variables
2. **Data Privacy**: Handle applicant PII according to regulations
3. **Rate Limiting**: Implement rate limiting on API endpoints
4. **Input Validation**: Validate all inputs using Pydantic
5. **HTTPS**: All API communications must use HTTPS
6. **Audit Logging**: Log all validation actions for audit trail

---

## Commands Reference

Use `make help` to see all available commands. Key commands:

```bash
# Installation
make install              # Install production dependencies
make install-dev          # Install all dependencies including dev tools

# Testing
make test                 # Run all tests
make test-unit            # Run unit tests only
make test-integration     # Run integration tests only (requires API credentials)
make test-cov             # Run tests with coverage report
make test-cov-check       # Run tests and fail if coverage < 90%

# Code Quality
make lint                 # Run ruff linter
make lint-fix             # Run ruff linter with auto-fix
make format               # Format code with ruff
make typecheck            # Run mypy type checker
make check                # Run all checks (lint, typecheck, test)
make check-all            # Run all checks including format and coverage

# Running the Application
make run                  # Run the API server
make dev                  # Run the API server with auto-reload

# Cleanup
make clean                # Remove build artifacts and cache files

# Development Utilities
make deps-update          # Update all dependencies to latest versions
make pre-commit-install   # Install pre-commit hooks
```

### Direct Commands (without Make)

```bash
# Run tests directly
uv run pytest tests/unit -v
uv run pytest -k "test_lever"    # Run specific tests
uv run pytest -x                 # Stop on first failure

# Run application with specific environment
APP_ENV=production uv run uvicorn applicant_validator.api.main:app
```

---

## Getting Started

1. **Clone and setup**:
   ```bash
   git clone <repo>
   cd lever-linkedin-applicant-validator
   python -m venv venv
   source venv/bin/activate
   pip install -e ".[dev]"
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API credentials
   ```

3. **Request sandbox access**:
   - Lever: https://hire.lever.co/developer/sandbox
   - LinkedIn: https://www.linkedin.com/developers/

4. **Run tests**:
   ```bash
   pytest
   ```

5. **Start development**:
   - Follow TDD workflow
   - Write test first, then implementation
   - Maintain 90%+ coverage

---

## Notes for Claude Code

When working on this project:

1. **Always write tests first** - This is non-negotiable
2. **Update PROJECT_PLAN.md** - Mark tasks complete as you finish them
3. **Check test coverage** after each implementation (must be 90%+)
4. **Use type hints** on all functions and methods
5. **Follow the directory structure** defined above
6. **Use async/await** for all I/O operations
7. **Document public APIs** with docstrings
8. **Keep validators modular** - each rule in its own file
9. **Mock external APIs** in unit tests
10. **Use fixtures** for test data
11. **Run linting** before committing (`make check`)
