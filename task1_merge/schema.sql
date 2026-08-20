-- ConsultBae merged database schema
-- One row per REAL PERSON in `people`. Everything else hangs off person_id.
-- We keep the raw source values too (not just cleaned ones) so we never
-- destroy information while cleaning it -- this is what lets us defend
-- every cleaning decision later.

CREATE TABLE IF NOT EXISTS people (
    person_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name     TEXT NOT NULL,
    email         TEXT,              -- normalized (lowercase, trimmed)
    phone         TEXT,              -- normalized to last 10 digits
    city          TEXT,              -- normalized/aliased city name
    created_at    TEXT DEFAULT (datetime('now'))
);

-- Every source row that got folded into a person, kept verbatim.
-- This is our audit trail: for any person we can show exactly which
-- raw rows from which files were merged and why.
CREATE TABLE IF NOT EXISTS source_records (
    record_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id     INTEGER NOT NULL REFERENCES people(person_id),
    source_name   TEXT NOT NULL,     -- 'naukri' | 'gig_workers' | 'cbnexus'
    raw_row_json  TEXT NOT NULL,     -- original row, untouched
    match_method  TEXT NOT NULL      -- 'email' | 'phone' | 'name_city' | 'unmatched'
);

CREATE TABLE IF NOT EXISTS skills (
    person_id     INTEGER NOT NULL REFERENCES people(person_id),
    skill         TEXT NOT NULL,
    PRIMARY KEY (person_id, skill)
);

CREATE TABLE IF NOT EXISTS naukri_applications (
    person_id         INTEGER NOT NULL REFERENCES people(person_id),
    experience_years   REAL,
    current_ctc_inr     INTEGER,     -- normalized to plain rupees/year
    ctc_unit_assumed    TEXT,        -- 'lakhs' | 'rupees' -- how we interpreted the raw value
    applied_date        TEXT         -- normalized to YYYY-MM-DD
);

CREATE TABLE IF NOT EXISTS gig_worker_profiles (
    person_id           INTEGER NOT NULL REFERENCES people(person_id),
    rate_raw            TEXT,        -- original e.g. "1415/hr" or "15k/month"
    rate_monthly_inr    INTEGER,     -- normalized estimate (see README for assumption)
    status               TEXT        -- 'active' | 'inactive' | 'paused'
);

CREATE TABLE IF NOT EXISTS cbnexus_contacts (
    person_id           INTEGER NOT NULL REFERENCES people(person_id),
    verified             INTEGER,    -- 0/1
    projects_completed   INTEGER
);

-- Task 3: audio submissions
CREATE TABLE IF NOT EXISTS audio_submissions (
    submission_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id       INTEGER REFERENCES people(person_id),  -- nullable: new person via the app
    name            TEXT NOT NULL,
    phone           TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    duration_sec    REAL,
    sample_rate_hz  INTEGER,
    bitrate_kbps    REAL,
    loudness_db     REAL,
    quality_note    TEXT,
    submitted_at    TEXT DEFAULT (datetime('now'))
);
