"""
ConsultBae Task 1 -- merge 3 messy CSVs into one SQLite database.

HOW MATCHING WORKS (read this before you touch anything):

  There is no single ID shared by all 3 files:
    - source1 (naukri)      has: email + phone
    - source2 (gig_workers) has: email only
    - source3 (cbnexus)     has: phone only

  So we match in two tiers:
    TIER 1 (strong):  normalized email match   -> links naukri <-> gig_workers
                       normalized phone match   -> links naukri <-> cbnexus
    TIER 2 (fallback): normalized full_name + normalized city match
                       -> used for pairs that share NO strong key at all
                          (e.g. gig_workers <-> cbnexus), and for cases like
                          alt-email duplicates within the same source.

  We use a union-find (disjoint set) over every raw row from all 3 files.
  Any two rows that match on a Tier-1 key, OR on the Tier-2 fallback key,
  get unioned into the same cluster. Each final cluster = one person.

  Every match is logged with WHICH rule fired, so the data-issues report
  below is generated from what the code actually did, not written by hand.
"""
import csv
import io
import json
import re
import sqlite3
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher

DATA_DIR = "/home/claude/consultbae/data"
DB_PATH = "/home/claude/consultbae/app/consultbae.db"
SCHEMA_PATH = "/home/claude/consultbae/app/schema.sql"
ISSUES_LOG = []  # collected as we go -> written to data_issues_report.md


def log_issue(category, detail):
    ISSUES_LOG.append((category, detail))
    print(f"[ISSUE:{category}] {detail}")


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

CITY_ALIASES = {
    "bengaluru": "Bengaluru", "bangalore": "Bengaluru",
    "gurgaon": "Gurugram", "gurugram": "Gurugram",
    "noida": "Noida",
    "pune": "Pune",
    "delhi": "New Delhi", "new delhi": "New Delhi",
    # "Delhi NCR" is a region, not a city -- we can't know if it means
    # Delhi/Gurugram/Noida. We keep it as its own bucket rather than
    # guessing, and flag it in the report.
    "delhi ncr": "Delhi NCR (ambiguous region)",
}


def norm_city(raw):
    if not raw or not raw.strip():
        return None
    key = re.sub(r"\s+", " ", raw.strip().lower())
    mapped = CITY_ALIASES.get(key)
    if not mapped:
        log_issue("unmapped_city", f"City value '{raw}' not in alias table, kept as-is")
        return raw.strip().title()
    return mapped


def norm_email(raw):
    if not raw or not raw.strip():
        return None
    return raw.strip().lower()


def norm_phone(raw):
    """Strip everything but digits, then take the last 10 (Indian mobile length)."""
    if not raw or not str(raw).strip():
        return None
    digits = re.sub(r"\D", "", str(raw))
    if len(digits) < 10:
        log_issue("bad_phone", f"Phone '{raw}' has fewer than 10 digits, skipped")
        return None
    return digits[-10:]


def norm_name(raw):
    if not raw:
        return None
    return re.sub(r"\s+", " ", raw.strip().lower())


def norm_ctc(raw):
    """
    Task1 CTC column mixes two units in the SAME column:
      - plain rupees, e.g. 417964
      - lakhs, e.g. 4.2  (meaning 4.2 lakh = 420000)
    Heuristic: if the value is small (< 100) it's almost certainly lakhs
    (nobody's CTC is Rs 100/year); otherwise it's already rupees.
    This is an ASSUMPTION -- documented, not hidden.
    """
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None, None
    if val < 100:
        return int(round(val * 100000)), "lakhs"
    return int(round(val)), "rupees"


def norm_date(raw):
    """Applied Date shows up in at least 4 formats. Try each, normalize to YYYY-MM-DD."""
    if not raw or not raw.strip():
        return None
    raw = raw.strip()
    formats = ["%d-%m-%Y", "%Y-%m-%d", "%d %b %Y", "%m/%d/%Y", "%d/%m/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    log_issue("bad_date", f"Applied Date '{raw}' didn't match any known format, left NULL")
    return None


def norm_rate_to_monthly(raw):
    """
    ASSUMPTION documented in README: hourly workers are assumed to work
    ~160 hrs/month (20 days x 8 hrs) to make hourly and monthly rates
    comparable. This is a business assumption, not a data fact.
    """
    if not raw:
        return None
    raw = raw.strip().lower()
    m = re.match(r"([\d.]+)\s*/\s*hr", raw)
    if m:
        return int(round(float(m.group(1)) * 160))
    m = re.match(r"([\d.]+)\s*k\s*/\s*month", raw)
    if m:
        return int(round(float(m.group(1)) * 1000))
    log_issue("bad_rate", f"Rate '{raw}' didn't match /hr or k/month pattern")
    return None


def norm_status(raw):
    if not raw:
        return None
    return raw.strip().lower()


def norm_verified(raw):
    if raw is None:
        return None
    v = str(raw).strip().lower()
    if v in ("y", "yes"):
        return 1
    if v in ("n", "no"):
        return 0
    log_issue("bad_verified", f"Verified value '{raw}' not in Y/N/yes/No, left NULL")
    return None


def split_skills(raw):
    if not raw:
        return []
    return [s.strip().lower() for s in raw.split(",") if s.strip()]


def name_city_key(name, city):
    if not name or not city:
        return None
    return f"{norm_name(name)}|{city.lower()}"


# ---------------------------------------------------------------------------
# Step 1: Read each source, cleaning known structural problems as we go
# ---------------------------------------------------------------------------

def read_source1():
    """Naukri applicants. Also dedupes exact-email repeats within the file itself."""
    rows = []
    seen_emails = {}
    with open(f"{DATA_DIR}/source1_naukri_applicants.csv", newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f)):
            email = norm_email(row["Email"])
            if email and email in seen_emails:
                log_issue(
                    "duplicate_row_same_source",
                    f"source1 row {i} ('{row['Full Name']}') has the same email as an "
                    f"earlier row ('{seen_emails[email]}') -- likely the same person "
                    f"entered twice (e.g. name typo 'R. Verma' vs 'Rohit Verma'). Merged.",
                )
            else:
                seen_emails[email] = row["Full Name"]
            rows.append(row)
    print(f"source1: read {len(rows)} rows")
    return rows


def read_source2():
    """
    Gig workers. Known structural problems handled here:
      - one fully blank row -> dropped
      - one row whose columns are shifted (skill_tags ended up in col 0) -> repaired
    """
    raw_text = open(f"{DATA_DIR}/source2_gig_workers.csv", encoding="utf-8").read()
    reader = csv.reader(io.StringIO(raw_text))
    header = next(reader)
    rows = []
    for i, cells in enumerate(reader):
        if all(c.strip() == "" for c in cells):
            log_issue("blank_row", f"source2 row {i} is entirely blank, dropped")
            continue
        # A well-formed row's first cell is an email (contains '@').
        # The shifted row we found has skill_tags (contains a comma-joined
        # list, no '@') in the first cell instead.
        if "@" not in cells[0]:
            log_issue(
                "shifted_columns",
                f"source2 row {i} has columns shifted left by one "
                f"(skill_tags ended up first): {cells}. Repaired by rotating fields back.",
            )
            cells = cells[1:] + cells[:1]
        row = dict(zip(header, cells))
        rows.append(row)
    print(f"source2: read {len(rows)} usable rows")
    return rows


def read_source3():
    """
    CBNexus contacts. Known structural problem: the file is two exports
    concatenated together, so the header row ('Name,Phone Number,...')
    appears a second time partway through the file. We detect and drop it.
    """
    rows = []
    with open(f"{DATA_DIR}/source3_cbnexus_contacts.csv", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        for i, cells in enumerate(reader):
            if cells == header:
                log_issue(
                    "embedded_duplicate_header",
                    f"source3 row {i} repeats the header row -- file is two exports "
                    f"concatenated together, dropped the extra header.",
                )
                continue
            rows.append(dict(zip(header, cells)))
    print(f"source3: read {len(rows)} usable rows")
    return rows


# ---------------------------------------------------------------------------
# Step 2: Union-Find clustering across all rows from all 3 sources
# ---------------------------------------------------------------------------

class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def build_person_clusters(s1, s2, s3):
    uf = UnionFind()
    # unique row ids
    ids1 = [f"s1_{i}" for i in range(len(s1))]
    ids2 = [f"s2_{i}" for i in range(len(s2))]
    ids3 = [f"s3_{i}" for i in range(len(s3))]
    for rid in ids1 + ids2 + ids3:
        uf.find(rid)

    match_reason = {}  # row_id -> strongest reason it was linked to its cluster ('email'/'phone'/'name_city')

    # index by strong keys
    email_index = defaultdict(list)  # email -> [(source, idx, row_id)]
    phone_index = defaultdict(list)
    namecity_index = defaultdict(list)

    for i, row in enumerate(s1):
        rid = f"s1_{i}"
        e = norm_email(row.get("Email"))
        p = norm_phone(row.get("Phone"))
        c = norm_city(row.get("City"))
        nc = name_city_key(row.get("Full Name"), c) if c else None
        if e:
            email_index[e].append(rid)
        if p:
            phone_index[p].append(rid)
        if nc:
            namecity_index[nc].append(rid)

    for i, row in enumerate(s2):
        rid = f"s2_{i}"
        e = norm_email(row.get("email_id"))
        c = norm_city(row.get("location"))
        nc = name_city_key(row.get("worker_name"), c) if c else None
        if e:
            email_index[e].append(rid)
        if nc:
            namecity_index[nc].append(rid)

    for i, row in enumerate(s3):
        rid = f"s3_{i}"
        p = norm_phone(row.get("Phone Number"))
        c = norm_city(row.get("City"))
        nc = name_city_key(row.get("Name"), c) if c else None
        if p:
            phone_index[p].append(rid)
        if nc:
            namecity_index[nc].append(rid)

    # Tier 1: union everything sharing a normalized email
    # (only mark rows as "matched via email" when the key was actually
    # shared by >1 row -- a unique email isn't a match reason for anyone)
    for e, ids in email_index.items():
        if len(ids) > 1:
            for rid in ids:
                match_reason[rid] = "email"
        for other in ids[1:]:
            uf.union(ids[0], other)
            log_issue("match_email", f"{ids[0]} <-> {other} matched on email '{e}'")

    # Tier 1: union everything sharing a normalized phone
    for p, ids in phone_index.items():
        if len(ids) > 1:
            for rid in ids:
                match_reason.setdefault(rid, "phone")
        for other in ids[1:]:
            uf.union(ids[0], other)
            log_issue("match_phone", f"{ids[0]} <-> {other} matched on phone '...{p[-4:]}'")

    # Tier 2 fallback: union everything sharing normalized name+city, but
    # this is the WEAKEST signal -- it's what connects source2 (no phone)
    # to source3 (no email), and also catches same-person/different-email
    # cases like the alt.* email. We only record it as the reason for rows
    # that had no stronger (email/phone) signal already.
    for nc, ids in namecity_index.items():
        if len(ids) > 1:
            for rid in ids:
                match_reason.setdefault(rid, "name_city")
        for other in ids[1:]:
            uf.union(ids[0], other)
            log_issue("match_name_city", f"{ids[0]} <-> {other} matched on name+city '{nc}'")

    return uf, ids1, ids2, ids3, match_reason


# ---------------------------------------------------------------------------
# Step 3: Build person records from clusters, write to SQLite
# ---------------------------------------------------------------------------

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(open(SCHEMA_PATH).read())
    cur = conn.cursor()

    s1 = read_source1()
    s2 = read_source2()
    s3 = read_source3()

    uf, ids1, ids2, ids3, match_reason = build_person_clusters(s1, s2, s3)

    row_by_id = {}
    for i, row in enumerate(s1):
        row_by_id[f"s1_{i}"] = ("naukri", row)
    for i, row in enumerate(s2):
        row_by_id[f"s2_{i}"] = ("gig_workers", row)
    for i, row in enumerate(s3):
        row_by_id[f"s3_{i}"] = ("cbnexus", row)

    clusters = defaultdict(list)
    for rid in row_by_id:
        clusters[uf.find(rid)].append(rid)

    print(f"\n{len(row_by_id)} raw rows collapsed into {len(clusters)} unique people\n")

    # ---- Conflict check: did the WEAK (name+city) fallback merge rows
    # that actually carry different phone numbers or different emails?
    # That's a red flag -- it means two different real people who happen
    # to share a name+city may have been merged into one. We don't reverse
    # it automatically (we don't know which is right), we just surface it
    # loudly so a human decides.
    for root, member_ids in clusters.items():
        phones, emails = set(), set()
        for rid in member_ids:
            source, row = row_by_id[rid]
            if source == "naukri":
                if row.get("Phone"):
                    phones.add(norm_phone(row["Phone"]))
                if row.get("Email"):
                    emails.add(norm_email(row["Email"]))
            elif source == "gig_workers" and row.get("email_id"):
                emails.add(norm_email(row["email_id"]))
            elif source == "cbnexus" and row.get("Phone Number"):
                phones.add(norm_phone(row["Phone Number"]))
        phones.discard(None)
        emails.discard(None)
        if len(phones) > 1 or len(emails) > 1:
            names = {row_by_id[rid][1].get("Full Name") or row_by_id[rid][1].get("worker_name")
                     or row_by_id[rid][1].get("Name") for rid in member_ids}
            log_issue(
                "POSSIBLE_OVER_MERGE",
                f"Cluster for {names} was merged by name+city fallback but contains "
                f"CONFLICTING identifiers -- phones={phones or 'n/a'}, emails={emails or 'n/a'}. "
                f"This may be two different people with the same name in the same city, "
                f"incorrectly merged. Left merged (no way to tell which is right from the "
                f"data alone) but flagged here for manual review.",
            )

    for root, member_ids in clusters.items():
        # Pick a canonical name: prefer naukri > cbnexus > gig_workers,
        # and prefer a longer/title-cased version over an ALLCAPS one.
        candidates = []
        email, phone, city = None, None, None
        for rid in member_ids:
            source, row = row_by_id[rid]
            if source == "naukri":
                candidates.append(row["Full Name"])
                email = email or norm_email(row.get("Email"))
                phone = phone or norm_phone(row.get("Phone"))
                city = city or norm_city(row.get("City"))
            elif source == "gig_workers":
                candidates.append(row["worker_name"])
                email = email or norm_email(row.get("email_id"))
                city = city or norm_city(row.get("location"))
            elif source == "cbnexus":
                candidates.append(row["Name"])
                phone = phone or norm_phone(row.get("Phone Number"))
                city = city or norm_city(row.get("City"))

        candidates = [c for c in candidates if c]
        canonical_name = sorted(candidates, key=lambda n: (n == n.upper(), -len(n)))[0]
        canonical_name = " ".join(w.capitalize() for w in canonical_name.split())

        cur.execute(
            "INSERT INTO people (full_name, email, phone, city) VALUES (?,?,?,?)",
            (canonical_name, email, phone, city),
        )
        person_id = cur.lastrowid

        for rid in member_ids:
            source, row = row_by_id[rid]
            method = match_reason.get(rid, "unmatched") if len(member_ids) > 1 else "unmatched"
            cur.execute(
                "INSERT INTO source_records (person_id, source_name, raw_row_json, match_method) "
                "VALUES (?,?,?,?)",
                (person_id, source, json.dumps(row), method),
            )

            if source == "naukri":
                for sk in split_skills(row.get("Skills")):
                    cur.execute(
                        "INSERT OR IGNORE INTO skills (person_id, skill) VALUES (?,?)",
                        (person_id, sk),
                    )
                ctc, unit = norm_ctc(row.get("Current CTC"))
                cur.execute(
                    "INSERT INTO naukri_applications "
                    "(person_id, experience_years, current_ctc_inr, ctc_unit_assumed, applied_date) "
                    "VALUES (?,?,?,?,?)",
                    (
                        person_id,
                        float(row["Experience (Years)"]) if row.get("Experience (Years)") else None,
                        ctc,
                        unit,
                        norm_date(row.get("Applied Date")),
                    ),
                )
            elif source == "gig_workers":
                for sk in split_skills(row.get("skill_tags")):
                    cur.execute(
                        "INSERT OR IGNORE INTO skills (person_id, skill) VALUES (?,?)",
                        (person_id, sk),
                    )
                cur.execute(
                    "INSERT INTO gig_worker_profiles (person_id, rate_raw, rate_monthly_inr, status) "
                    "VALUES (?,?,?,?)",
                    (
                        person_id,
                        row.get("rate"),
                        norm_rate_to_monthly(row.get("rate")),
                        norm_status(row.get("status")),
                    ),
                )
            elif source == "cbnexus":
                cur.execute(
                    "INSERT INTO cbnexus_contacts (person_id, verified, projects_completed) "
                    "VALUES (?,?,?)",
                    (
                        person_id,
                        norm_verified(row.get("Verified")),
                        int(row["Projects Completed"]) if row.get("Projects Completed") else None,
                    ),
                )

    conn.commit()

    # sanity summary
    cur.execute("SELECT COUNT(*) FROM people")
    n_people = cur.fetchone()[0]
    cur.execute(
        "SELECT source_name, COUNT(*) FROM source_records GROUP BY source_name"
    )
    print(f"\nFinal: {n_people} people in the database")
    for name, count in cur.fetchall():
        print(f"  {name}: {count} source rows folded in")

    conn.close()
    write_issues_report()


def write_issues_report():
    by_category = defaultdict(list)
    for cat, detail in ISSUES_LOG:
        by_category[cat].append(detail)

    lines = ["# Data Issues Report (auto-generated from pipeline log)\n"]
    lines.append(
        "Every issue below was actually caught by `merge.py` while running -- "
        "this file is generated from `ISSUES_LOG`, not written by hand.\n"
    )
    for cat, items in sorted(by_category.items()):
        lines.append(f"\n## {cat} ({len(items)} occurrences)\n")
        for item in items[:20]:
            lines.append(f"- {item}")
        if len(items) > 20:
            lines.append(f"- ...and {len(items) - 20} more")

    with open("/home/claude/consultbae/exports/data_issues_report.md", "w") as f:
        f.write("\n".join(lines))
    print("\nWrote exports/data_issues_report.md")


if __name__ == "__main__":
    main()
