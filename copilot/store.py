"""Persist the normalised records to DuckDB: a SQL-queryable system of record with provenance, rebuilt by every ingest.
Corrections are NOT written here; they stay in the append-only facts table and are applied as an overlay when read."""
import json
import os

import duckdb
import pandas as pd


def _flat(df):
    df = df.copy()
    for c in df.columns:
        if df[c].map(lambda v: isinstance(v, (list, dict))).any():
            df[c] = df[c].map(lambda v: json.dumps(v) if isinstance(v, (list, dict)) else v)
    for c in df.columns:
        if str(df[c].dtype).startswith("datetime64[ns, "):
            df[c] = df[c].dt.tz_convert("UTC").dt.tz_localize(None)
    return df


def to_duckdb(ds, path="data/store.duckdb"):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if os.path.exists(path):
        os.remove(path)
    con = duckdb.connect(path)
    tables = {"wells": ds.w.drop(columns=["location"]), "inspections": ds.i, "maintenance": ds.m.drop(columns=["contain_hours"]).assign(
        containment_hours=ds.m.contain_hours), "regulatory_events": ds.r, "human_notes": ds.n,
        "rules": pd.DataFrame([{"rule": f"producing_delta_{k}", "value": v, "source": ds.rules["prov"].get(f"producing_delta:{k}", "")}
                               for k, v in ds.rules["producing_delta"].items()] +
                              [{"rule": k, "value": v, "source": ds.rules["prov"].get(k, "fleet/sops")} for k, v in ds.rules.items() if isinstance(v, float)])}
    for name, df in tables.items():
        con.register("tmp_df", _flat(df))
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM tmp_df")
        con.unregister("tmp_df")
    con.execute("""CREATE VIEW inspections_effective_raw AS
        SELECT i.*, (i.wellhead_temp_c - i.ambient_temp_c) >= r.value AS producing
        FROM inspections i JOIN rules r ON r.rule = 'producing_delta_' || i.well_type""")
    con.close()
    return path
