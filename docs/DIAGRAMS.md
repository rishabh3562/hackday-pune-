# Asset Intelligence Copilot: visual guide

Colour key used in every diagram: 🟧 user / UI · 🟪 LLM (thin: plan + write) · 🟩 deterministic code · ⬜ stores · 🟥 guards.

## 1. The whole system in one picture
The LLM only plans and writes. Every number comes from code over typed stores, and a guard checks the prose before it is shown.

```mermaid
flowchart LR
  U([👤 Operator<br/>picks a user]):::ui --> P{{"🧠 Planner<br/>1 LLM call → JSON plan"}}:::llm
  P -->|query| X["⚙️ 34 tools<br/>no LLM inside"]:::det
  P -->|statement| S["📝 Statement handlers<br/>correction · rule · note · claim"]:::det
  P -->|ambiguous| C["❓ Clarify<br/>2-4 options + free text"]:::ui
  X --> D[("🗄️ Records<br/>pandas + DuckDB")]:::store
  X --> H["🔎 Hybrid doc search<br/>BM25 + Chroma vectors"]:::det
  S --> F[("🧾 Facts log<br/>SQLite overlay")]:::store
  F -. applied when read .-> D
  X --> W{{"✍️ Writer<br/>tool result only"}}:::llm
  X --> BL["🧩 Blocks composer<br/>4-8 visual blocks, 0 tokens"]:::det --> R
  W --> G{"🛡️ Grounding guard<br/>IDs · numbers · every row · contradictions"}:::guard
  G -->|ok| CR{{"🕵️ Critic sub-agent<br/>Gemini 2.5 Pro"}}:::llm
  CR -->|ok or one rewrite| R["🖼️ Typed UI spec<br/>blocks + evidence + context"]:::ui
  G -->|fails twice| T["📄 Template answer"]:::guard --> R
  C --> U
  R --> U
  classDef ui fill:#fff4dd,stroke:#f5a524,color:#1d2433
  classDef llm fill:#eef0ff,stroke:#4f46e5,color:#1d2433
  classDef det fill:#e8f7f4,stroke:#0f9d8a,color:#1d2433
  classDef store fill:#f1f5f9,stroke:#5b6577,color:#1d2433
  classDef guard fill:#ffe9e9,stroke:#e5484d,color:#1d2433
```

## 2. Each kind of data gets the store that fits its shape
```mermaid
flowchart TB
  subgraph IN["📥 What we are given"]
    A1["Inspections ~40k<br/>weekly temps, spills"]:::in
    A2["Repairs ~5.7k<br/>+ 1.5k free-text reports"]:::in
    A3["Regulator events · notes"]:::in
    A4["Manuals & SOPs<br/>rules in prose"]:::in
    A5["What users tell us<br/>corrections, rules, claims"]:::in
    A6["Who asked what, when"]:::in
  end
  subgraph OUT["🗄️ Where it lives"]
    B1[("Tables: pandas in memory<br/>+ DuckDB system of record")]:::st
    B2[("Root-cause column<br/>lifted from reports")]:::st
    B3[("Chunks + BM25 + embeddings<br/>applicability metadata")]:::st
    B4[("Rules registry<br/>value + source section")]:::st
    B5[("SQLite facts<br/>append-only, selector, status")]:::st
    B6[("SQLite convo<br/>user · time · entity IDs")]:::st
  end
  A1 --> B1
  A2 --> B1 & B2 & B3
  A3 --> B1 & B3
  A4 --> B3 & B4
  A5 --> B5
  A6 --> B6
  classDef in fill:#fff4dd,stroke:#f5a524
  classDef st fill:#e8f7f4,stroke:#0f9d8a
```
No vector server, no graph DB, no NoSQL: the data is small, structured, and linked by plain IDs.

## 3. Ingestion: one command over any number of dataset roots
```mermaid
flowchart LR
  R1["📁 sample-data"]:::in --> L
  R2["📁 test-data<br/>(new wells, areas)"]:::in --> L
  L["Locate fleet/ + assets/<br/>merge by ID, later root wins"]:::det --> RU["Parse rules from manual/SOP text<br/>+ section provenance<br/>warn, never crash"]:::det
  L --> LF["Lift facts from reports<br/>containment hours · root cause"]:::det
  L --> CH["Chunk (passages) + embed<br/>cached; Chroma collection"]:::det
  RU --> DB[("DuckDB<br/>store.duckdb")]:::st
  LF --> DB
  CH --> IDX[("Search index")]:::st
  DB --> V["✅ Validate<br/>golden · SQL cross-check · 50 core scenarios"]:::guard
  classDef in fill:#fff4dd,stroke:#f5a524
  classDef det fill:#e8f7f4,stroke:#0f9d8a
  classDef st fill:#f1f5f9,stroke:#5b6577
  classDef guard fill:#ffe9e9,stroke:#e5484d
```

## 4. Corrections are an overlay, never an overwrite
```mermaid
sequenceDiagram
  autonumber
  actor M as Michael (supervisor)
  participant A as Agent
  participant F as Facts log
  participant E as Effective view
  actor J as Jessica (inspector)
  M->>A: "All manual readings in NE-8, 1 Sep–15 Oct, read 6° low"
  A->>A: extract {selector, op=add, value=6, reason}
  A->>M: "That changes 248 rows across 31 wells. Apply?"
  M->>A: "Apply to all"
  A->>F: append correction #7 (author, scope, status=confirmed)
  Note over F,E: raw data untouched
  J->>A: "Is WELL-0164 producing?"
  A->>E: read raw rows + apply active corrections
  E-->>A: 29.0 °C (was 24.0), source #7 by Michael
  A->>J: "Yes — corrected by Michael Turner (+6 °C, gun fault)"
  M->>A: "Undo my last correction"
  A->>F: #7 → revoked (kept in the audit log)
```

## 5. Correction lifecycle and who wins
```mermaid
stateDiagram-v2
  direction LR
  [*] --> confirmed: user states it
  [*] --> unconfirmed: contradicts the data
  unconfirmed --> confirmed: inspection / user confirms
  confirmed --> superseded: newer correction, same selector + field
  confirmed --> revoked: "undo"
  unconfirmed --> revoked: "undo"
  superseded --> [*]
  revoked --> [*]
  note right of confirmed
    Precedence when several apply to one row:
    inspection > well > area > well type > fleet,
    then latest wins. Overlaps are reported.
  end note
```

## 6. "The wells we discussed…", even months later
```mermaid
flowchart TD
  Q(["“the three wells we discussed in April”"]):::ui --> H[("This user's own answers<br/>time · tool · entity IDs")]:::st
  H --> N{"how many wells named?<br/>(three → 3)"}:::det
  N --> T{"time phrase?<br/>yesterday · last month · April"}:::det
  T -->|window has matches| M{"more than one<br/>distinct set?"}:::det
  T -->|none in window| FB["use latest match<br/>and say so"]:::guard --> M
  M -->|no| A["✅ answer for that set"]:::det
  M -->|yes, ask mode| K["❓ ask: which set?<br/>options with dates"]:::ui
  M -->|yes, auto mode| L["use latest, list the others"]:::det
  H -. none at all .-> NO["“I have no earlier conversation<br/>with you about that”"]:::guard
  classDef ui fill:#fff4dd,stroke:#f5a524
  classDef st fill:#f1f5f9,stroke:#5b6577
  classDef det fill:#e8f7f4,stroke:#0f9d8a
  classDef guard fill:#ffe9e9,stroke:#e5484d
```

## 7. The clarification loop
One short question, grounded options, free text always allowed. In `auto` mode (no human, e.g. the graded run) it never asks and states its assumption instead.
```mermaid
flowchart TD
  M(["User message"]):::ui --> P{{"Planner"}}:::llm
  P -->|clear| RUN["Run tools → grounded answer"]:::det
  P -->|"ambiguous, and a wrong guess<br/>changes the answer"| MODE{"mode"}:::det
  MODE -->|ask| ASK["❓ One question<br/>2-4 options + free text"]:::ui
  MODE -->|auto| ASSUME["Pick best default<br/>show “Assumed: …”"]:::guard --> RUN
  ASK --> ANS(["User clicks an option<br/>or types an answer"]):::ui --> MERGE["Reply + original request<br/>→ full plan"]:::llm --> RUN
  RUN --> BIG{"change touches<br/>> 150 rows?"}:::det
  BIG -->|yes| CONF["❓ Confirm: Apply to all N / narrow"]:::ui
  BIG -->|no| OUT([Answer + evidence]):::ui
  CONF -->|Apply| OUT
  CONF -->|No| CANCEL["nothing recorded"]:::guard
  classDef ui fill:#fff4dd,stroke:#f5a524
  classDef llm fill:#eef0ff,stroke:#4f46e5
  classDef det fill:#e8f7f4,stroke:#0f9d8a
  classDef guard fill:#ffe9e9,stroke:#e5484d
```

## 8. “Which wells are failing due to mud?”: text lifted into structure
```mermaid
flowchart LR
  subgraph ING["At ingest (once)"]
    R["1.5k repair reports"]:::in --> RC["Root cause column<br/>~25 distinct phrasings"]:::st
  end
  subgraph Q["At query time"]
    C(["concept: “mud”"]):::ui --> SH["Shortlist phrasings<br/>BM25 overlap + embeddings"]:::det
    RC --> SH --> J{{"LLM judge, 25 short lines<br/>exact · related · nearest + why"}}:::llm
    J --> LIT{"word appears<br/>literally?"}:::det
    LIT -->|yes| AGG["SQL-style aggregation<br/>wells · reports · cost · last date · quote"]:::det
    LIT -->|"no (mud: 0 records)"| OPT["❓ “No record mentions mud.<br/>Closest causes:<br/>sand/scale 37 reports, 34 wells …”<br/>pick one"]:::ui
    OPT --> AGG
  end
  AGG --> TB([Table + verbatim quote per row]):::ui
  classDef in fill:#fff4dd,stroke:#f5a524
  classDef st fill:#f1f5f9,stroke:#5b6577
  classDef ui fill:#fff4dd,stroke:#f5a524
  classDef det fill:#e8f7f4,stroke:#0f9d8a
  classDef llm fill:#eef0ff,stroke:#4f46e5
```

## 9. Why hybrid search (and a graph without a graph DB)
```mermaid
flowchart TB
  Q(["query"]):::ui --> B["BM25<br/>exact tokens: SR-02, MNT-0001-029,<br/>“stuffing box”"]:::det
  Q --> V["Embeddings<br/>meaning: “how fast must a leak<br/>be contained”"]:::det
  B --> RRF["Reciprocal rank fusion"]:::det
  V --> RRF
  RRF --> BO["Boost applicability<br/>this well's reports · its type's manual · fleet SOPs"]:::det
  BO --> TOP([Top chunks with section + source]):::ui
  classDef ui fill:#fff4dd,stroke:#f5a524
  classDef det fill:#e8f7f4,stroke:#0f9d8a
```
```mermaid
erDiagram
  WELL ||--o{ INSPECTION : "weekly"
  INSPECTION ||--o{ MAINTENANCE : "triggered_by"
  MAINTENANCE ||--o| REPORT : "report_file"
  INSPECTION ||--o{ REGULATORY_EVENT : "related_inspection"
  INSPECTION ||--o{ NOTE : "correction / mention"
  INSPECTION ||--o{ FACT : "user correction"
  WELL }o--|| WELL_TYPE : "manual + thresholds"
  WELL_TYPE ||--o{ RULE : "section"
```
`trace(entity_id)` walks these ID links, so impact and provenance questions need no graph database.

## 10. One answer, many visualizations
```mermaid
flowchart LR
  T["⚙️ Tool result<br/>rows + notes + citations"]:::det --> C{{"🧩 blocks.py<br/>deterministic composer"}}:::det
  C --> K["KPI tiles"]:::blk
  C --> CA["Callouts<br/>stale status · corrections · notes"]:::blk
  C --> ST["Status card"]:::blk
  C --> CH["Bar · Line · Donut · Scatter"]:::blk
  C --> HM["Heatmap"]:::blk
  C --> MP["Map pins"]:::blk
  C --> TL["Event timeline"]:::blk
  C --> TB["Table"]:::blk
  K & CA & ST & CH & HM & MP & TL & TB --> R["📦 blocks.js<br/>one framework-free renderer"]:::ui
  R --> P["Plain UI"]:::ui
  R --> CK["CopilotKit UI<br/>(thin React host)"]:::ui
  classDef det fill:#e8f7f4,stroke:#0f9d8a
  classDef blk fill:#eef0ff,stroke:#4f46e5
  classDef ui fill:#fff4dd,stroke:#f5a524
```

## 11. Evidence: scenarios and models
```mermaid
pie showData title 50 core scenarios (+19 extended tests)
  "Given by the challenge (18)" : 18
  "Extra medium + complex (22)" : 22
  "Design review, core (10)" : 10
```
```mermaid
xychart-beta
  title "Router-only benchmark, 40 questions (right tool and kind)"
  x-axis ["Gemini 2.5 Flash", "Gemma 4 26B-A4B"]
  y-axis "correct" 0 --> 40
  bar [40, 35]
```
```mermaid
mindmap
  root((Awards))
    Asset Intelligence Copilot
      Deterministic engine
      Corrections overlay
      Clarification loop
      Grounding check
    Best use of Gemma 4
      Same planner on Gemma 4 26B-A4B via Vertex
      35/40 vs Gemini 40/40
    Best open source
      CopilotKit + AG-UI
      DuckDB
      BM25 + embeddings
      Playwright, Mermaid
```
