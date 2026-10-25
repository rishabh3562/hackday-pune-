"""Open-ended analysis as a LAST RESORT: the model writes ONE read-only DuckDB query over the corrected data; code validates and runs it.
Safety: SELECT/WITH only, single statement, forbidden keywords and file/network functions rejected, EXPLAIN-validated, row-capped, in-memory DB.
Auditability: the SQL is returned and shown with every answer, and the answer is labelled ad-hoc (less verified than the typed tools)."""
import json
import re

import duckdb
import pandas as pd

from .data import TODAY_ISO
from .tools import Engine

FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|attach|detach|copy|pragma|install|load|export|import|call|set|truncate|replace|merge|vacuum|read_csv|read_parquet|read_json|glob|httpfs|http_get)\b", re.I)
MAX_ROWS = 200


def _flat(df):
    df = df.copy()
    for c in list(df.columns):
        if df[c].map(lambda v: isinstance(v, (list, dict))).any():
            df = df.drop(columns=[c])
    for c in df.columns:
        if str(df[c].dtype).startswith("datetime64[ns, "):
            df[c] = df[c].dt.tz_convert("UTC").dt.tz_localize(None)
    return df


def _connection(e: Engine):
    ds, con = e.ds, duckdb.connect(":memory:")
    inc = ["inspection_id", "asset_id", "ts", "inspector_user_id", "method", "ambient_temp_c", "wellhead_temp_c", "spill_detected", "spill_area_pct", "spill_est_volume_bbl",
           "notes", "well_type", "area_id", "delta", "threshold", "producing", "correction"]
    tables = {"wells": ds.w.drop(columns=["location"]), "inspections": e.inspections()[inc], "maintenance": ds.m.drop(columns=["cost_usd"]).rename(columns={"cost_total": "cost_usd_total"}),
              "regulatory_events": ds.r, "human_notes": ds.n, "users": pd.DataFrame(ds.users), "areas": pd.DataFrame(ds.areas).drop(columns=["asset_ids", "center"], errors="ignore")}
    for name, df in tables.items():
        con.register(name, _flat(df))
    return con


def _schema(con):
    out = []
    for (t,) in con.execute("SHOW TABLES").fetchall():
        cols = con.execute(f"DESCRIBE {t}").fetchall()
        out.append(f"{t}({', '.join(f'{c[0]} {c[1]}' for c in cols)})")
    return "\n".join(out)


PROMPT = """You write ONE read-only DuckDB SQL query that answers an oil-field operator's question. Today is {today}.
Tables:
{schema}
Facts about the data: inspections are weekly per well; inspections.producing already applies the well-type temperature rule and any user corrections (wellhead_temp_c is the corrected value).
Downtime days = 7 * count of inspections where producing is false. A real spill = spill_detected true (corrections already applied). maintenance.maintenance_type is 'corrective' or 'scheduled';
maintenance.ts is the start time; cost is cost_usd_total. Use area_id/well_type/asset_id joins; names of areas are in areas.name, people in users.name.
Return JSON {{"sql":"<single SELECT or WITH query>","explain":"<one sentence: what the query computes>"}}. Select explicit, readable columns, add ORDER BY, and keep it to at most {cap} rows."""


def _validate(sql):
    s = re.sub(r"--.*?$|/\*.*?\*/", "", sql, flags=re.S | re.M).strip().rstrip(";").strip()
    if ";" in s: raise ValueError("only one statement is allowed")
    if not re.match(r"^(select|with)\b", s, re.I): raise ValueError("only SELECT/WITH queries are allowed")
    if FORBIDDEN.search(s): raise ValueError("the query uses a forbidden keyword or function")
    return s


def sql_query(self, question):
    from .agent import call_llm, parse_json
    con = _connection(self)
    msgs = [{"role": "system", "content": PROMPT.format(today=TODAY_ISO, schema=_schema(con), cap=MAX_ROWS)}, {"role": "user", "content": question}]
    err, last = None, None
    for _ in range(3):
        try:
            plan = parse_json(call_llm(msgs + ([{"role": "assistant", "content": json.dumps(last)}, {"role": "user", "content": f"That failed: {err}. Fix the query and reply with the same JSON."}] if err else []), 900, json_mode=True, label="sql"))
            last, sql = plan, _validate(plan["sql"])
            con.execute("EXPLAIN " + sql)
            df = con.execute(f"SELECT * FROM ({sql}) LIMIT {MAX_ROWS}").fetchdf()
            for c in df.columns:
                if str(df[c].dtype).startswith("datetime64"): df[c] = df[c].astype(str)
            rows = json.loads(df.to_json(orient="records", date_format="iso"))
            return {"visual": "table", "rows": rows, "citations": [], "sql": sql, "explain": plan.get("explain", ""),
                    "notes": [f"Ad-hoc query written by the model and run read-only on the corrected data: {plan.get('explain', '')}", f"{len(rows)} row(s)" + (f" (capped at {MAX_ROWS})" if len(rows) == MAX_ROWS else "")]}
        except Exception as ex:  # noqa: BLE001
            err = str(ex)[:240]
    return {"visual": "text", "rows": [], "citations": [], "notes": [f"I could not turn that into a safe query ({err})."], "error": f"I could not turn that into a safe query ({err})."}


Engine.sql_query = sql_query
