-- Initialize applicant_validator database
-- This script runs on first container startup

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text matching

-- Grant privileges (in case we add more users later)
GRANT ALL PRIVILEGES ON DATABASE applicant_validator TO applicant_validator;
