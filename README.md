# Lever-LinkedIn Applicant Validator

A fraud detection system that integrates with Lever ATS and LinkedIn to identify potentially fraudulent job applicants. Built for HR teams to catch applicants using cloned or stolen identities while using their own email address.

## The Problem

Fraudulent job applicants are becoming increasingly sophisticated. They clone real people's LinkedIn profiles and resumes but use their own email addresses. This system automates detection by:

- Cross-referencing applicant data from Lever with LinkedIn profiles
- Running extensible validation rules to detect inconsistencies
- Flagging suspicious applicants with risk scores
- Providing a review dashboard for HR teams

## Features

- **Lever Integration** - Fetch and process applicants from your Lever ATS
- **LinkedIn Verification** - Validate applicant profiles against LinkedIn data
- **Extensible Validation Rules** - Plugin architecture for custom fraud detection rules
- **Risk Scoring** - Automated risk assessment (low/medium/high/critical)
- **Review Dashboard** - Next.js frontend for reviewing flagged applicants
- **Audit Logging** - Full audit trail for compliance
- **TDD Approach** - 90%+ test coverage with 200+ tests

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                        │
│    ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐   │
│    │  Dashboard Home │  │  Applicant List │  │ Detail Page  │   │
│    │  (Statistics)   │  │  (Table + Sort) │  │ (Flags/Review)│   │
│    └─────────────────┘  └─────────────────┘  └──────────────┘   │
└────────────────────────────────┬────────────────────────────────┘
                                 │ HTTP/REST
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│    ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐   │
│    │  REST API       │  │  Validation     │  │  External    │   │
│    │  /api/v1/       │  │  Engine         │  │  API Clients │   │
│    └────────┬────────┘  └────────┬────────┘  └──────┬───────┘   │
│             │                    │                   │           │
│             ▼                    ▼                   ▼           │
│    ┌─────────────────────────────────────────────────────────┐  │
│    │              Async SQLAlchemy ORM Layer                 │  │
│    └─────────────────────────────┬───────────────────────────┘  │
└──────────────────────────────────┬──────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PostgreSQL Database                          │
│    ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐   │
│    │ applicants│  │  flags    │  │ linkedin_ │  │ validation│   │
│    │           │  │           │  │ profiles  │  │ _runs     │   │
│    └───────────┘  └───────────┘  └───────────┘  └───────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Tech Stack

### Backend
- **Python 3.11+** with async/await
- **FastAPI** - REST API framework
- **SQLAlchemy 2.0** - Async ORM
- **PostgreSQL 16** - Primary database
- **Alembic** - Database migrations
- **Pydantic** - Data validation
- **httpx** - Async HTTP client

### Frontend
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **shadcn/ui** - UI components
- **Jest + React Testing Library** - Testing

### Development
- **uv** - Fast Python package manager
- **Docker Compose** - Local development environment
- **ruff** - Linting and formatting
- **mypy** - Static type checking
- **pre-commit** - Git hooks

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- uv package manager (`pip install uv`)

### 1. Clone and Setup

```bash
git clone https://github.com/yourorg/applicant-validator.git
cd applicant-validator

# Install Python dependencies
uv sync

# Install frontend dependencies
cd frontend && npm install && cd ..

# Copy environment config
cp .env.example .env
# Edit .env with your credentials
```

### 2. Start Database

```bash
# Start PostgreSQL
make docker-up

# Run migrations
make db-upgrade

# Seed flag types and sample data
make db-seed
```

### 3. Run the Application

```bash
# Terminal 1: Start API server
make dev

# Terminal 2: Start frontend
make frontend-dev
```

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Frontend**: http://localhost:3000

## Project Structure

```
├── src/applicant_validator/
│   ├── api/                    # FastAPI application
│   │   ├── main.py            # App entrypoint
│   │   ├── routes/            # API endpoints
│   │   │   └── applicants.py  # Applicant CRUD
│   │   └── schemas/           # Pydantic models
│   ├── clients/               # External API clients
│   │   ├── lever.py          # Lever ATS client
│   │   └── linkedin.py       # LinkedIn API client
│   ├── database/              # Database layer
│   │   ├── models.py         # SQLAlchemy models
│   │   └── base.py           # Session management
│   ├── validators/            # Validation rules
│   │   ├── base.py           # Abstract base rule
│   │   ├── email_rules.py    # Email validation
│   │   └── phone_rules.py    # Phone validation
│   └── services/              # Business logic
│
├── frontend/
│   └── src/
│       ├── app/               # Next.js pages
│       │   ├── page.tsx      # Dashboard home
│       │   └── applicants/
│       │       └── [id]/     # Applicant detail
│       ├── components/        # React components
│       │   ├── ui/           # shadcn components
│       │   └── applicants-table.tsx
│       └── lib/               # Utilities
│           ├── api.ts        # API client
│           └── types.ts      # TypeScript types
│
├── tests/                     # Backend tests
│   ├── unit/                  # Unit tests
│   └── integration/           # Integration tests
│
├── alembic/                   # Database migrations
├── scripts/                   # Utility scripts
│   ├── seed_flag_types.py    # Seed flag types
│   └── seed_applicants.py    # Seed fake data
│
└── Makefile                   # Development commands
```

## Database Schema

### Core Tables

| Table | Description |
|-------|-------------|
| `applicants` | Applicant records from Lever with validation summary |
| `flags` | Individual fraud flags raised for applicants |
| `flag_types` | Lookup table of configurable flag definitions |
| `linkedin_profiles` | Cached LinkedIn profile data |
| `validation_runs` | Audit trail of validation executions |
| `validation_results` | Individual rule results per run |
| `audit_logs` | System-wide audit trail |

### Key Fields

**Applicant**
- `lever_id` - Unique ID from Lever ATS
- `risk_level` - Computed risk (low/medium/high/critical)
- `validation_score` - Numeric fraud score (0-100)
- `flag_count` - Denormalized count of active flags
- `is_reviewed` - Whether HR has reviewed this applicant

**Flag**
- `flag_type_id` - References configurable flag type
- `severity` - info/low/medium/high/critical
- `message` - Human-readable explanation
- `is_active` - Soft delete support

## Validation Rules

Rules are Python classes extending `ValidationRule`:

```python
from applicant_validator.validators.base import ValidationRule, Severity

class MyCustomRule(ValidationRule):
    name = "my_custom_rule"
    description = "Description of what this rule checks"
    severity = Severity.MEDIUM

    async def validate(self, applicant, linkedin_profile):
        # Your validation logic
        # Return ValidationResult with pass/fail and message
        pass
```

### Built-in Rules

| Rule | Category | Severity | Description |
|------|----------|----------|-------------|
| `voip_phone` | phone | medium | Detects VoIP numbers (Google Voice, etc.) |
| `disposable_email` | email | high | Checks for disposable email domains |
| `linkedin_exists` | linkedin | medium | Verifies LinkedIn profile URL is valid |
| `name_consistency` | identity | high | Name matches across platforms |
| `profile_age` | linkedin | medium | Profile creation date vs experience |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/applicants` | List applicants with pagination/filtering |
| GET | `/api/v1/applicants/{id}` | Get applicant with flags |
| PATCH | `/api/v1/applicants/{id}` | Update review status |
| POST | `/api/v1/applicants/{id}/validate` | Trigger validation run |
| GET | `/api/v1/applicants/{id}/report` | Get validation report |

### Query Parameters (List)

- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20, max: 100)
- `sort_by` - Field to sort: created_at, name, risk_level, flag_count
- `sort_order` - asc or desc
- `risk_level` - Filter by risk level
- `is_reviewed` - Filter by review status (true/false)

## Development Commands

### Installation
```bash
make install          # Install production deps
make install-dev      # Install with dev tools
make frontend-install # Install frontend deps
```

### Testing
```bash
make test             # Run all backend tests
make test-unit        # Run unit tests only
make test-cov         # Run with coverage report
make frontend-test    # Run frontend tests
```

### Code Quality
```bash
make lint             # Run ruff linter
make format           # Format code
make typecheck        # Run mypy
make check            # Run all checks
make pre-commit-run   # Run pre-commit hooks
```

### Running
```bash
make dev              # API with hot reload
make frontend-dev     # Frontend dev server
make run              # Production API server
```

### Database
```bash
make docker-up        # Start PostgreSQL
make docker-down      # Stop all services
make db-upgrade       # Apply migrations
make db-downgrade     # Rollback migration
make db-seed          # Seed all data
```

### Dev Container
```bash
make dev-shell        # Open shell in container
make dev-api          # Run API in container
make dev-db-upgrade   # Migrate in container
make dev-test         # Test in container
```

## Environment Variables

Create `.env` from `.env.example`:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/applicant_validator

# Lever API
LEVER_API_KEY=your_lever_api_key
LEVER_SANDBOX=true

# LinkedIn (optional)
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret

# App
DEBUG=true
LOG_LEVEL=INFO
```

## Testing

The project follows TDD with 200+ tests and 90%+ coverage.

```bash
# Run all tests
make test

# With coverage
make test-cov

# Frontend tests (14 tests for detail page)
cd frontend && npm test
```

## Roadmap

- [x] Phase 1: Core Lever integration
- [x] Phase 2: Database schema & migrations
- [x] Phase 3: REST API layer
- [x] Phase 4: Next.js frontend dashboard
- [ ] Phase 5: LinkedIn integration
- [ ] Phase 6: Visual rules builder for non-technical users
- [ ] Phase 7: Production deployment

## License

MIT
