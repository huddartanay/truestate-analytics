"""
Sharjah source-registry verification.

Ensures every value on the Sharjah tab matches what the three source reports
explicitly state, and that no Dubai / Abu Dhabi / UAE-wide value has leaked
into the Sharjah data layer.

    python tests/verify_sharjah_data.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from regions.sharjah import sources as S     # noqa: E402

PASS, FAIL = "\033[1;32mPASS\033[0m", "\033[1;31mFAIL\033[0m"
results: list[bool] = []


def check(name: str, expected, actual) -> None:
    ok = expected == actual
    results.append(ok)
    print(f"  {PASS if ok else FAIL}  {name}")
    if not ok:
        print(f"        expected: {expected!r}")
        print(f"        actual:   {actual!r}")


def section(title: str) -> None:
    print(f"\n{title}")


# ─────────────────────────────────────────────────────────────────────────────
# 1. KEY STATS — Savills Q1 2026, page 1
# ─────────────────────────────────────────────────────────────────────────────
section("Key stats (Savills Q1 2026, p.1)")
k = {kv["label"]: kv for kv in S.SHARJAH_KEY_STATS}
check("Total Transaction Value — value", "AED 18.5B", k["Total Transaction Value"]["value"])
check("Total Transaction Value — YoY",   "+40.7% year-on-year",
      k["Total Transaction Value"]["change"])
check("Total Transactions — value",      "29,235", k["Total Transactions"]["value"])
check("Total Transactions — YoY",        "+18.9% year-on-year",
      k["Total Transactions"]["change"])
check("Sales Transactions — value",      "9,978", k["Sales Transactions"]["value"])
check("Sales Transactions — YoY",        "+18.9% year-on-year",
      k["Sales Transactions"]["change"])
check("Investing Nationalities — value", "113", k["Investing Nationalities"]["value"])
check("Investing Nationalities — vs",    "vs 97 in Q1 2025",
      k["Investing Nationalities"]["change"])

# ─────────────────────────────────────────────────────────────────────────────
# 2. MONTHLY DYNAMICS — Savills Q1 2026, page 2
# ─────────────────────────────────────────────────────────────────────────────
section("Monthly dynamics (Savills Q1 2026, p.2)")
months = {m["month"]: m for m in S.SHARJAH_MONTHLY_DYNAMICS}
check("January headline",  "AED 9.3B in transactions. 10,333 deals.",
      months["January 2026"]["headline"])
check("January ACRES",     "Record January activity. ACRES exhibition drove AED 5B in sales in 4 days.",
      months["January 2026"]["note"])
check("February note",     "Escrow framework publicly launched.", months["February 2026"]["note"])
check("March headline",    "Regional tensions from 28 February introduced caution.",
      months["March 2026"]["headline"])

# ─────────────────────────────────────────────────────────────────────────────
# 3. INVESTMENT BY NATIONALITY — Savills Q1 2026, page 3
# ─────────────────────────────────────────────────────────────────────────────
section("Investment by nationality (Savills Q1 2026, p.3)")
inv = {d["label"]: d["value_aed_billion"] for d in S.SHARJAH_INVESTOR_NATIONALITY}
check("UAE Nationals — 9.0B",   9.0, inv["UAE Nationals"])
check("International — 5.3B",   5.3, inv["International"])
check("Arab Nationals — 3.4B",  3.4, inv["Arab Nationals"])
check("GCC Nationals — 0.8B",   0.8, inv["GCC Nationals"])

# ─────────────────────────────────────────────────────────────────────────────
# 4. SALES BY PROPERTY TYPE — Savills Q1 2026, page 3
# STRICT: percentages must NOT sum to 100%.
# ─────────────────────────────────────────────────────────────────────────────
section("Sales by property type (Savills Q1 2026, p.3)")
pt = {d["label"]: d["share_pct"] for d in S.SHARJAH_PROPERTY_TYPE_SHARE}
check("Residential — 78.0%",  78.0, pt["Residential"])
check("Commercial — 6.4%",     6.4, pt["Commercial"])
check("Agricultural — 3.2%",   3.2, pt["Agricultural"])
sum_pct = round(sum(pt.values()), 2)
check("Percentages NOT normalised to 100%", True, sum_pct != 100.0)

# ─────────────────────────────────────────────────────────────────────────────
# 5. TOP AREAS — Savills Q1 2026, page 3
# ─────────────────────────────────────────────────────────────────────────────
section("Top performing areas (Savills Q1 2026, p.3)")
areas = {a["area"]: (a["rank"], a["value_aed_million"]) for a in S.SHARJAH_TOP_AREAS}
check("Muwaileh Commercial rank",   1, areas["Muwaileh Commercial"][0])
check("Muwaileh Commercial value",  1700, areas["Muwaileh Commercial"][1])
check("Al Belaida value",           1100, areas["Al Belaida"][1])
check("Al Khan value",              718,  areas["Al Khan"][1])
check("Hamriyah West value",        715,  areas["Hamriyah West"][1])
check("Rawdat Al Sidr value",       568,  areas["Rawdat Al Sidr"][1])

# ─────────────────────────────────────────────────────────────────────────────
# 6. NOTABLE TRANSACTIONS — Savills Q1 2026, page 4
# ─────────────────────────────────────────────────────────────────────────────
section("Notable transactions (Savills Q1 2026, p.4)")
txn = {t["area"]: t for t in S.SHARJAH_NOTABLE_TRANSACTIONS}
check("Al Khan — Built-in land / Sale / 90M",
      ("Built-in land", "Sale", 90),
      (txn["Al Khan"]["type"], txn["Al Khan"]["transaction_type"],
       txn["Al Khan"]["value_aed_million"]))
check("Al Tay West — Vacant land / Mortgage / 240M",
      ("Vacant land", "Mortgage", 240),
      (txn["Al Tay West"]["type"], txn["Al Tay West"]["transaction_type"],
       txn["Al Tay West"]["value_aed_million"]))
check("Al Majaz 1 — Land / Mortgage / 153M",
      ("Land", "Mortgage", 153),
      (txn["Al Majaz 1"]["type"], txn["Al Majaz 1"]["transaction_type"],
       txn["Al Majaz 1"]["value_aed_million"]))

# ─────────────────────────────────────────────────────────────────────────────
# 7. NEW PROJECT REGISTRATIONS — Savills Q1 2026, page 4
# ─────────────────────────────────────────────────────────────────────────────
section("New project registrations (Savills Q1 2026, p.4)")
nps = {n["metric"]: n["value"] for n in S.SHARJAH_NEW_PROJECTS}
check("New projects registered — 7",         7,  nps["New projects registered"])
check("New freehold-eligible projects — 3",  3,  nps["New freehold-eligible projects"])
check("Total freehold projects — 47",        47, nps["Total freehold projects"])
check("ACRES 2026 sales — AED 5B in 4 days", 5,  nps["ACRES 2026 sales"])

# ─────────────────────────────────────────────────────────────────────────────
# 8. APRIL POST-Q1 — Savills Q1 2026, page 1 & page 5
# ─────────────────────────────────────────────────────────────────────────────
section("April 2026 post-Q1 (Savills Q1 2026, p.1 & p.5)")
apr = S.SHARJAH_APRIL_POST_Q1
check("April period label carries 'post-Q1'", True, "post-Q1" in apr["period"])
check("April value string",                   "AED 3.5B across 15,669 transactions",
      apr["value"])
check("April NOT included in Q1 stats",       True,
      "18.5B" not in apr["value"] and "29,235" not in apr["value"])

# ─────────────────────────────────────────────────────────────────────────────
# 9. REGULATORY LANDSCAPE — 4 items, correct sources
# ─────────────────────────────────────────────────────────────────────────────
section("Regulatory landscape")
regs = {r["title"]: r for r in S.SHARJAH_REGULATORY}
check("Escrow 37/2024 present",       True, any("37 of 2024" in t for t in regs))
check("Freehold 30/2022 present",     True, any("30 of 2022" in t for t in regs))
check("Sharjah Leasing Law 5/2024 present",
      True, any("Law No. (5) of 2024" in t for t in regs))
check("SRERD × UAE Pass present",     True, any("SRERD" in t and "UAE Pass" in t for t in regs))
check("Leasing Law source is Markaz H2/H1 25",
      S.MARKAZ_2024_25["id"],
      next(r for r in S.SHARJAH_REGULATORY if "Law No. (5)" in r["title"])["source"]["id"])
check("UAE Pass source is Markaz 2024",
      S.MARKAZ_2024["id"],
      next(r for r in S.SHARJAH_REGULATORY if "UAE Pass" in r["title"])["source"]["id"])

# ─────────────────────────────────────────────────────────────────────────────
# 10. INFRASTRUCTURE — Savills Q1 2026, page 4
# ─────────────────────────────────────────────────────────────────────────────
section("Infrastructure (Savills Q1 2026, p.4)")
infras = {i["title"]: i for i in S.SHARJAH_INFRASTRUCTURE}
check("Etihad Rail Phase 1 present",       True, any("Etihad Rail" in t for t in infras))
check("Sharjah International Airport present",
      True, any("Sharjah International Airport" in t for t in infras))
check("Airport expected capacity mentioned",
      True, "25 million" in next(i["expected"] for t, i in infras.items() if "Airport" in t))

# ─────────────────────────────────────────────────────────────────────────────
# 11. OUTLOOK — 3 forward signals from Savills
# ─────────────────────────────────────────────────────────────────────────────
section("Outlook — forward signals")
check("Exactly 3 forward signals",  3, len(S.SHARJAH_FORWARD_SIGNALS))
check("Signal 1 mentions Ramadan/regional",
      True, "Ramadan" in S.SHARJAH_FORWARD_SIGNALS[0]["text"]
             or "regional uncertainty" in S.SHARJAH_FORWARD_SIGNALS[0]["text"])
check("Signal 2 mentions escrow + freehold",
      True, "escrow" in S.SHARJAH_FORWARD_SIGNALS[1]["text"]
             and "freehold" in S.SHARJAH_FORWARD_SIGNALS[1]["text"])
check("Signal 3 mentions Etihad Rail",
      True, "Etihad Rail" in S.SHARJAH_FORWARD_SIGNALS[2]["text"])

# ─────────────────────────────────────────────────────────────────────────────
# 12. FUNDAMENTALS — Savills-listed masterplans only
# ─────────────────────────────────────────────────────────────────────────────
section("Fundamentals — masterplans")
mp_names = {m["name"] for m in S.SHARJAH_MASTERPLANS}
check("Masaar listed",           True, "Masaar" in mp_names)
check("Al Mamsha listed",        True, "Al Mamsha" in mp_names)
check("Sustainable City listed", True, "Sustainable City" in mp_names)
check("Tilal corridor listed",   True, "Tilal corridor" in mp_names)

# ─────────────────────────────────────────────────────────────────────────────
# 13. PROHIBITED CONTENT — must NOT appear anywhere in Sharjah data
# ─────────────────────────────────────────────────────────────────────────────
section("Sharjah-only filter — prohibited content must be absent")


def _dump_text() -> str:
    """Flatten every Sharjah string value so we can grep it."""
    parts = [
        S.SHARJAH_OVERVIEW_NARRATIVE,
        S.SHARJAH_OVERVIEW_SUBTITLE,
        *S.SHARJAH_NEAR_TERM,
        *S.SHARJAH_FUNDAMENTALS,
        *(m["headline"] + " " + m["note"] for m in S.SHARJAH_MONTHLY_DYNAMICS),
        *(r["title"] + " " + r["summary"] + " " + r["impact"] for r in S.SHARJAH_REGULATORY),
        *(i["title"] + " " + i["expected"] + " " + i["detail"] for i in S.SHARJAH_INFRASTRUCTURE),
        *(s["text"] for s in S.SHARJAH_FORWARD_SIGNALS),
        *(k["label"] for k in S.SHARJAH_KEY_STATS),
        *(a["area"] for a in S.SHARJAH_TOP_AREAS),
        *(t["area"] for t in S.SHARJAH_NOTABLE_TRANSACTIONS),
    ]
    return "\n".join(parts).lower()


text = _dump_text()

# Note: Savills / Markaz *narratives* legitimately name Dubai when explaining
# Sharjah's relative pricing position. That is a Sharjah insight, not Dubai
# data. We forbid Dubai/Abu Dhabi *METRICS*, not the words themselves.
FORBIDDEN_METRICS = [
    r"dubai land department",
    r"dubai residential price index",
    r"abu dhabi transactions",
    r"abu dhabi price index",
    r"adrec",
    r"al reem island",
    r"saadiyat",
    r"yas island",
    r"ajman transactions",
    r"ras al khaimah transactions",
    r"fujairah transactions",
    r"umm al quwain transactions",
    r"uae-wide gdp",
]
for pattern in FORBIDDEN_METRICS:
    check(f"Prohibited metric absent: {pattern!r}",
          True, re.search(pattern, text) is None)

# ─────────────────────────────────────────────────────────────────────────────
# 14. SOURCE INDEX — every section maps to one of the three reports
# ─────────────────────────────────────────────────────────────────────────────
section("Source index")
valid_citations = {r["citation"] for r in S.all_sources()}
for section_name, cite in S.source_index():
    check(f"'{section_name}' → known citation",
          True, cite in valid_citations)


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
passed = sum(results)
total = len(results)
print(f"\n{'─' * 60}")
print(f"Sharjah data verification: {passed} / {total} checks passed.")
sys.exit(0 if passed == total else 1)
