"""
Sharjah — report-sourced regional market intelligence.

Unlike Dubai (which reads a live transaction dataset), Sharjah is a
REPORT-SOURCED tab. Every value on the Sharjah dashboard traces back to one
of three published research reports:

    A. Savills — Sharjah Residential Market in Minutes, Q1 2026
    B. Marmore/Markaz — UAE Real Estate Report, H2 2024 review + H1 2025 outlook
    C. Marmore/Markaz — UAE Real Estate Report, H1 2024 review + H2 2024 outlook

The `sources.py` module is the single registry driving both the dashboard and
the PDF report. Nothing here is invented, inferred from Dubai, or normalised
away from what the reports actually say.
"""
