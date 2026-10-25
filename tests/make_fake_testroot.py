"""Build a stand-in 'test dataset': new wells WELL-0201.. cloned from existing ones, in a new area, own fleet/ files."""
import json, os, shutil
src, dst = "data/repo/sample-data", "data/fake_test/sample-data"
shutil.rmtree("data/fake_test", ignore_errors=True)
os.makedirs(f"{dst}/assets"); shutil.copytree(f"{src}/fleet", f"{dst}/fleet")
new = []
for k in range(5):
    old, nid = f"WELL-{10 + k:04d}", f"WELL-{201 + k:04d}"
    o4, n4 = old[-4:], nid[-4:]
    shutil.copytree(f"{src}/assets/{old}", f"{dst}/assets/{nid}")
    for root, _, files in os.walk(f"{dst}/assets/{nid}"):
        for f in files:
            p = os.path.join(root, f)
            t = open(p).read().replace(old, nid).replace(f"-{o4}-", f"-{n4}-")
            if f == "metadata.json":
                m = json.loads(t); m["area_id"] = "NW-31"; m["team_id"] = "TEAM-NW"; m["name"] = f"NW-31 Well {n4[1:]}"
                m["equipment"] = [dict(e, equipment_id=e["equipment_id"].replace(old, nid)) for e in m["equipment"]]; t = json.dumps(m, indent=2)
            open(p, "w").write(t)
    new.append(nid)
a = json.load(open(f"{dst}/fleet/areas.json"))
a["areas"].append({"area_id": "NW-31", "name": "Northwest Block 31", "team_id": "TEAM-NW", "center": {"lat": 32.5, "lon": -102.9}, "asset_ids": new})
a["teams"].append({"team_id": "TEAM-NW", "name": "Northwest Production", "lead_user_id": "U-201"})
json.dump(a, open(f"{dst}/fleet/areas.json", "w"), indent=2)
print("built", new)
