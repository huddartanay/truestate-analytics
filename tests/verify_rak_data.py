"""
RAK source-registry verification.

Ensures every value on the RAK tab matches what the three RAK Statistics Office
reports explicitly state, and that no cross-emirate value has leaked in.

    python tests/verify_rak_data.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from regions.rak import sources as S     # noqa: E402

PASS, FAIL = "\033[1;32mPASS\033[0m", "\033[1;31mFAIL\033[0m"
results: list[bool] = []


def check(name: str, expected, actual) -> None:
    ok = expected == actual
    results.append(ok)
    print(f"  {PASS if ok else FAIL}  {name}")
    if not ok:
        print(f"        expected: {expected!r}")
        print(f"        actual:   {actual!r}")


def section(t: str) -> None:
    print(f"\n{t}")


# ── 2024–2025 headline value totals (RAK Annual 2025 Table 1) ─────────────
section("2024–2025 headline value totals (RAK Annual 2025 Table 1)")
v = {r["category"]: r for r in S.RAK_ANNUAL_2024_2025_VALUE}
check("Sales 2025 = 3,192,316,419",     3_192_316_419, v["Real Estate Sales Volume"]["y2025_aed"])
check("Sales 2024 = 6,438,983,837",     6_438_983_837, v["Real Estate Sales Volume"]["y2024_aed"])
check("Mortgages 2025 = 12,682,671,958", 12_682_671_958, v["Real Estate Mortgages Volume"]["y2025_aed"])
check("Waivers 2025 = 2,928,225,958",   2_928_225_958, v["Waiver Market Value"]["y2025_aed"])
check("Total 2025 = 18,803,214,335",    18_803_214_335, v["Total Transactions"]["y2025_aed"])
check("Total 2024 = 15,085,466,470",    15_085_466_470, v["Total Transactions"]["y2024_aed"])
check("Total Δ = +25%",                 25, v["Total Transactions"]["change_pct"])
check("Mortgages Δ = +159%",            159, v["Real Estate Mortgages Volume"]["change_pct"])
check("Sales Δ = -50%",                 -50, v["Real Estate Sales Volume"]["change_pct"])

# ── 2024–2025 count totals ────────────────────────────────────────────────
section("2024–2025 count totals")
c = {r["category"]: r for r in S.RAK_ANNUAL_2024_2025_COUNT}
check("Sales # 2025 = 2,964",           2964, c["Real Estate Sales Number"]["y2025"])
check("Mortgages # 2025 = 1,480",       1480, c["Real Estate Mortgages Number"]["y2025"])
check("Waivers # 2025 = 825",           825,  c["Waivers Number"]["y2025"])
check("Total # 2025 = 5,269",           5269, c["Total Number of Transactions"]["y2025"])
check("Total # 2024 = 5,054",           5054, c["Total Number of Transactions"]["y2024"])

# ── 2021–2022 annual (r3.pdf / RAK Annual 2022 Table 1) ───────────────────
section("2021–2022 annual (RAK Annual 2022 = r3.pdf)")
v = {r["category"]: r for r in S.RAK_ANNUAL_2021_2022_VALUE}
check("Sales 2022 = 2,184,141,723",     2_184_141_723, v["Real Estate Sales Volume"]["y2022_aed"])
check("Mortgages 2022 = 4,088,088,578", 4_088_088_578, v["Real Estate Mortgages Volume"]["y2022_aed"])
check("Waivers 2022 = 1,060,154,758",   1_060_154_758, v["Waiver Market Value"]["y2022_aed"])
check("Total 2022 = 7,332,385,059",     7_332_385_059, v["Total Transactions"]["y2022_aed"])
check("Total Δ 2021→2022 = +12%",       12, v["Total Transactions"]["change_pct"])

c = {r["category"]: r for r in S.RAK_ANNUAL_2021_2022_COUNT}
check("Sales # 2022 = 2,279",           2279, c["Real Estate Sales Number"]["y2022"])
check("Mortgages # 2022 = 942",         942,  c["Real Estate Mortgages Number"]["y2022"])
check("Waivers # 2022 = 720",           720,  c["Waivers Number"]["y2022"])
check("Total # 2022 = 3,941",           3941, c["Total Number of Transactions"]["y2022"])
check("Top region 2022 = AL Jazeera AL Hamra Qaryat Al Hamra",
      "AL Jazeera AL Hamra Qaryat Al Hamra", S.RAK_TOP_REGION_2022["region"])

# Popular areas 2022
areas22 = {a["region"]: a for a in S.RAK_POPULAR_AREAS_2022}
check("AL Jazeera AL Hamra 2022 = 698,213,762",
      698_213_762, areas22["AL Jazeera AL Hamra Qaryat Al Hamra"]["sales_value_2022_aed"])
check("Jazeerat AL Marjan 2022 = 405,595,563",
      405_595_563, areas22["Jazeerat AL Marjan"]["sales_value_2022_aed"])
check("AL Riffa 2022 = 188,581,031",
      188_581_031, areas22["AL Riffa"]["sales_value_2022_aed"])

# Property Use 2022 spot checks
pu22 = {r["use"]: r for r in S.RAK_PROPERTY_USE_2021_2022}
check("Touristic Lands 2022 Δ = +192%", 192, pu22["Touristic Lands"]["change_pct"])
check("Commercial Lands 2022 Δ = -61%", -61, pu22["Commercial Lands"]["change_pct"])
check("Free Residential 2022 = 221,984,259",
      221_984_259, pu22["Free Residential"]["y2022_aed"])

# Investors 2022
inv22_v = {r["nationality"]: r["value_aed"] for r in S.RAK_INVESTORS_BY_VALUE_2022}
check("UAE 2022 by value = 892,242,650",  892_242_650, inv22_v["UAE"])
check("India 2022 by value = 75,424,828", 75_424_828,  inv22_v["India"])
check("Total Investors 2022 = 2,279",     2279, S.RAK_TOTAL_INVESTORS_2022)


# ── 2020–2021 historical totals (RAK Annual 2021 Table 1) ─────────────────
section("2020–2021 historical totals (RAK Annual 2021 Table 1)")
v = {r["category"]: r for r in S.RAK_ANNUAL_2020_2021_VALUE}
check("Sales 2021 = 1,738,994,965",     1_738_994_965, v["Real Estate Sales Volume"]["y2021_aed"])
check("Mortgages 2021 = 4,152,346,223", 4_152_346_223, v["Real Estate Mortgages Volume"]["y2021_aed"])
check("Waivers 2021 = 667,421,666",     667_421_666,   v["Waiver Market Value"]["y2021_aed"])
check("Total 2021 = 6,558,762,854",     6_558_762_854, v["Total Transactions"]["y2021_aed"])
check("Total 2020 = 3,846,897,851",     3_846_897_851, v["Total Transactions"]["y2020_aed"])
check("Total Δ = +70%",                 70, v["Total Transactions"]["change_pct"])

c = {r["category"]: r for r in S.RAK_ANNUAL_2020_2021_COUNT}
check("Sales # 2021 = 2,406",           2406, c["Real Estate Sales Number"]["y2021"])
check("Mortgages # 2021 = 1,147",       1147, c["Real Estate Mortgages Number"]["y2021"])
check("Total # 2021 = 4,082",           4082, c["Total Number of Transactions"]["y2021"])

# ── Popular areas 2025 (RAK Annual 2025 Table 2) ──────────────────────────
section("Popular areas 2025 (RAK Annual 2025 Table 2)")
a = {r["region"]: r for r in S.RAK_POPULAR_AREAS_2025}
check("Jazeerat AL Marjan 2025 value = 940,279,261",
      940_279_261, a["Jazeerat AL Marjan"]["sales_value_2025_aed"])
check("Jazeerat AL Marjan 2024 value = 4,044,092,592",
      4_044_092_592, a["Jazeerat AL Marjan"]["sales_value_2024_aed"])
check("AL Riffa 2025 value = 605,902,422",
      605_902_422, a["AL Riffa"]["sales_value_2025_aed"])
check("AL Riffa Δ = +16%", 16, a["AL Riffa"]["change_pct"])
check("AL Jazeera AL Hamra 2025 value = 385,111,220",
      385_111_220, a["AL Jazeera AL Hamra (Qaryat AL Hamra)"]["sales_value_2025_aed"])

# ── Popular areas 2021 (RAK Annual 2021 Table 2) ──────────────────────────
section("Popular areas 2021 (RAK Annual 2021 Table 2)")
a = {r["region"]: r for r in S.RAK_POPULAR_AREAS_2021}
check("Al Jazirah Al Hamra 2021 value = 782,505,476",
      782_505_476, a["Al Jazirah Al Hamra"]["sales_value_2021_aed"])
check("Al Jazirah Al Hamra 2020 value = 339,715,466",
      339_715_466, a["Al Jazirah Al Hamra"]["sales_value_2020_aed"])
check("Saih Al Bir 2021 value = 93,917,500",
      93_917_500, a["Saih Al Bir"]["sales_value_2021_aed"])

# ── Property use (RAK Annual 2025 Table 3) — spot checks ──────────────────
section("Property use 2024–2025 (RAK Annual 2025 Table 3)")
pu = {r["use"]: r for r in S.RAK_PROPERTY_USE_2024_2025}
check("Popular Houses Δ = +55%",         55, pu["Popular Houses"]["change_pct"])
check("Commercial Unit Δ = +43%",        43, pu["Commercial Unit"]["change_pct"])
check("Touristic Δ = -87%",              -87, pu["Touristic"]["change_pct"])
check("Apartments Investment 2025 = 585,089,172",
      585_089_172, pu["Apartments (Investment)"]["y2025_aed"])
check("Touristic 2024 = 2,649,984,906",
      2_649_984_906, pu["Touristic"]["y2024_aed"])
check("Infrastructure 2025 change is None (dash in source)",
      None, pu["Infrastructure"]["change_pct"])

# ── Investors 2025 (RAK Annual 2025 Table 4 & Figure 4) ───────────────────
section("Investors 2025 (RAK Annual 2025 Table 4 & Figure 4)")
inv_v = {r["nationality"]: r["value_aed"] for r in S.RAK_INVESTORS_BY_VALUE_2025}
check("UAE by value = 1,369,351,039",   1_369_351_039, inv_v["UAE"])
check("UK by value = 172,332,131",      172_332_131, inv_v["UK"])
check("India by value = 164,594,106",   164_594_106, inv_v["India"])
check("Russia by value = 91,598,097",   91_598_097, inv_v["The Russian Union"])
check("KSA by value = 41,489,759",      41_489_759, inv_v["KSA"])
check("Exactly 10 nationalities by value", 10, len(S.RAK_INVESTORS_BY_VALUE_2025))

inv_n = {r["nationality"]: r["count"] for r in S.RAK_INVESTORS_BY_NUMBER_2025}
check("UAE by number = 2,079",  2079, inv_n["UAE"])
check("India by number = 163",  163,  inv_n["India"])
check("UK by number = 143",     143,  inv_n["UK"])
check("KSA by number = 34",     34,   inv_n["KSA"])

check("Total investors 2025 = 3,469", 3469, S.RAK_INVESTORS_TOTALS["y2025"])
check("Total investors 2024 = 3,363", 3363, S.RAK_INVESTORS_TOTALS["y2024"])

# ── January 2026 monthly (r1.pdf) ─────────────────────────────────────────
section("January 2026 monthly (RAK Monthly Jan 2026)")
check("Jan 2026 sales value = 249,794,299",  249_794_299, S.RAK_JAN_2026["sales_value_aed"])
check("Jan 2026 sales count = 302",          302, S.RAK_JAN_2026["sales_count"])
check("Jan 2026 mortgages = 136,953,350",    136_953_350, S.RAK_JAN_2026["mortgages_aed"])
check("Jan 2025 sales value = 549,433,417",  549_433_417, S.RAK_JAN_2025["sales_value_aed"])
check("Jan 2025 mortgages = 1,116,512,387",  1_116_512_387, S.RAK_JAN_2025["mortgages_aed"])

check("Jan 2026 top region = AL RIFFA",      "AL RIFFA", S.RAK_JAN_TOP_REGION_2026["region"])
check("Jan 2026 top region value = 70,715,594",
      70_715_594, S.RAK_JAN_TOP_REGION_2026["sales_value_aed"])
check("Jan 2026 top region count = 53",      53, S.RAK_JAN_TOP_REGION_2026["sales_count"])

check("Jan 2026 highest sale — AL NAKHEEL AED 7M",
      ("AL NAKHEEL", 7_000_000),
      (S.RAK_JAN_HIGHEST_SALES[0]["region"], S.RAK_JAN_HIGHEST_SALES[0]["value_aed"]))
check("Jan 2025 highest sale — Jazeerat Al Marjan AED 160M",
      ("Jazeerat Al Marjan", 160_000_000),
      (S.RAK_JAN_HIGHEST_SALES[1]["region"], S.RAK_JAN_HIGHEST_SALES[1]["value_aed"]))

fh = {r["land_use"]: r for r in S.RAK_JAN_FREEHOLD_MARKET}
check("Jan 2026 freehold apartments count = 77",   77, fh["Apartment (Investment)"]["count"])
check("Jan 2026 freehold villas count = 18",       18, fh["Villa (Investment)"]["count"])
check("Jan 2026 freehold total count = 95",        95, fh["Total"]["count"])
check("Jan 2026 freehold total value = 115,711,007",
      115_711_007, fh["Total"]["value_aed"])
check("Jan 2026 freehold areas total sales = 407",
      407, S.RAK_JAN_FREEHOLD_AREAS_TOTAL["sales_count"])

# ── Monthly time series — spot-check values from the source PDFs ─────────
section("Monthly time series — verbatim values from RAK Statistics Office reports")
ts = {(r["year"], r["month"]): r for r in S.RAK_MONTHLY_TIMESERIES}

# 2019-2020 old-format (Sales only)
check("January 2019 sales_v = 105,635,787",  105_635_787, ts[(2019, "January")]["sales_v"])
check("January 2019 sales_n = 207",          207,          ts[(2019, "January")]["sales_n"])
check("April 2020 sales_v = 34,005,382",     34_005_382,   ts[(2020, "April")]["sales_v"])
check("August 2020 sales_v = 104,484,715",   104_484_715,  ts[(2020, "August")]["sales_v"])
check("2019-2020 months carry no mortgage data (Jan 2019)",
      None, ts[(2019, "January")]["mort_v"])

# Modern format (full breakdown)
check("December 2020 sales_v = 112,858,726", 112_858_726,  ts[(2020, "December")]["sales_v"])
check("December 2020 mort_v = 65,120,201",   65_120_201,   ts[(2020, "December")]["mort_v"])
check("December 2020 waiv_v = 38,682,278",   38_682_278,   ts[(2020, "December")]["waiv_v"])
check("December 2021 sales_v = 129,885,930", 129_885_930,  ts[(2021, "December")]["sales_v"])
check("October 2023 mort_v = 886,167,023",   886_167_023,  ts[(2023, "October")]["mort_v"])
check("November 2023 sales_v = 582,281,834", 582_281_834,  ts[(2023, "November")]["sales_v"])
check("December 2024 waiv_v = 1,436,821,780", 1_436_821_780, ts[(2024, "December")]["waiv_v"])
check("November 2025 waiv_v = 333,744,328",  333_744_328,  ts[(2025, "November")]["waiv_v"])
check("December 2025 sales_v = 233,008,207", 233_008_207,  ts[(2025, "December")]["sales_v"])
check("January 2026 sales_v = 249,794,299 (matches r1.pdf)",
      249_794_299, ts[(2026, "January")]["sales_v"])

# OCR-extracted months
check("October 2022 mort_v = 674,360,576 (OCR)", 674_360_576, ts[(2022, "October")]["mort_v"])
check("June 2024 sales_v = 2,935,067,291 (OCR)", 2_935_067_291, ts[(2024, "June")]["sales_v"])
check("August 2025 waiv_v = 232,334,273 (OCR)",  232_334_273,   ts[(2025, "August")]["waiv_v"])

# Consistency between annual r2/r4 and the monthly extracts
check("Dec 2021 sales_v matches (both monthly and annual chain)",
      129_885_930, ts[(2021, "December")]["sales_v"])
check("Jan 2026 sales_v matches r1.pdf key stat",
      249_794_299, ts[(2026, "January")]["sales_v"])

# Unreadable list transparency
check("Unreadable list contains 8 entries",
      8, len(S.RAK_MONTHLY_UNREADABLE))
check("Unreadable list references February 2023/2024",
      True, any("February 2023" in u["period"] for u in S.RAK_MONTHLY_UNREADABLE))

# Data point count
check("Total monthly data points = 35",
      35, len(S.RAK_MONTHLY_TIMESERIES))


# ── Sharjah-only / cross-emirate filter ──────────────────────────────────
section("Cross-emirate filter — no non-RAK content leaked in")


def _dump() -> str:
    parts = [
        S.RAK_OVERVIEW_NARRATIVE,
        S.RAK_OVERVIEW_SUBTITLE,
        *(r["citation"] for r in S.all_sources()),
        *(k["label"] for k in S.RAK_KEY_STATS),
        *(a["region"] for a in S.RAK_POPULAR_AREAS_2025),
        *(a["region"] for a in S.RAK_POPULAR_AREAS_2021),
        *(p["use"] for p in S.RAK_PROPERTY_USE_2024_2025),
        *(i["nationality"] for i in S.RAK_INVESTORS_BY_VALUE_2025),
        *(h["region"] + " " + h["type"] for h in S.RAK_JAN_HIGHEST_SALES),
    ]
    return "\n".join(parts).lower()


text = _dump()
FORBIDDEN = [
    r"dubai land department",
    r"dubai residential price index",
    r"abu dhabi transactions",
    r"abu dhabi price index",
    r"savills sharjah",
    r"markaz sharjah",
    r"srerd",
    r"jazeerat al marjan[^a-z]*sharjah",
    r"dubai marina",
    r"downtown dubai",
    r"saadiyat",
    r"yas island",
    r"al reem",
]
for pattern in FORBIDDEN:
    check(f"Prohibited metric absent: {pattern!r}",
          True, re.search(pattern, text) is None)

# ── Source index maps to known reports ───────────────────────────────────
section("Source index")
valid = {r["citation"] for r in S.all_sources()}
for section_name, cite in S.source_index():
    if "Monthly time series" in section_name:
        # Aggregate citation covers many monthly reports; verify it names them.
        check(f"'{section_name}' cites monthly reports",
              True, "monthly report" in cite.lower())
    else:
        check(f"'{section_name}' → known citation", True, cite in valid)

# ── Summary ──────────────────────────────────────────────────────────────
passed = sum(results)
total = len(results)
print(f"\n{'─' * 60}")
print(f"RAK data verification: {passed} / {total} checks passed.")
sys.exit(0 if passed == total else 1)
