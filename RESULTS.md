# Final run

Data roots: data/repo/test-data/dataset. Fresh memory DB. 2026-10-17 16:58

## Q1 (Michael Turner, chat 1)
**All our wells feed one reservoir. Map the reservoir pressure across the field from the pressure data.**

No reservoir pressure data exists in the provided records. Inspections only record wellhead and ambient temperature, spill fields, and notes (125,198 inspections, 600 wells). There are no pressure columns found, and no notes mention reservoir or bottom-hole pressure. Therefore, a reservoir pressure map cannot be built from this data. The nearest alternative would be to map the wellhead-to-air temperature difference by area.

*Visual: text*

No reservoir pressure data exists: inspections record only wellhead and ambient temperature, spill fields and notes (125,198 inspections, 600 wells); pressure columns found: none; notes mentioning reservoir/bottom-hole pressure: 0. A reservoir pressure map cannot be built from this data. Nearest honest alternative: wellhead-to-air temperature difference by area.

## Q2 (Robert Hayes, chat 2)
**Which well produced the most oil in 2026?**

No oil production volumes exist in this dataset; only a weekly producing/not-producing reading per well (temperature rule). Therefore, the question "Which well produced the most oil in 2026?" cannot be answered. The closest proxy is the number of weekly inspections showing the well producing, with 45 wells tying at 55. Wells WELL-0008, WELL-0016, WELL-0017, WELL-0024, WELL-0044, WELL-0050, WELL-0051, WELL-0106, WELL-0144, and WELL-0207 all had 55 weekly inspections showing them producing in 2026.

*Visual: text*

| Well | Weekly inspections showing producing in 2026 |
|---|---|
| WELL-0008 | 55 |
| WELL-0016 | 55 |
| WELL-0017 | 55 |
| WELL-0024 | 55 |
| WELL-0044 | 55 |
| WELL-0050 | 55 |
| WELL-0051 | 55 |
| WELL-0106 | 55 |
| WELL-0144 | 55 |
| WELL-0207 | 55 |

No oil production volumes exist in this dataset: only a weekly producing / not-producing reading per well (temperature rule). So 'most oil produced in 2026' cannot be answered; the closest proxy is the number of weekly inspections showing the well producing (45 wells tie at 55). That is uptime, not barrels.

## Q3 (Laura Simmons, chat 3)
**Since 1 Nov 2026, every time an operator note reports gas at a well, did we get someone out to that well in time under our operating procedures? List every report and whether the response met the deadline.**

26 gas-odor notes since 2026-11-01; 9 missed. OPS-1: response = a maintenance job starting, or a MANUAL inspection (drone does not count), after the note within 24 h (notes before 01 Jan 2027) / 12 h (from then).
Problems: WELL-0163 (Missed), 251.1 h; WELL-0341 (Missed), 677.8 h; WELL-0332 (Missed); WELL-0401 (Missed), 138.2 h; WELL-0052 (Missed); WELL-0362 (Missed), 31.8 h; WELL-0161 (Missed), 475.2 h; WELL-0599 (Missed), 16.4 h; WELL-0516 (Missed), 15.0 h.

*Visual: table*

| Well | Area | Reported at | Response | Hours to response | Deadline | Met/Missed |
|---|---|---|---|---|---|---|
| WELL-0163 | Northeast Block 8 | 2026-11-03 20:55 | MNT-0163-019 at 2026-11-14 08:00 | 251.1 | 24 h | Missed |
| WELL-0149 | Northeast Block 7 | 2026-11-06 18:20 | MNT-0149-029 at 2026-11-07 08:00 | 13.7 | 24 h | Met |
| WELL-0165 | Northeast Block 8 | 2026-11-13 20:35 | MNT-0165-031 at 2026-11-14 08:00 | 11.4 | 24 h | Met |
| WELL-0341 | Northwest Block 12 | 2026-11-19 07:40 | INS-0341-0109 at 2026-12-17 13:30 | 677.8 | 24 h | Missed |
| WELL-0091 | Southwest Block 24 | 2026-11-27 22:25 | MNT-0091-019 at 2026-11-28 08:00 | 9.6 | 24 h | Met |
| WELL-0423 | Northwest Block 12 | 2026-12-03 05:25 | INS-0423-0213 at 2026-12-03 09:15 | 3.8 | 24 h | Met |
| WELL-0059 | Southwest Block 24 | 2026-12-03 06:10 | INS-0059-0213 at 2026-12-03 12:15 | 6.1 | 24 h | Met |
| WELL-0332 | Northwest Block 12 | 2026-12-03 12:10 | none | - | 24 h | Missed |
| WELL-0401 | Northwest Block 12 | 2026-12-05 13:50 | MNT-0401-033 at 2026-12-11 08:00 | 138.2 | 24 h | Missed |
| WELL-0189 | Northeast Block 8 | 2026-12-10 12:35 | MNT-0189-037 at 2026-12-11 08:00 | 19.4 | 24 h | Met |
| WELL-0403 | Northwest Block 12 | 2026-12-10 21:15 | MNT-0403-024 at 2026-12-11 08:00 | 10.8 | 24 h | Met |
| WELL-0244 | Southeast Block 31 | 2026-12-11 05:25 | MNT-0244-026 at 2026-12-11 08:00 | 2.6 | 24 h | Met |
| WELL-0040 | Southwest Block 23 | 2026-12-12 01:55 | MNT-0040-029 at 2026-12-12 08:00 | 6.1 | 24 h | Met |
| WELL-0228 | Southeast Block 31 | 2026-12-16 19:50 | INS-0228-0144 at 2026-12-17 12:45 | 16.9 | 24 h | Met |
| WELL-0052 | Southwest Block 24 | 2026-12-18 06:45 | none | - | 24 h | Missed |
| WELL-0370 | Northwest Block 12 | 2026-12-21 12:45 | MNT-0370-028 at 2026-12-22 08:00 | 19.2 | 24 h | Met |
| WELL-0362 | Northwest Block 12 | 2026-12-24 00:15 | MNT-0362-030 at 2026-12-25 08:00 | 31.8 | 24 h | Missed |
| WELL-0161 | Northeast Block 8 | 2026-12-25 15:45 | INS-0161-0168 at 2027-01-14 11:00 | 475.2 | 24 h | Missed |
| WELL-0135 | Northeast Block 7 | 2026-12-27 03:50 | MNT-0135-034 at 2026-12-27 08:00 | 4.2 | 24 h | Met |
| WELL-0324 | Northwest Block 12 | 2027-01-01 22:40 | MNT-0324-036 at 2027-01-02 08:00 | 9.3 | 12 h | Met |
| WELL-0330 | Northwest Block 12 | 2027-01-02 21:40 | MNT-0330-030 at 2027-01-03 08:00 | 10.3 | 12 h | Met |
| WELL-0599 | Southeast Block 32 | 2027-01-06 17:20 | INS-0599-0196 at 2027-01-07 09:45 | 16.4 | 12 h | Missed |
| WELL-0516 | Southeast Block 32 | 2027-01-06 21:15 | INS-0516-0215 at 2027-01-07 12:15 | 15.0 | 12 h | Missed |
| WELL-0425 | Northwest Block 12 | 2027-01-07 05:20 | INS-0425-0218 at 2027-01-07 09:00 | 3.7 | 12 h | Met |
| WELL-0465 | Southeast Block 32 | 2027-01-08 23:35 | MNT-0465-031 at 2027-01-09 08:00 | 8.4 | 12 h | Met |

(26 rows total)

26 gas-odor notes since 2026-11-01; 9 missed. OPS-1: response = a maintenance job starting, or a MANUAL inspection (drone does not count), after the note within 24 h (notes before 01 Jan 2027) / 12 h (from then).

Evidence: CTX-0040-002, CTX-0052-003, CTX-0059-002, CTX-0091-001, CTX-0135-009, CTX-0137-004, CTX-0149-004, CTX-0161-006, CTX-0163-002, CTX-0165-001, CTX-0189-003, CTX-0228-004, CTX-0244-002, CTX-0324-001, CTX-0330-003, CTX-0332-004, CTX-0341-002, CTX-0362-002, CTX-0370-005, CTX-0401-002, CTX-0403-004, CTX-0423-002, CTX-0425-006, CTX-0465-005, CTX-0516-002, CTX-0599-003, INS-0059-0213, INS-0161-0168, INS-0228-0144, INS-0341-0109, INS-0423-0213, INS-0425-0218, INS-0516-0215, INS-0599-0196, MNT-0040-029, MNT-0091-019, MNT-0135-034, MNT-0137-032, MNT-0149-029, MNT-0163-019, MNT-0165-031, MNT-0189-037, MNT-

## Q4 (Chris Dalton, chat 4)
**Across all areas, which temporary flowline bypasses are in place right now, and is each one allowed? Also list any bypass, past or present, that stayed in after its approval ran out or was never approved at all.**

12 bypass periods found in operator notes; 5 are not allowed (OPS-2). Expiry runs to the end of the memo's date; an extension memo replaces the earlier expiry.
Problems: WELL-0087 (Expired); WELL-0158 (Expired); WELL-0249 (Expired); WELL-0405 (Not approved); WELL-0561 (Not approved).
In place right now: WELL-0249 (Expired, MOC-2026-036); WELL-0405 (Not approved, none); WELL-0248 (Allowed, MOC-2026-044).

*Visual: table*

| Well | Area | Bypass in | Bypass out | Approval | Approval valid until | Status |
|---|---|---|---|---|---|---|
| WELL-0087 | Southwest Block 24 | 2026-12-02 11:15 | 2027-01-06 13:20 | MOC-2026-036 | 2026-12-15 | Expired |
| WELL-0158 | Northeast Block 8 | 2026-11-20 15:20 | 2026-12-28 10:35 | MOC-2026-036 | 2026-12-15 | Expired |
| WELL-0249 | Southeast Block 31 | 2026-11-25 10:25 | still in | MOC-2026-036 | 2026-12-15 | Expired |
| WELL-0405 | Northwest Block 12 | 2026-12-20 10:15 | still in | none | - | Not approved |
| WELL-0561 | Southeast Block 32 | 2026-12-08 08:25 | 2026-12-19 08:55 | none | - | Not approved |
| WELL-0013 | Southwest Block 23 | 2026-11-10 13:15 | 2027-01-08 14:45 | MOC-2026-044 | 2027-02-28 | Allowed |
| WELL-0062 | Southwest Block 24 | 2026-11-02 11:45 | 2026-11-27 09:20 | MOC-2026-044 | 2027-02-28 | Allowed |
| WELL-0248 | Southeast Block 31 | 2026-11-05 13:30 | still in | MOC-2026-044 | 2027-02-28 | Allowed |
| WELL-0284 | Southwest Block 24 | 2026-11-12 10:55 | 2026-12-10 15:20 | MOC-2026-036 | 2026-12-15 | Allowed |
| WELL-0356 | Northwest Block 12 | 2026-11-18 09:20 | 2026-12-05 12:15 | MOC-2026-036 | 2026-12-15 | Allowed |
| WELL-0461 | Southeast Block 32 | 2026-11-14 09:50 | 2026-12-12 15:40 | MOC-2026-036 | 2026-12-15 | Allowed |
| WELL-0476 | Southeast Block 32 | 2026-10-22 15:50 | 2026-11-18 14:10 | MOC-2026-044 | 2027-02-28 | Allowed |

12 bypass periods found in operator notes; 5 are not allowed (OPS-2). Expiry runs to the end of the memo's date; an extension memo replaces the earlier expiry.

Evidence: CTX-0013-002, CTX-0013-005, CTX-0062-002, CTX-0062-005, CTX-0087-001, CTX-0087-004, CTX-0158-003, CTX-0158-005, CTX-0248-002, CTX-0249-002, CTX-0284-002, CTX-0284-003, CTX-0356-002, CTX-0356-003, CTX-0405-003, CTX-0461-002, CTX-0461-003, CTX-0476-002, CTX-0476-003, CTX-0561-004, CTX-0561-005, MOC-2026-031, MOC-2026-036, MOC-2026-044

## Q5 (Michael Turner, chat 5)
**The State Oil & Gas Commission wrote to us in November 2026 about spills. Which of our spills does the letter cover, and on which ones are we not compliant? Show me a table.**

6 spills of at least 5 bbl in Northeast Block 7/8 since 01 Jun 2026 (volumes after corrections; spills corrected to not-a-spill are excluded); 3 not compliant; results were due 15 Jan 2027.
Problems: WELL-0123 (No: clean-up section lacks 'Soil samples sent to the lab.' (field soil readings only)); WELL-0182 (No: clean-up section lacks 'Soil samples sent to the lab.' (field soil readings only)); WELL-0262 (No: clean-up section lacks 'Soil samples sent to the lab.' (field soil readings only)).

*Visual: table*

| Well | Area | Inspection | Volume | Clean-up job | Compliant? |
|---|---|---|---|---|---|
| WELL-0168 | Northeast Block 8 | INS-0168-0190, 2026-06-11 | 5.6 bbl | MNT-0168-024 | Yes: report says soil samples were sent to the lab |
| WELL-0123 | Northeast Block 7 | INS-0123-0093, 2026-09-24 | 6 bbl | MNT-0123-014 | No: clean-up section lacks 'Soil samples sent to the lab.' ( |
| WELL-0277 | Northeast Block 7 | INS-0277-0205, 2026-10-01 | 6.2 bbl | MNT-0277-031 | Yes: report says soil samples were sent to the lab |
| WELL-0119 | Northeast Block 7 | INS-0119-0209, 2026-11-05 | 6 bbl | MNT-0119-029 | Yes: report says soil samples were sent to the lab |
| WELL-0182 | Northeast Block 8 | INS-0182-0208, 2026-12-03 | 5.2 bbl | MNT-0182-028 | No: clean-up section lacks 'Soil samples sent to the lab.' ( |
| WELL-0262 | Northeast Block 8 | INS-0262-0218, 2027-01-07 | 6.1 bbl | MNT-0262-029 | No: clean-up section lacks 'Soil samples sent to the lab.' ( |

6 spills of at least 5 bbl in Northeast Block 7/8 since 01 Jun 2026 (volumes after corrections; spills corrected to not-a-spill are excluded); 3 not compliant; results were due 15 Jan 2027.

Evidence: INS-0119-0209, INS-0123-0093, INS-0168-0190, INS-0182-0208, INS-0262-0218, INS-0277-0205, MNT-0119-029, MNT-0123-014, MNT-0168-024, MNT-0182-028, MNT-0262-029, MNT-0277-031, regulator-letter-2026-11-20.md

## Q6 (Nathan Pierce, chat 6)
**Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right now, and why?**

10 wells where a newer shut-in/restart operator note overrides the latest inspection (OPS-3). Plugged-and-abandoned wells are excluded; 'unconfirmed' = restart note, no inspection since.
WELL-0026: Producing oil (unconfirmed). Why: the operator note (2027-01-15 10:25) is newer than inspection INS-0026-0216 and says the well was restarted; an inspection has not confirmed it yet.
WELL-0032: Producing oil (unconfirmed). Why: the operator note (2027-01-15 10:25) is newer than inspection INS-0032-0219 and says the well was restarted; an inspection has not confirmed it yet.
WELL-0033: Producing oil (unconfirmed). Why: the operator note (2027-01-15 10:25) is newer than inspection INS-0033-0222 and says the well was restarted; an inspection has not confirmed it yet.
WELL-0044: Not producing oil. Why: the operator note (2027-01-14 13:05) is newer than inspection INS-0044-0218 and says the well was shut in; an inspection has not confirmed it.
WELL-0046: Producing oil (unconfirmed). Why: the operator note (2027-01-15 10:25) is newer than inspection INS-0046-0220 and says the well was restarted; an inspection has not confirmed it yet.
WELL-0323: Not producing oil. Why: the operator note (2027-01-14 19:20) is newer than inspection INS-0323-0219 and says the well was shut in; an inspection has not confirmed it.
WELL-0355: Not producing oil. Why: the operator note (2027-01-14 19:05) is newer than inspection INS-0355-0213 and says the well was shut in; an inspection has not confirmed it.
WELL-0422: Not producing oil. Why: the operator note (2027-01-14 21:35) is newer than inspection INS-0422-0215 and says the well was shut in; an inspection has not confirmed it.
WELL-0479: Not producing oil. Why: the operator note (2027-01-14 15:35) is newer than inspection INS-0479-0213 and says the well was shut in; an inspection has not confirmed it.
WELL-0481: Not producing oil. Why: the operator note (2027-01-14 18:50) is newer than inspection INS-0481-0220 and says the well was shut in; an inspection has not confirmed it.

*Visual: table*

| Well | Area | Latest inspection | Latest operator note | Status now |
|---|---|---|---|---|
| WELL-0026 | Southwest Block 23 | INS-0026-0216, 2027-01-14, not producing | 2027-01-15 10:25, restarted: WELL-0026 put back on productio | Producing oil (unconfirmed) |
| WELL-0032 | Southwest Block 23 | INS-0032-0219, 2027-01-14, not producing | 2027-01-15 10:25, restarted: Brought WELL-0032 back online a | Producing oil (unconfirmed) |
| WELL-0033 | Southwest Block 23 | INS-0033-0222, 2027-01-14, not producing | 2027-01-15 10:25, restarted: Restarted WELL-0033, unit runni | Producing oil (unconfirmed) |
| WELL-0044 | Southwest Block 23 | INS-0044-0218, 2027-01-14, producing | 2027-01-14 13:05, shut in: Shut in WELL-0044 at the wellhead | Not producing oil |
| WELL-0046 | Southwest Block 23 | INS-0046-0220, 2027-01-14, not producing | 2027-01-15 10:25, restarted: WELL-0046 put back on productio | Producing oil (unconfirmed) |
| WELL-0323 | Northwest Block 12 | INS-0323-0219, 2027-01-14, producing | 2027-01-14 19:20, shut in: Shut-in WELL-0323 after the pumpe | Not producing oil |
| WELL-0355 | Northwest Block 12 | INS-0355-0213, 2027-01-14, producing | 2027-01-14 19:05, shut in: Found WELL-0355 leaking at the st | Not producing oil |
| WELL-0422 | Northwest Block 12 | INS-0422-0215, 2027-01-14, producing | 2027-01-14 21:35, shut in: Shut in WELL-0422 for the night,  | Not producing oil |
| WELL-0479 | Southeast Block 32 | INS-0479-0213, 2027-01-14, producing | 2027-01-14 15:35, shut in: Found WELL-0479 leaking at the st | Not producing oil |
| WELL-0481 | Southeast Block 32 | INS-0481-0220, 2027-01-14, producing | 2027-01-14 18:50, shut in: Shut in WELL-0481 for the night,  | Not producing oil |

10 wells where a newer shut-in/restart operator note overrides the latest inspection (OPS-3). Plugged-and-abandoned wells are excluded; 'unconfirmed' = restart note, no inspection since.

Evidence: INS-0026-0216, CTX-0026-001, INS-0032-0219, CTX-0032-006, INS-0033-0222, CTX-0033-003, INS-0044-0218, CTX-0044-008, INS-0046-0220, CTX-0046-004, INS-0323-0219, CTX-0323-002, INS-0355-0213, CTX-0355-004, INS-0422-0215, CTX-0422-003, INS-0479-0213, CTX-0479-004, INS-0481-0220, CTX-0481-006

## Q7 (Robert Hayes, chat 7)
**Over the last month the operators have written notes about wells that sound or behave wrong. Which of those wells haven't had a repair since? Rank the 10 most likely to need a repair in the next 90 days, other than a spill clean-up, and quote the notes as evidence.**

Wells: WELL-0197, WELL-0281, WELL-0498, WELL-0219, WELL-0010, WELL-0175, WELL-0182, WELL-0203, WELL-0249, WELL-0481.
Here are the 10 wells most likely to need a repair in the next 90 days, excluding spill clean-ups, based on operator notes and lack of subsequent repair. The ranking is a heuristic, not a prediction model, calculated from the severity weight of the notes, non-producing readings, and repeat corrective repairs.

1.  **WELL-0197** in Northeast Block 8. Notes include: "Pumper reports rattling at WELL-0197 pump jack, keep an eye on it." (CTX-0197-002, 04 Jan); "Heard fluid pound on WELL-0197, unit still running." (CTX-0197-003, 08 Jan); "Heard fluid pound on WELL-0197, unit still running." (CTX-0197-004, 12 Jan). The last repair was MNT-0197-029 on 2027-01-01 for a parted sucker rod.
2.  **WELL-0281** in Northeast Block 7. The note states: "Found WELL-0281 leaking at the stuffing box, shut the well in." (CTX-0281-004, 14 Jan). The last repair was MNT-0281-031 on 2027-01-02 for a flowline corrosion pinhole leak.
3.  **WELL-0498** in Southeast Block 32. Notes include: "WELL-0498 drive tripping on and off overnight, reset it each time." (CTX-0498-004, 09 Jan); "WELL-0498 drive tripping on underload, restarted from the panel." (CTX-0498-005, 11 Jan); "WELL-0498 drive tripping on underload, restarted from the panel." (CTX-0498-006, 12 Jan). The last repair was MNT-0498-031 on 2027-01-03 for a separator level controller fault.
4.  **WELL-0219** in Southeast Block 31. Notes include: "WELL-0219 drive tripping on underload, restarted from the panel." (CTX-0219-006, 05 Jan); "Drive on WELL-0219 showing amps hunting between 38 and 44 A." (CTX-0219-007, 13 Jan). The last repair was MNT-0219-022 on 2026-11-24 for scheduled wellhead valve service.
5.  **WELL-0010** in Southwest Block 23. Notes include: "Rod squeal at WELL-0010 stuffing box, greased the polished rod." (CTX-0010-005, 10 Jan); "Rod squeal at WELL-0010 stuffing box, greased the polished rod." (CTX-0010-006, 13 Jan); "Heard fluid pound on WELL-0010, unit still running." (CTX-0010-007, 14 Jan). The last repair was MNT-0010-031 on 2027-01-08 for a flowline leak causing a spill.
6.  **WELL-0175** in Northeast Block 8. Notes include: "Heard fluid pound on WELL-0175, unit still running." (CTX-0175-003, 17 Dec); "Rod squeal at WELL-0175 stuffing box, greased the polished rod." (CTX-0175-006, 21 Dec); "WELL-0175 tagging bottom on the downstroke, adjust spacing next visit." (CTX-0175-007, 26 Dec). The last repair was MNT-0175-035 on 2026-11-28 for scheduled wellhead valve service.
7.  **WELL-0182** in Northeast Block 8. Notes include: "Pumper reports rattling at WELL-0182 pump jack, keep an eye on it." (CTX-0182-005, 27 Dec); "WELL-0182 tagging bottom on the downstroke, adjust spacing next visit." (CTX-0182-007, 30 Dec); "Heard fluid pound on WELL-0182, unit still running." (CTX-0182-008, 05 Jan). The last repair was MNT-0182-029 on 2026-12-26 for walking beam bearing wear.
8.  **WELL-0203** in Southeast Block 31. The note states: "Found WELL-0203 leaking at the stuffing box, shut the well in." (CTX-0203-003, 14 Jan). The last repair was MNT-0203-031 on 2027-01-10 for scheduled wellhead valve service.
9.  **WELL-0249** in Southeast Block 31. The note states: "WELL-0249 drive tripping on underload, restarted from the panel." (CTX-0249-004, 13 Jan). The last repair was MNT-0249-018 on 2027-01-09 for ESP motor burnout.
10. **WELL-0481** in Southeast Block 32. Notes include: "Rod squeal at WELL-0481 stuffing box, greased the polished rod." (CTX-0481-004, 06 Jan); "Pumper reports rattling at WELL-0481 pump jack, keep an eye on it." (CTX-0481-005, 08 Jan); "Shut in WELL-0481 for the night, high pressure alarm on the separator." (CTX-0481-006, 14 Jan). The last repair was MNT-0481-025 on 2026-12-14 for scheduled lubrication and belt inspection.

*Visual: table*

| Rank | _score | Well | Area | Operator-note evidence | Other warning signs | Last repair |
|---|---|---|---|---|---|---|
| 1 | 11 | WELL-0197 | Northeast Block 8 | "Pumper reports rattling at WELL-0197 pump jack, keep an eye | latest inspection: not producing; 3 non-producing weekly ins | MNT-0197-029, 2027-01-01 (Sucker rod parted) |
| 2 | 11 | WELL-0281 | Northeast Block 7 | "Found WELL-0281 leaking at the stuffing box, shut the well  | latest inspection: not producing; 3 non-producing weekly ins | MNT-0281-031, 2027-01-02 (Flowline corrosion pinhole leak) |
| 3 | 11 | WELL-0498 | Southeast Block 32 | "WELL-0498 drive tripping on and off overnight, reset it eac | 2 non-producing weekly inspections in the last 12 weeks | MNT-0498-031, 2027-01-03 (Separator level controller fault) |
| 4 | 10 | WELL-0219 | Southeast Block 31 | "WELL-0219 drive tripping on underload, restarted from the p | latest inspection: not producing; 1 non-producing weekly ins | MNT-0219-022, 2026-11-24 (Scheduled wellhead valve service) |
| 5 | 9 | WELL-0010 | Southwest Block 23 | "Rod squeal at WELL-0010 stuffing box, greased the polished  | latest inspection: not producing; 2 non-producing weekly ins | MNT-0010-031, 2027-01-08 (Flowline leak causing spill) |
| 6 | 9 | WELL-0175 | Northeast Block 8 | "Heard fluid pound on WELL-0175, unit still running." (CTX-0 | latest inspection: not producing; 1 non-producing weekly ins | MNT-0175-035, 2026-11-28 (Scheduled wellhead valve service) |
| 7 | 9 | WELL-0182 | Northeast Block 8 | "Pumper reports rattling at WELL-0182 pump jack, keep an eye | 4 non-producing weekly inspections in the last 12 weeks; 6 c | MNT-0182-029, 2026-12-26 (Walking beam bearing wear) |
| 8 | 9 | WELL-0203 | Southeast Block 31 | "Found WELL-0203 leaking at the stuffing box, shut the well  | latest inspection: not producing; 1 non-producing weekly ins | MNT-0203-031, 2027-01-10 (Scheduled wellhead valve service) |
| 9 | 9 | WELL-0249 | Southeast Block 31 | "WELL-0249 drive tripping on underload, restarted from the p | latest inspection: not producing; 2 non-producing weekly ins | MNT-0249-018, 2027-01-09 (ESP motor burnout) |
| 10 | 9 | WELL-0481 | Southeast Block 32 | "Rod squeal at WELL-0481 stuffing box, greased the polished  | 2 non-producing weekly inspections in the last 12 weeks; 2 c | MNT-0481-025, 2026-12-14 (Scheduled lubrication and belt ins |

Operator notes from the last 30 days that describe something sounding or behaving wrong (leak, tripping drive, hunting amps, tagging bottom, rattling, squeal, fluid pound), on wells with no repair job started since the note. Ranking = severity weight of the notes + non-producing readings + repeat corrective repairs; it is a heuristic, not a prediction model.

Evidence: CTX-0423-003, CTX-0423-004, CTX-0118-003, CTX-0118-004, CTX-0118-006, CTX-0342-003, CTX-0493-003, CTX-0493-004, CTX-0196-005, CTX-0196-007, CTX-0130-001, CTX-0130-002, CTX-0076-005, CTX-0076-006, CTX-0076-008, CTX-0175-003, CTX-0175-006, CTX-0175-007, CTX-0030-001, CTX-0030-002, CTX-0030-004, CTX-0434-002, CTX-0434-003, CTX-0469-004, CTX-0469-005, CTX-0478-001, CTX-0401-003, CTX-0401-004, CTX-0538-004, CTX-0349-001, CTX-0349-002, CTX-0554-003, CTX-0554-004, CTX-0463-004, CTX-0413-002, CTX-0413-003, CTX-0392-002, CTX-0392-003, CTX-0536-003, CTX-0286-002, CTX-0286-004, CTX-0286-005, CTX-0520-002

## Q8 (Robert Hayes, chat 7)
**Which three would you send a crew to first this week, and why?**

You should send a crew to WELL-0197, WELL-0281, and WELL-0498 first this week. WELL-0197 in Northeast Block 8 is ranked first because operator notes sound wrong, specifically reporting rattling at the pump jack on January 4th (CTX-0197-002). WELL-0281 in Northeast Block 7 is ranked second because operator notes sound wrong, indicating a leak at the stuffing box and the well being shut in on January 14th (CTX-0281-004). WELL-0498 in Southeast Block 32 is ranked third because operator notes sound wrong, with the drive tripping on and off overnight on January 9th (CTX-0498-004).

*Visual: table*

| Rank | Well | Area | Score | Why |
|---|---|---|---|---|
| 1 | WELL-0197 | Northeast Block 8 | 5.5 | operator notes sound wrong: "Pumper reports rattling at WELL |
| 2 | WELL-0281 | Northeast Block 7 | 5.5 | operator notes sound wrong: "Found WELL-0281 leaking at the  |
| 3 | WELL-0498 | Southeast Block 32 | 5.5 | operator notes sound wrong: "WELL-0498 drive tripping on and |
| 4 | WELL-0219 | Southeast Block 31 | 5.0 | operator notes sound wrong: "WELL-0219 drive tripping on und |
| 5 | WELL-0010 | Southwest Block 23 | 4.5 | operator notes sound wrong: "Rod squeal at WELL-0010 stuffin |
| 6 | WELL-0175 | Northeast Block 8 | 4.5 | operator notes sound wrong: "Heard fluid pound on WELL-0175, |
| 7 | WELL-0182 | Northeast Block 8 | 4.5 | operator notes sound wrong: "Pumper reports rattling at WELL |
| 8 | WELL-0203 | Southeast Block 31 | 4.5 | operator notes sound wrong: "Found WELL-0203 leaking at the  |
| 9 | WELL-0249 | Southeast Block 31 | 4.5 | operator notes sound wrong: "WELL-0249 drive tripping on und |
| 10 | WELL-0481 | Southeast Block 32 | 4.5 | operator notes sound wrong: "Rod squeal at WELL-0481 stuffin |

Priority = safety (unanswered gas report) > recalled pump in a well not producing > recalled pump > operator-note warning > missed heat-trace check. Weights are a judgement stated here, not a company rule.

## Q9 (Nathan Pierce, chat 8)
**WELL-0333's recalled pump was swapped out yesterday. The work order isn't in the system yet. Please count it as replaced from now on.**

Recorded for WELL-0333 as shared knowledge from Nathan Pierce: "Recalled pump was swapped out yesterday." (valid from 2027-01-14). Other users asking about this will see it, attributed to you.
From now on WELL-0333's recalled pump counts as replaced in the recall list. Source: Nathan Pierce's own statement, no work order in the system yet; I will say so wherever I use it.

*Visual: text*

## Q10 (Nathan Pierce, chat 8)
**Also, just for me: whenever you list wells, sort them by area and then by well ID, and show costs in thousands of dollars.**

Saved for Nathan Pierce only (a personal preference, not shared with other users): sort wells by area, then well ID and show costs in thousands of dollars. It applies to every list I show you from now on, and I will say so each time.

*Visual: text*

## Q11 (Robert Hayes, chat 9)
**Which recalled pumps are still in the ground right now?**

Recalled lots (supplier notice HPC-RN-2026-07): LOT-2409-A, LOT-2409-C, LOT-2410-B; RP-175 rod pumps only, current pump only, ESP wells and plugged wells excluded. 8 still in the ground.
Facts come from the maintenance reports' 'Parts installed' lines and the supplier notice.
Counted as replaced by a user-reported swap (no work order yet): WELL-0333: swap recorded by Nathan Pierce (confirmed)
8 wells: Northeast Block 8: WELL-0156, WELL-0160; Northwest Block 12: WELL-0305, WELL-0426, WELL-0428; Southeast Block 32: WELL-0577; Southwest Block 23: WELL-0031, WELL-0263.
WELL-0031: producing; last repaired 2027-01-02 (MNT-0031-033, corrective: Stuffing box packing leak); installed 2026-04-24 (MNT-0031-027, lot LOT-2409-A).
WELL-0156: producing; last repaired 2026-12-04 (MNT-0156-030, corrective: Flowline leak causing spill); installed 2026-06-27 (MNT-0156-027, lot LOT-2409-A).
WELL-0160: not producing; last repaired 2026-12-27 (MNT-0160-031, scheduled: Scheduled wellhead valve service); installed 2026-07-18 (MNT-0160-028, lot LOT-2409-C).
WELL-0263: not producing; last repaired 2027-01-09 (MNT-0263-035, corrective: Flowline corrosion pinhole leak); installed 2026-10-16 (MNT-0263-033, lot LOT-2410-B).
WELL-0305: producing; last repaired 2026-12-13 (MNT-0305-033, scheduled: Scheduled lubrication and belt inspection); installed 2026-10-16 (MNT-0305-032, lot LOT-2409-A).
WELL-0426: producing; last repaired 2027-01-04 (MNT-0426-035, scheduled: Scheduled wellhead valve service); installed 2026-06-19 (MNT-0426-030, lot LOT-2409-C).
WELL-0428: producing; last repaired 2026-12-19 (MNT-0428-028, scheduled: Scheduled lubrication and belt inspection); installed 2026-03-07 (MNT-0428-022, lot LOT-2410-B).
WELL-0577: producing; last repaired 2026-12-07 (MNT-0577-033, scheduled: Scheduled lubrication and belt inspection); installed 2026-07-31 (MNT-0577-028, lot LOT-2409-A).

*Visual: table*

| Well | Area | Pump | Serial | Lot | Installed | Install job | Install cost (USD) |
|---|---|---|---|---|---|---|---|
| WELL-0031 | Southwest Block 23 | Highline RP-175 | SN-664877 | LOT-2409-A | 2026-04-24 | MNT-0031-027 | 19625 |
| WELL-0156 | Northeast Block 8 | Highline RP-175 | SN-952958 | LOT-2409-A | 2026-06-27 | MNT-0156-027 | 23398 |
| WELL-0160 | Northeast Block 8 | Highline RP-175 | SN-429965 | LOT-2409-C | 2026-07-18 | MNT-0160-028 | 33086 |
| WELL-0263 | Southwest Block 23 | Highline RP-175 | SN-187332 | LOT-2410-B | 2026-10-16 | MNT-0263-033 | 17254 |
| WELL-0305 | Northwest Block 12 | Highline RP-175 | SN-978137 | LOT-2409-A | 2026-10-16 | MNT-0305-032 | 24528 |
| WELL-0426 | Northwest Block 12 | Highline RP-175 | SN-880271 | LOT-2409-C | 2026-06-19 | MNT-0426-030 | 24044 |
| WELL-0428 | Northwest Block 12 | Highline RP-175 | SN-708611 | LOT-2410-B | 2026-03-07 | MNT-0428-022 | 27074 |
| WELL-0577 | Southeast Block 32 | Highline RP-175 | SN-757468 | LOT-2409-A | 2026-07-31 | MNT-0577-028 | 25500 |

Recalled lots (supplier notice HPC-RN-2026-07): LOT-2409-A, LOT-2409-C, LOT-2410-B; RP-175 rod pumps only, current pump only, ESP wells and plugged wells excluded. 8 still in the ground.  
Facts come from the maintenance reports' 'Parts installed' lines and the supplier notice.  
Counted as replaced by a user-reported swap (no work order yet): WELL-0333: swap recorded by Nathan Pierce (confirmed)

Evidence: MNT-0031-027, MNT-0156-027, MNT-0160-028, MNT-0263-033, MNT-0305-032, MNT-0426-030, MNT-0428-022, MNT-0577-028, supplier-recall-notice-2026-12-01.md

## Q12 (Olivia Grant, chat 10)
**Nathan told me the recalled pump on WELL-0577 was swapped as well. Take it off the recall list.**

Recorded as second-hand and UNVERIFIED: Olivia Grant is relaying what someone else said, and there is no work order or inspection for it yet. I did NOT apply it (for example, a recalled pump stays on the recall list) until the person who did the work, or a record, confirms it.

*Visual: text*

## Q13 (Nathan Pierce, chat 11)
**Show me the recalled pumps that are still in the ground in my area, and what it cost to install each one.**

Recalled lots (supplier notice HPC-RN-2026-07): LOT-2409-A, LOT-2409-C, LOT-2410-B; RP-175 rod pumps only, current pump only, ESP wells and plugged wells excluded. 3 still in the ground.
Facts come from the maintenance reports' 'Parts installed' lines and the supplier notice.
Counted as replaced by a user-reported swap (no work order yet): WELL-0333: swap recorded by Nathan Pierce (confirmed)
WELL-0577: Olivia Grant's claim 'Recalled pump HPC-RN-2026-07 was swapped.' is unconfirmed and was NOT applied
Applied Nathan Pierce's own saved display preference (private to them): sorted by area, then well ID, costs in thousands of dollars.
3 wells: Northwest Block 12: WELL-0305, WELL-0426, WELL-0428.
WELL-0305: producing; last repaired 2026-12-13 (MNT-0305-033, scheduled: Scheduled lubrication and belt inspection); installed 2026-10-16 (MNT-0305-032, lot LOT-2409-A).
WELL-0426: producing; last repaired 2027-01-04 (MNT-0426-035, scheduled: Scheduled wellhead valve service); installed 2026-06-19 (MNT-0426-030, lot LOT-2409-C).
WELL-0428: producing; last repaired 2026-12-19 (MNT-0428-028, scheduled: Scheduled lubrication and belt inspection); installed 2026-03-07 (MNT-0428-022, lot LOT-2410-B).

*Visual: table*

| Well | Area | Pump | Serial | Lot | Installed | Install job | Producing now |
|---|---|---|---|---|---|---|---|
| WELL-0305 | Northwest Block 12 | Highline RP-175 | SN-978137 | LOT-2409-A | 2026-10-16 | MNT-0305-032 | Producing |
| WELL-0426 | Northwest Block 12 | Highline RP-175 | SN-880271 | LOT-2409-C | 2026-06-19 | MNT-0426-030 | Producing |
| WELL-0428 | Northwest Block 12 | Highline RP-175 | SN-708611 | LOT-2410-B | 2026-03-07 | MNT-0428-022 | Producing |

Recalled lots (supplier notice HPC-RN-2026-07): LOT-2409-A, LOT-2409-C, LOT-2410-B; RP-175 rod pumps only, current pump only, ESP wells and plugged wells excluded. 3 still in the ground.  
Facts come from the maintenance reports' 'Parts installed' lines and the supplier notice.  
Counted as replaced by a user-reported swap (no work order yet): WELL-0333: swap recorded by Nathan Pierce (confirmed)  
WELL-0577: Olivia Grant's claim 'Recalled pump HPC-RN-2026-07 was swapped.' is unconfirmed and was NOT applied  
Applied Nathan Pierce's own saved display preference (private to them): sorted by area, then well ID, costs in thousands of dollars.

Evidence: MNT-0305-032, MNT-0426-030, MNT-0428-022, supplier-recall-notice-2026-12-01.md

## Q14 (Robert Hayes, chat 12)
**How many recalled pumps are still in the ground, and in which areas?**

Recalled lots (supplier notice HPC-RN-2026-07): LOT-2409-A, LOT-2409-C, LOT-2410-B; RP-175 rod pumps only, current pump only, ESP wells and plugged wells excluded. 8 still in the ground.
Facts come from the maintenance reports' 'Parts installed' lines and the supplier notice.
Counted as replaced by a user-reported swap (no work order yet): WELL-0333: swap recorded by Nathan Pierce (confirmed)
WELL-0577: Olivia Grant's claim 'Recalled pump HPC-RN-2026-07 was swapped.' is unconfirmed and was NOT applied
8 wells: Northeast Block 8: WELL-0156, WELL-0160; Northwest Block 12: WELL-0305, WELL-0426, WELL-0428; Southeast Block 32: WELL-0577; Southwest Block 23: WELL-0031, WELL-0263.
WELL-0031: producing; last repaired 2027-01-02 (MNT-0031-033, corrective: Stuffing box packing leak); installed 2026-04-24 (MNT-0031-027, lot LOT-2409-A).
WELL-0156: producing; last repaired 2026-12-04 (MNT-0156-030, corrective: Flowline leak causing spill); installed 2026-06-27 (MNT-0156-027, lot LOT-2409-A).
WELL-0160: not producing; last repaired 2026-12-27 (MNT-0160-031, scheduled: Scheduled wellhead valve service); installed 2026-07-18 (MNT-0160-028, lot LOT-2409-C).
WELL-0263: not producing; last repaired 2027-01-09 (MNT-0263-035, corrective: Flowline corrosion pinhole leak); installed 2026-10-16 (MNT-0263-033, lot LOT-2410-B).
WELL-0305: producing; last repaired 2026-12-13 (MNT-0305-033, scheduled: Scheduled lubrication and belt inspection); installed 2026-10-16 (MNT-0305-032, lot LOT-2409-A).
WELL-0426: producing; last repaired 2027-01-04 (MNT-0426-035, scheduled: Scheduled wellhead valve service); installed 2026-06-19 (MNT-0426-030, lot LOT-2409-C).
WELL-0428: producing; last repaired 2026-12-19 (MNT-0428-028, scheduled: Scheduled lubrication and belt inspection); installed 2026-03-07 (MNT-0428-022, lot LOT-2410-B).
WELL-0577: producing; last repaired 2026-12-07 (MNT-0577-033, scheduled: Scheduled lubrication and belt inspection); installed 2026-07-31 (MNT-0577-028, lot LOT-2409-A).

*Visual: table*

| Well | Area | Pump | Serial | Lot | Installed | Install job | Install cost (USD) |
|---|---|---|---|---|---|---|---|
| WELL-0031 | Southwest Block 23 | Highline RP-175 | SN-664877 | LOT-2409-A | 2026-04-24 | MNT-0031-027 | 19625 |
| WELL-0156 | Northeast Block 8 | Highline RP-175 | SN-952958 | LOT-2409-A | 2026-06-27 | MNT-0156-027 | 23398 |
| WELL-0160 | Northeast Block 8 | Highline RP-175 | SN-429965 | LOT-2409-C | 2026-07-18 | MNT-0160-028 | 33086 |
| WELL-0263 | Southwest Block 23 | Highline RP-175 | SN-187332 | LOT-2410-B | 2026-10-16 | MNT-0263-033 | 17254 |
| WELL-0305 | Northwest Block 12 | Highline RP-175 | SN-978137 | LOT-2409-A | 2026-10-16 | MNT-0305-032 | 24528 |
| WELL-0426 | Northwest Block 12 | Highline RP-175 | SN-880271 | LOT-2409-C | 2026-06-19 | MNT-0426-030 | 24044 |
| WELL-0428 | Northwest Block 12 | Highline RP-175 | SN-708611 | LOT-2410-B | 2026-03-07 | MNT-0428-022 | 27074 |
| WELL-0577 | Southeast Block 32 | Highline RP-175 | SN-757468 | LOT-2409-A | 2026-07-31 | MNT-0577-028 | 25500 |

Recalled lots (supplier notice HPC-RN-2026-07): LOT-2409-A, LOT-2409-C, LOT-2410-B; RP-175 rod pumps only, current pump only, ESP wells and plugged wells excluded. 8 still in the ground.  
Facts come from the maintenance reports' 'Parts installed' lines and the supplier notice.  
Counted as replaced by a user-reported swap (no work order yet): WELL-0333: swap recorded by Nathan Pierce (confirmed)  
WELL-0577: Olivia Grant's claim 'Recalled pump HPC-RN-2026-07 was swapped.' is unconfirmed and was NOT applied

Evidence: MNT-0031-027, MNT-0156-027, MNT-0160-028, MNT-0263-033, MNT-0305-032, MNT-0426-030, MNT-0428-022, MNT-0577-028, supplier-recall-notice-2026-12-01.md

## Q15 (Robert Hayes, chat 12)
**Different topic. Who leads Northwest Production, and how many wells does that team run?**

Nathan Pierce (U-601) leads Northwest Production. This team runs 150 active wells; plugged-and-abandoned wells are not counted (TEAM-NW).

*Visual: card*

| Team | Lead | Lead ID | Wells |
|---|---|---|---|
| Northwest Production | Nathan Pierce | U-601 | 150 |

Northwest Production is led by Nathan Pierce; 150 active wells today (team_history applied; plugged-and-abandoned wells not counted).

Evidence: TEAM-NW, U-601

## Q16 (Robert Hayes, chat 12)
**What does our operations SOP say about cold weather? Name one well that missed the check in December.**

The Operations SOP (SOP-OPS, Revision 2, effective 1 Oct 2026) states that from December 1st to February 28th, any inspection with an ambient temperature at or below -5 °C on a producing well requires a maintenance job with "Heat trace check" in its issue, starting within 7 days of the inspection (operations-sop-rev2.md §OPS-5). A cold reading on a non-producing well does not require this.

Four wells missed the heat trace check in December 2026:
*   WELL-0310 in Northwest Block 12, with an inspection (INS-0310-0213) on 2026-12-17 at -6.0 °C.
*   WELL-0354 in Northwest Block 12, with an inspection (INS-0354-0215) on 2026-12-17 at -11.4 °C.
*   WELL-0486 in Southeast Block 32, with an inspection (INS-0486-0219) on 2026-12-31 at -7.0 °C.
*   WELL-0531 in Southeast Block 32, with an inspection (INS-0531-0217) on 2026-12-31 at -5.3 °C.

*Visual: text*

| doc | kind | section | snippet |
|---|---|---|---|
| fleet/sops/operations-sop-rev2.md | manual/sop | Operations SOP | operations-sop-rev2 / Operations SOP
# Operations SOP

> Fic |
| fleet/sops/field-work-sop.md | manual/sop | Field Work Safety and Maintenance SOP | field-work-sop / Field Work Safety and Maintenance SOP
# Fie |
| fleet/sops/spill-response-sop.md | manual/sop | Spill Response SOP | spill-response-sop / Spill Response SOP
# Spill Response SOP |
| fleet/sops/field-work-sop.md | manual/sop | **WS-07** / Write the **maintenance report** within 3 days o | field-work-sop / 3. Protocols: **WS-07** / Write the **maint |
| fleet/sops/field-work-sop.md | manual/sop | 2. Background (industry references) | field-work-sop / 2. Background (industry references)
## 2. B |

hybrid search: BM25 + text-embedding-005 vectors in chroma (6411 chunks)  
SOP (OPS-5, freeze protection): from 1 Dec to 28 Feb, any inspection with ambient at or below -5 °C on a well producing at that reading needs a maintenance job whose issue contains 'Heat trace check' on that well, starting within 7 days after the inspection; a cold reading on a non-producing well needs none.  
OPS-5 (1 Dec to 28 Feb, ambient <= -5 °C, producing well): 9 qualifying inspections in 2026-12-01..2026-12-31, 5 followed by a heat-trace job within 7 days, 4 missed.

Evidence: fleet/sops/operations-sop-rev2.md, fleet/sops/field-work-sop.md, fleet/sops/spill-response-sop.md, INS-0310-0213, INS-0354-0215, INS-0486-0219, INS-0531-0217, operations-sop-rev2.md §OPS-5

## Q17 (Robert Hayes, chat 12)
**An operator reported a gas smell at WELL-0332 on 3 Dec. What was the H2S reading?**

1 gas-odor notes since 2026-12-03; 1 missed. OPS-1: response = a maintenance job starting, or a MANUAL inspection (drone does not count), after the note within 24 h (notes before 01 Jan 2027) / 12 h (from then).
No H2S reading is recorded for this report: the operator note only says gas was smelled, and H2S ppm values exist only in maintenance reports' safety sections (personal monitors) - no job followed the note. Inspections around it: INS-0332-0212 03 Dec 14:45 (drone, no gas measurement).
Problems: WELL-0332 (Missed).

*Visual: table*

| Well | Area | Reported at | Response | Hours to response | Deadline | Met/Missed |
|---|---|---|---|---|---|---|
| WELL-0332 | Northwest Block 12 | 2026-12-03 12:10 | none | - | 24 h | Missed |

1 gas-odor notes since 2026-12-03; 1 missed. OPS-1: response = a maintenance job starting, or a MANUAL inspection (drone does not count), after the note within 24 h (notes before 01 Jan 2027) / 12 h (from then).  
No H2S reading is recorded for this report: the operator note only says gas was smelled, and H2S ppm values exist only in maintenance reports' safety sections (personal monitors) - no job followed the note. Inspections around it: INS-0332-0212 03 Dec 14:45 (drone, no gas measurement).

Evidence: CTX-0332-004

## Q18 (Robert Hayes, chat 12)
**Back to the pumps from my first question: which of those wells are not producing oil right now, and when was each one last repaired?**

Recalled lots (supplier notice HPC-RN-2026-07): LOT-2409-A, LOT-2409-C, LOT-2410-B; RP-175 rod pumps only, current pump only, ESP wells and plugged wells excluded. 2 still in the ground.
Facts come from the maintenance reports' 'Parts installed' lines and the supplier notice.
Counted as replaced by a user-reported swap (no work order yet): WELL-0333: swap recorded by Nathan Pierce (confirmed)
WELL-0577: Olivia Grant's claim 'Recalled pump HPC-RN-2026-07 was swapped.' is unconfirmed and was NOT applied
2 wells: Northeast Block 8: WELL-0160; Southwest Block 23: WELL-0263.
WELL-0160: not producing; last repaired 2026-12-27 (MNT-0160-031, scheduled: Scheduled wellhead valve service); installed 2026-07-18 (MNT-0160-028, lot LOT-2409-C).
WELL-0263: not producing; last repaired 2027-01-09 (MNT-0263-035, corrective: Flowline corrosion pinhole leak); installed 2026-10-16 (MNT-0263-033, lot LOT-2410-B).

*Visual: table*

| Well | Area | Pump | Serial | Lot | Installed | Install job | Install cost (USD) |
|---|---|---|---|---|---|---|---|
| WELL-0160 | Northeast Block 8 | Highline RP-175 | SN-429965 | LOT-2409-C | 2026-07-18 | MNT-0160-028 | 33086 |
| WELL-0263 | Southwest Block 23 | Highline RP-175 | SN-187332 | LOT-2410-B | 2026-10-16 | MNT-0263-033 | 17254 |

Recalled lots (supplier notice HPC-RN-2026-07): LOT-2409-A, LOT-2409-C, LOT-2410-B; RP-175 rod pumps only, current pump only, ESP wells and plugged wells excluded. 2 still in the ground.  
Facts come from the maintenance reports' 'Parts installed' lines and the supplier notice.  
Counted as replaced by a user-reported swap (no work order yet): WELL-0333: swap recorded by Nathan Pierce (confirmed)  
WELL-0577: Olivia Grant's claim 'Recalled pump HPC-RN-2026-07 was swapped.' is unconfirmed and was NOT applied

Evidence: MNT-0160-028, MNT-0263-033, supplier-recall-notice-2026-12-01.md

## Q19 (Robert Hayes, chat 12)
**Of all the wells we've talked about today, which one would you deal with first, and why?**

You should deal with WELL-0332 first because a gas odor was reported on 2026-12-03 12:10 with no response in time (OPS-1 missed), indicating a safety concern. Additionally, operator notes sound wrong: "Rod squeal at WELL-0332 stuffing box, greased the polished rod." (CTX-0332-005, 31 Dec) and "Pumper reports rattling at WELL-0332 pump jack, k" (CTX-0332-005, 31 Dec).

*Visual: table*

| Rank | Well | Area | Score | Why |
|---|---|---|---|---|
| 1 | WELL-0332 | Northwest Block 12 | 10.0 | gas odor reported 2026-12-03 12:10 with no response in time  |
| 2 | WELL-0263 | Southwest Block 23 | 9.0 | recalled pump LOT-2410-B still in the ground, 15 days past t |
| 3 | WELL-0160 | Northeast Block 8 | 5 | recalled pump LOT-2409-C still in the ground, 15 days past t |
| 4 | WELL-0305 | Northwest Block 12 | 4.5 | recalled pump LOT-2409-A still in the ground, 15 days past t |
| 5 | WELL-0428 | Northwest Block 12 | 4.5 | recalled pump LOT-2410-B still in the ground, 15 days past t |
| 6 | WELL-0031 | Southwest Block 23 | 3 | recalled pump LOT-2409-A still in the ground, 15 days past t |
| 7 | WELL-0156 | Northeast Block 8 | 3 | recalled pump LOT-2409-A still in the ground, 15 days past t |
| 8 | WELL-0426 | Northwest Block 12 | 3 | recalled pump LOT-2409-C still in the ground, 15 days past t |
| 9 | WELL-0577 | Southeast Block 32 | 3 | recalled pump LOT-2409-A still in the ground, 15 days past t |

Priority = safety (unanswered gas report) > recalled pump in a well not producing > recalled pump > operator-note warning > missed heat-trace check. Weights are a judgement stated here, not a company rule.

## Q20 (Michael Turner, chat 13)
**When a well stays shut in longer than the repair itself, what are we usually waiting on: parts, crews, contractors or weather? Break it down by area for jobs started in 2026, with the typical number of extra days, and tell me if any area stands out.**

498 of 4360 jobs started in 2026 had a well shut in longer than the repair itself (report sentence 'stayed shut in for about N days longer…'); 'Workover rig busy' is a separate waiting sentence in reports and is listed on its own.
Area with the highest share of jobs hit by a post-repair delay: Northeast Block 8 (15% of its jobs); lowest: Southeast Block 31 (8%).
Most common reason per area: Northeast Block 7: Contractor slot (15 jobs); Northeast Block 8: Crew on spill response (19 jobs); Northwest Block 12: Workover rig busy (43 jobs); Southeast Block 31: Workover rig busy (13 jobs); Southeast Block 32: Contractor slot (32 jobs); Southwest Block 23: Weather (road impassable) (16 jobs); Southwest Block 24: Contractor slot (17 jobs).

*Visual: bar*

| Area | Reason | Jobs | Share of area's delayed jobs | Typical extra days |
|---|---|---|---|---|
| Northeast Block 7 | Contractor slot | 15 | 23% | 8.0 |
| Northeast Block 7 | Crew on spill response | 11 | 17% | 16.0 |
| Northeast Block 7 | Parts back-ordered | 15 | 23% | 15.0 |
| Northeast Block 7 | Weather (road impassable) | 15 | 23% | 9.0 |
| Northeast Block 7 | Workover rig busy | 8 | 12% | 12.0 |
| Northeast Block 8 | Contractor slot | 17 | 21% | 9.0 |
| Northeast Block 8 | Crew on spill response | 19 | 24% | 14.0 |
| Northeast Block 8 | Parts back-ordered | 13 | 16% | 10.0 |
| Northeast Block 8 | Weather (road impassable) | 18 | 22% | 8.0 |
| Northeast Block 8 | Workover rig busy | 13 | 16% | 8.0 |
| Northwest Block 12 | Contractor slot | 27 | 16% | 9.0 |
| Northwest Block 12 | Crew on spill response | 36 | 21% | 8.5 |
| Northwest Block 12 | Parts back-ordered | 29 | 17% | 9.0 |
| Northwest Block 12 | Weather (road impassable) | 36 | 21% | 9.0 |
| Northwest Block 12 | Workover rig busy | 43 | 25% | 9.0 |
| Southeast Block 31 | Contractor slot | 10 | 25% | 15.5 |
| Southeast Block 31 | Crew on spill response | 3 | 8% | 2.0 |
| Southeast Block 31 | Parts back-ordered | 6 | 15% | 8.5 |
| Southeast Block 31 | Weather (road impassable) | 8 | 20% | 12.5 |
| Southeast Block 31 | Workover rig busy | 13 | 32% | 14.0 |
| Southeast Block 32 | Contractor slot | 32 | 23% | 9.0 |
| Southeast Block 32 | Crew on spill response | 21 | 15% | 10.0 |
| Southeast Block 32 | Parts back-ordered | 26 | 19% | 9.5 |
| Southeast Block 32 | Weather (road impassable) | 31 | 22% | 8.0 |
| Southeast Block 32 | Workover rig busy | 29 | 21% | 9.0 |

(35 rows total)

498 of 4360 jobs started in 2026 had a well shut in longer than the repair itself (report sentence 'stayed shut in for about N days longer…'); 'Workover rig busy' is a separate waiting sentence in reports and is listed on its own.  
Area with the highest share of jobs hit by a post-repair delay: Northeast Block 8 (15% of its jobs); lowest: Southeast Block 31 (8%).  
Most common reason per area: Northeast Block 7: Contractor slot (15 jobs); Northeast Block 8: Crew on spill response (19 jobs); Northwest Block 12: Workover rig busy (43 jobs); Southeast Block 31: Workover rig busy (13 jobs); Southeast Block 32: Contractor slot (32 jobs); Southwest Block 23: Weather (road impassable) (16 jobs); Southwest Block 24: Contractor slot (17 jobs).

Evidence: MNT-0001-028, MNT-0001-033, MNT-0002-018, MNT-0002-020, MNT-0004-021, MNT-0004-026, MNT-0005-031, MNT-0006-023, MNT-0006-025, MNT-0006-026, MNT-0007-031, MNT-0009-026

## Q21 (Olivia Grant, chat 14)
**Which region of the field consistently runs hotter?**

The Southeast Block 31 consistently runs hotter with an average wellhead temperature of 53.0°C and an average wellhead above air temperature of 31.5°C. Other areas and their average wellhead temperatures are: Southeast Block 32 (50.5°C), Northwest Block 12 (50.1°C), Southwest Block 23 (48.8°C), Northeast Block 7 (48.8°C), Southwest Block 24 (48.4°C), and Northeast Block 8 (48.2°C). This analysis is based on average wellhead temperature over the last 12 months, with wellhead-above-air shown beside it because air temperature differs by area.

*Visual: bar*

| Area | Avg wellhead (°C) | Avg air (°C) | Avg wellhead above air (°C) | Readings |
|---|---|---|---|---|
| Southeast Block 31 | 53.0 | 21.6 | 31.5 | 2468 |
| Southeast Block 32 | 50.5 | 21.7 | 28.8 | 7795 |
| Northwest Block 12 | 50.1 | 21.8 | 28.3 | 7800 |
| Southwest Block 23 | 48.8 | 21.8 | 27.0 | 3285 |
| Northeast Block 7 | 48.8 | 21.7 | 27.1 | 3220 |
| Southwest Block 24 | 48.4 | 21.8 | 26.6 | 3263 |
| Northeast Block 8 | 48.2 | 21.8 | 26.4 | 3221 |

'Hotter' read as average wellhead temperature over the last 12 months, with wellhead-above-air shown beside it because air temperature differs by area.
