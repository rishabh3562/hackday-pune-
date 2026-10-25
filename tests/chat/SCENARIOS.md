# Scenarios from the mentor / friend discussion (suite 3): 10 core + 19 extended

Together with the 18 given and the 22 extra scenarios, the **10 core** ones here make the **50 core scenarios** (18 + 22 + 10). The other 19 are extended tests (all 29 run and pass). These are stateful (memory is reset per scenario) and check the hard parts the
mentor raised. Expected values are computed independently from the raw files in `tests/chat/run.py`. Run: `.venv/bin/python -u tests/chat/run.py`.

| ID | Set | What it tests | Mentor / friend point |
|---|---|---|---|
| S1 | **core** | One correction ("add 6 °C to all manual readings in an area between two dates") changes every matched row and the area answer | One feedback applies to many rows |
| S2 | **core** | "Undo my last correction" restores the originals; the record stays as `revoked` in the audit log | Reversibility, audit |
| S3 | extended | A newer correction on the same selector supersedes the older (+5, not +8) | Correction lifecycle |
| S4 | extended | A well/inspection-level value beats an area-wide shift (most specific scope wins) | Conflicting feedback, precedence |
| S5 | **core** | "All T200 wells: RCA after 4 repairs" changes only T200 (T350 stays 3), applied in a new chat | Rules scoped to a well type |
| S6 | extended | "All the readings are wrong" with no scope records nothing and asks | Safety: never rewrite the fleet by accident |
| S7 | **core** | "The wells we discussed in April" resolves a 6-month-old conversation by timestamp | Recall months later |
| S8 | extended | "Yesterday" with nothing yesterday: uses the latest match and says so | Honest fallback |
| S9 | extended | Two different 3-well sets in history: uses the latest, lists the other set | Ambiguity |
| S10 | **core** | Another user is refused, the owner's memory is unaffected | Private memory |
| S11 | extended | A shared FYI from one user is visible to another, attributed to the author | Shared knowledge |
| S12 | **core** | "Show that as a bar chart" re-renders the last result without re-querying | Conversational chart switching |
| S13 | extended | A two-part question returns two result blocks | Several UIs in one response |
| S14 | extended | A claim that agrees with the latest inspection is stored as confirmed | Claim handling |
| S15 | **core** | "Which wells are failing due to mud?": no record says mud, so no invented matches; nearest causes offered | Concept search honesty |
| S16 | extended | Corrosion wells in an area match an independent regex over the reports | Text lifted into structure |
| S17 | extended | Related concept (sand) returns wells whose quote really says sand/scale | Synonyms |
| S18 | **core** | `trace` walks inspection -> repair -> regulator events | Graph via ID links, no graph DB |
| S19 | extended | Hybrid search: manual by name, exact protocol ID, and a paraphrase all find the right document | Why hybrid |
| S20 | extended | WELL-0007 (T350) gets 20 °C, WELL-0001 (T200) gets 15 °C, with the source | SOP/manual per well |
| S21 | extended | A second dataset root (new wells + area) loads; loading a root twice is idempotent | New test data |
| S22 | extended | Unknown well gives a graceful answer | Robustness |
| S23 | extended | `NE-8` and lower-case area names resolve to the same area | Robustness |
| S24 | extended | One user's correction is used and attributed in another user's answer | Shared corrections |
| S25 | extended | Two different 3-well sets in history: asks which (options), then answers with the chosen set | Clarification loop |
| S26 | **core** | "Show me downtime.": one short question with 2-4 options; the free-text reply completes the original request | Clarification loop |
| S27 | extended | Auto mode (no human to answer): never asks, states the assumption | Non-interactive grading |
| S28 | **core** | A change touching thousands of rows asks first; "Apply" applies, "No" records nothing | Confirm large scope |
| S29 | extended | Unknown area: asks and offers the real areas as options | Clarification options |
