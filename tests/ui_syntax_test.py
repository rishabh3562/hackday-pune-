"""Every front-end module must parse (a missing paren means a blank page). Run: .venv/bin/python tests/ui_syntax_test.py"""
import glob, subprocess, sys
bad = 0
for f in sorted(glob.glob("static/js/**/*.js", recursive=True)):
    code = subprocess.run(["node", "--input-type=module", "-e", f"import fs from 'fs'; new Function(fs.readFileSync('{f}','utf8').replace(/^import .*$/gm,'').replace(/^export /gm,''))"], capture_output=True, text=True)
    ok = code.returncode == 0; bad += not ok; print(("PASS " if ok else "FAIL ") + f, "" if ok else code.stderr.strip().splitlines()[-1][:120])
sys.path.insert(0, "tests"); import _results; _results.save("ui-syntax", [{"id": f, "desc": f, "ok": True} for f in sorted(glob.glob("static/js/**/*.js", recursive=True))] if not bad else [{"id": "ui", "desc": "a module failed to parse", "ok": False}])
print("FAILS:", bad); sys.exit(1 if bad else 0)
