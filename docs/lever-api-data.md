# Lever API Data Reference

This document describes the data available from the Lever ATS API and how it maps to our system.

## Table of Contents

1. [API Overview](#api-overview)
2. [Authentication](#authentication)
3. [Candidate Object](#candidate-object)
4. [Field Mapping](#field-mapping)
5. [Pagination](#pagination)
6. [Filtering Options](#filtering-options)
7. [Related Endpoints](#related-endpoints)

---

## API Overview

- **Base URLs**:
  - Production: `https://api.lever.co/v1`
  - Sandbox: `https://api.sandbox.lever.co/v1`
- **Documentation**: https://hire.lever.co/developer/documentation
- **Rate Limits**: Lever implements rate limiting; our client defaults to 10 requests/second

---

## Authentication

Lever uses HTTP Basic Authentication:

```
Authorization: Basic <base64(api_key:)>
```

Note: The password is empty, only the API key is used as the username.

---

## Candidate Object

The primary endpoint we use is `GET /candidates` which returns candidate (applicant) records.

### Full Response Example

```json
{
  "id": "b2b0c192-be1a-465b-9af1-f0c4a1069d08",
  "name": "Dennis Wilson",
  "contact": "7df3bc9b-07d4-488d-b405-cec748b9f64c",
  "headline": "Ray-I Cyber Advisors, McLane Company, Trustwave Holdings",
  "stage": "a3828c46-6dbb-404c-8b85-fa2bbcce7612",
  "confidentiality": "non-confidential",
  "location": "TX, USA",
  "phones": [
    {
      "type": "home",
      "value": "+13034336647"
    }
  ],
  "emails": [
    "dennisray86@hotmail.com"
  ],
  "links": [
    "http://www.linkedin.com/in/dennisraywilson"
  ],
  "archived": null,
  "tags": [
    "#devSecOps"
  ],
  "sources": [
    "Added manually",
    "LinkedIn"
  ],
  "stageChanges": [
    {
      "toStageId": "a3828c46-6dbb-404c-8b85-fa2bbcce7612",
      "toStageIndex": 0,
      "updatedAt": 1767714001426,
      "userId": "51420f35-cc30-426f-956a-08a3471e4414"
    }
  ],
  "origin": "sourced",
  "sourcedBy": "51420f35-cc30-426f-956a-08a3471e4414",
  "owner": "51420f35-cc30-426f-956a-08a3471e4414",
  "followers": [
    "51420f35-cc30-426f-956a-08a3471e4414",
    "d6ab40fe-012d-43af-93a1-0fe0f2083dc5"
  ],
  "applications": [],
  "createdAt": 1767714001426,
  "updatedAt": 1767714093519,
  "lastInteractionAt": 1767714056110,
  "lastAdvancedAt": 1767714001426,
  "snoozedUntil": null,
  "urls": {
    "list": "https://hire.lever.co/candidates",
    "show": "https://hire.lever.co/candidates/b2b0c192-be1a-465b-9af1-f0c4a1069d08"
  },
  "isAnonymized": false,
  "dataProtection": null
}
```

---

## Field Descriptions

### Core Identity Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string (UUID) | Unique identifier for the candidate |
| `name` | string | Full name of the candidate |
| `contact` | string (UUID) | Reference to the contact record |
| `headline` | string | Professional headline (often from LinkedIn) |
| `location` | string | Geographic location (city, state, country) |

### Contact Information

| Field | Type | Description |
|-------|------|-------------|
| `emails` | array[string] | List of email addresses |
| `phones` | array[object] | List of phone objects |
| `phones[].type` | string | Phone type: "home", "mobile", "work", "skype", "other" |
| `phones[].value` | string | Phone number (may include country code) |
| `links` | array[string] | URLs including LinkedIn, portfolio, GitHub, etc. |

### Application & Source Data

| Field | Type | Description |
|-------|------|-------------|
| `sources` | array[string] | How the candidate was sourced (e.g., "LinkedIn", "Indeed", "Referral") |
| `origin` | string | How candidate entered: "sourced", "applied", "referred", "agency", "internal" |
| `sourcedBy` | string (UUID) | User ID who sourced the candidate |
| `applications` | array | Job applications associated with this candidate |
| `tags` | array[string] | Custom tags applied to candidate |

### Pipeline & Status

| Field | Type | Description |
|-------|------|-------------|
| `stage` | string (UUID) | Current pipeline stage ID |
| `stageChanges` | array[object] | History of stage transitions |
| `stageChanges[].toStageId` | string | Stage ID moved to |
| `stageChanges[].toStageIndex` | number | Stage index in pipeline |
| `stageChanges[].updatedAt` | number | Timestamp (ms) of change |
| `stageChanges[].userId` | string | User who made the change |
| `archived` | object/null | Archive info if candidate is archived |
| `confidentiality` | string | "non-confidential" or "confidential" |

### Ownership & Collaboration

| Field | Type | Description |
|-------|------|-------------|
| `owner` | string (UUID) | User ID who owns this candidate |
| `followers` | array[string] | User IDs following this candidate |

### Timestamps

| Field | Type | Description |
|-------|------|-------------|
| `createdAt` | number | Unix timestamp (milliseconds) when created |
| `updatedAt` | number | Unix timestamp (milliseconds) of last update |
| `lastInteractionAt` | number | Unix timestamp (milliseconds) of last activity |
| `lastAdvancedAt` | number | Unix timestamp (milliseconds) of last stage advance |
| `snoozedUntil` | number/null | Timestamp if candidate is snoozed |

### URLs & Privacy

| Field | Type | Description |
|-------|------|-------------|
| `urls.list` | string | URL to candidates list in Lever UI |
| `urls.show` | string | URL to this candidate in Lever UI |
| `isAnonymized` | boolean | Whether data has been anonymized (GDPR) |
| `dataProtection` | object/null | Data protection/GDPR status info |

---

## Field Mapping

How Lever fields map to our database:

| Lever Field | Our Field | Notes |
|-------------|-----------|-------|
| `id` | `lever_id` | Stored as string |
| `name` | `name` | Direct mapping |
| `emails[0]` | `email` | First email only |
| `phones[0].value` | `phone` | First phone only |
| `location` | `location` | Direct mapping |
| `headline` | `headline` | Direct mapping |
| `links` (LinkedIn) | `linkedin_url` | Extracted if contains "linkedin.com" |
| `sources` | `applicant_sources` | Stored in child table |
| `stageChanges[-1].toStageId` | `lever_stage` | Latest stage |
| `createdAt` | `lever_created_at` | Converted to datetime |
| `opportunityIds[0]` | `lever_opportunity_id` | First opportunity |

---

## Pagination

Lever uses cursor-based pagination:

### Request

```
GET /candidates?limit=100&offset=abc123
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | number | Results per page (max 100) |
| `offset` | string | Cursor for next page |

### Response

```json
{
  "data": [...],
  "hasNext": true,
  "next": "xyz789"
}
```

| Field | Description |
|-------|-------------|
| `data` | Array of candidate objects |
| `hasNext` | Whether more results exist |
| `next` | Cursor to pass as `offset` for next page |

---

## Filtering Options

### Date Filtering

```
GET /candidates?created_at_start=1704067200000&created_at_end=1704153600000
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `created_at_start` | number | Unix timestamp (ms) - start of range |
| `created_at_end` | number | Unix timestamp (ms) - end of range |
| `updated_at_start` | number | Filter by update time |
| `updated_at_end` | number | Filter by update time |

### Status Filtering

```
GET /candidates?archived=false&confidentiality=non-confidential
```

| Parameter | Values | Description |
|-----------|--------|-------------|
| `archived` | true/false | Filter archived status |
| `confidentiality` | non-confidential, confidential | Filter by confidentiality |

### Source Filtering

```
GET /candidates?origin=applied&source=LinkedIn
```

| Parameter | Description |
|-----------|-------------|
| `origin` | Filter by origin: sourced, applied, referred, agency, internal |
| `source` | Filter by source string |

### Stage Filtering

```
GET /candidates?stage_id=abc123
```

| Parameter | Description |
|-----------|-------------|
| `stage_id` | Filter by pipeline stage UUID |

---

## Related Endpoints

### Opportunities

```
GET /opportunities
GET /opportunities/{id}
```

Opportunities represent job applications. A candidate can have multiple opportunities.

### Stages

```
GET /stages
```

Returns pipeline stages which can be used to understand `stage` and `stageChanges` values.

### Users

```
GET /users
GET /users/{id}
```

Returns user information for `owner`, `sourcedBy`, and `followers` references.

### Postings

```
GET /postings
GET /postings/{id}
```

Job postings that candidates apply to.

### Resumes/Files

```
GET /opportunities/{id}/resumes
GET /opportunities/{id}/files
```

Resumes and other files attached to an opportunity.

---

## Data Not Currently Used

The following Lever data is available but not currently imported:

| Field | Reason |
|-------|--------|
| `applications` | We use opportunities instead |
| `followers` | Not needed for validation |
| `owner` | Internal Lever user reference |
| `sourcedBy` | Internal Lever user reference |
| `dataProtection` | GDPR metadata |
| `isAnonymized` | Privacy flag |
| `archived` | We filter out archived by default |
| `tags` | Could be useful for future filtering |

---

## API Client Usage

### Basic Usage

```python
from applicant_validator.clients.lever import LeverClient
from applicant_validator.config import get_settings

settings = get_settings()
client = LeverClient(
    api_key=settings.lever_api_key,
    environment=settings.lever_environment,  # "sandbox" or "production"
)

async with client:
    # Get parsed applicants
    applicants = await client.get_applicants(limit=100)

    # Get single applicant
    applicant = await client.get_applicant("candidate-uuid")

    # Get raw API response
    response = await client._make_lever_request(
        "GET",
        "/candidates",
        params={"limit": 100, "created_at_start": 1704067200000}
    )
```

### Date Range Query

```python
import time

# Last 7 days in milliseconds
days = 7
created_at_start = int((time.time() - days * 24 * 60 * 60) * 1000)

response = await client._make_lever_request(
    "GET",
    "/candidates",
    params={
        "limit": 100,
        "created_at_start": created_at_start
    }
)
```

---

## Rate Limiting Considerations

- Lever enforces rate limits (exact limits vary by plan)
- Our client includes retry logic with exponential backoff
- Default: 10 requests/second maximum
- For large syncs (1000+ candidates), expect ~10+ API calls

---

## Future Enhancements

Potential additional data to leverage:

1. **Resume text extraction** - Parse resumes for validation
2. **Opportunity details** - Job-specific context
3. **Interview feedback** - Additional signals
4. **Custom fields** - Company-specific data
5. **Activity history** - Engagement patterns
