# Applicant Validator System Guide

A system to validate job applicants using Lever ATS data and detect potential fraud indicators.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Components](#components)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Running the Application](#running-the-application)
7. [Validation Rules](#validation-rules)
8. [API Endpoints](#api-endpoints)

---

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Next.js        │────▶│  FastAPI        │────▶│  PostgreSQL     │
│  Frontend       │     │  Backend        │     │  Database       │
│  (Port 3000)    │     │  (Port 8000)    │     │  (Port 5432)    │
│                 │     │                 │     │                 │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │                 │
                        │  Lever API      │
                        │  (External)     │
                        │                 │
                        └─────────────────┘
```

### Data Flow

1. **Sync**: Frontend triggers sync → Backend fetches candidates from Lever API → Stores in PostgreSQL
2. **Validation**: After sync, each applicant is validated against fraud rules → Flags stored in database
3. **Display**: Frontend queries backend for applicants with their flags and risk levels

---

## Components

### Backend (Python/FastAPI)

- **Location**: `src/applicant_validator/`
- **Framework**: FastAPI with async support
- **Database**: SQLAlchemy 2.0 with asyncpg driver

Key modules:
- `api/` - REST API routes and schemas
- `clients/` - External API clients (Lever)
- `database/` - SQLAlchemy models and session management
- `validators/` - Fraud detection rules
- `services/` - Business logic (validation service)

### Frontend (Next.js/React)

- **Location**: `frontend/`
- **Framework**: Next.js 15 with App Router
- **UI Library**: shadcn/ui components
- **Styling**: Tailwind CSS

Key components:
- `app/page.tsx` - Main applicant list view
- `components/applicants-table.tsx` - Data table with sorting
- `components/sync-panel.tsx` - Lever sync controls

### Database (PostgreSQL)

- **Version**: PostgreSQL 16
- **Managed via**: Docker Compose

Key tables:
- `applicants` - Core applicant data from Lever
- `flags` - Fraud indicators detected
- `flag_types` - Types of validation rules
- `validation_runs` - Audit trail of validations
- `validation_results` - Individual rule results

---

## Prerequisites

- **Python**: 3.11 or higher
- **Node.js**: 18 or higher
- **Docker**: For PostgreSQL database
- **uv**: Python package manager (recommended)

---

## Installation

### 1. Clone and Setup Python Environment

```bash
# Clone the repository
git clone <repository-url>
cd FakeApplicants

# Create virtual environment with uv
uv venv

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Install dependencies
uv sync
```

### 2. Start PostgreSQL Database

```bash
# Start PostgreSQL container
docker compose up -d postgres

# Verify it's running
docker compose ps
```

### 3. Run Database Migrations

```bash
# Apply all migrations
uv run alembic upgrade head
```

### 4. Setup Frontend

```bash
cd frontend

# Install Node.js dependencies
npm install
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Lever API Configuration (Required)
LEVER_API_KEY=your_lever_api_key_here
LEVER_ENVIRONMENT=production  # or 'sandbox' for testing

# Database Configuration
DATABASE_URL=postgresql+asyncpg://applicant_validator:dev_password_change_me@localhost:5432/applicant_validator
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10

# Application Settings
APP_ENV=development  # development, staging, or production
LOG_LEVEL=INFO
DEBUG_MODE=false

# API Server
API_HOST=0.0.0.0
API_PORT=8000

# LinkedIn (Optional - for future integration)
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
LINKEDIN_REDIRECT_URI=http://localhost:8000/auth/linkedin/callback
```

### Docker Environment (Optional)

For Docker settings, these can be set in `.env`:

```env
POSTGRES_USER=applicant_validator
POSTGRES_PASSWORD=dev_password_change_me
POSTGRES_DB=applicant_validator
POSTGRES_PORT=5432
```

---

## Running the Application

### Development Mode

**Terminal 1 - Database:**
```bash
docker compose up -d postgres
```

**Terminal 2 - Backend API:**
```bash
source .venv/bin/activate
uv run uvicorn applicant_validator.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 3 - Frontend:**
```bash
cd frontend
npm run dev
```

Access the application:
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Using pgAdmin (Optional)

```bash
# Start with tools profile
docker compose --profile tools up -d

# Access pgAdmin
open http://localhost:5050
# Login: admin@example.com / admin
```

---

## Validation Rules

The system currently implements these fraud detection rules:

### 1. Disposable Email Rule (`disposable_email`)
- **Severity**: HIGH
- **Category**: Email
- **Description**: Detects emails from known disposable/temporary email providers
- **Examples**: mailinator.com, guerrillamail.com, 10minutemail.com

### 2. VoIP Phone Rule (`voip_phone`)
- **Severity**: MEDIUM
- **Category**: Phone
- **Description**: Detects phone numbers from VoIP carriers
- **Examples**: Google Voice, Twilio, Bandwidth, Vonage

### How Validation Works

1. When sync runs, each applicant is validated against all rules
2. Failed rules create `Flag` records with evidence
3. Applicant's `risk_level` is set based on highest severity flag:
   - CRITICAL → critical
   - HIGH → high
   - MEDIUM → medium
   - LOW/INFO → low
4. `flag_count` on applicant is updated for quick filtering

---

## API Endpoints

### Applicants

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/applicants` | List applicants (paginated) |
| GET | `/api/applicants/{id}` | Get single applicant |
| PATCH | `/api/applicants/{id}` | Update applicant (review status) |

**Query Parameters for List:**
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20)
- `sort_by` - Field to sort by (name, risk_level, flag_count, created_at)
- `sort_order` - asc or desc

### Sync

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sync/status` | Get current sync status |
| POST | `/api/sync/start` | Start a new sync |
| GET | `/api/sync/count` | Get applicant count |

**POST /api/sync/start Body:**
```json
{
  "days": 7  // Number of days to sync (1-365)
}
```

**Sync Status Response:**
```json
{
  "status": "running",      // idle, running, completed, failed
  "progress": 150,          // Current count
  "total": 500,             // Total to process
  "message": "Validating applicants...",
  "last_sync_at": "2024-01-07T12:00:00Z",
  "last_sync_count": 500,
  "error": null
}
```

---

## Troubleshooting

### Database Connection Errors

```bash
# Check if PostgreSQL is running
docker compose ps

# Restart PostgreSQL
docker compose restart postgres

# View PostgreSQL logs
docker compose logs postgres
```

### API Not Starting

```bash
# Check for port conflicts
lsof -i :8000

# Kill existing process
pkill -f uvicorn

# Verify environment
source .venv/bin/activate
uv run python -c "from applicant_validator.config import get_settings; print(get_settings().database_url)"
```

### Frontend Issues

```bash
cd frontend

# Clear cache and reinstall
rm -rf node_modules .next
npm install
npm run dev
```

### Migration Errors

```bash
# Check migration status
uv run alembic current

# Reset database (development only!)
docker compose down -v
docker compose up -d postgres
uv run alembic upgrade head
```
