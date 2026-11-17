"""Turn the logs written by run_compare.sh into a Markdown table.

usage: python summarize_logs.py OUTDIR

Reads OUTDIR/{cuopt_pr_1,cuopt_pr_2,cuopt_orig,highs,scip}.log (missing files are skipped).
Columns: total wall time, presolve, LP / solve stage, final status.

What each number is
  total      the last line "WALL <s>" of each log (the whole process, including reading and writing)
  cuOPT      presolve = Papilo + cuOpt presolve; LP = "Concurrent time" (root LP of the presolved problem)
  HiGHS      presolve and solve are the values HiGHS prints in its own "Timing" block
  SCIP       presolve = "Presolving Time"; solve = "Solving Time" minus presolve (an estimate)
The status column only repeats what the solver printed. It does NOT mean the solution is feasible:
check every solution with verify_solution.py.
"""
import os
import re
import sys

NUM = r"[-+]?\d+\.?\d*(?:[eE][-+]?\d+)?"


def grab(text, pattern, group=1, last=False):
    found = re.findall(pattern, text)
    if not found:
        return None
    v = found[-1] if last else found[0]
    return float(v if isinstance(v, str) else v[group - 1])


def fmt(v, nd=1):
    return "-" if v is None else f"{v:.{nd}f}"


def cuopt(text):
    papilo = grab(text, rf"Papilo presolve time:\s*({NUM})")
    cu_pre = grab(text, rf"cuOpt presolve time:\s*({NUM})")
    pre = None if papilo is None and cu_pre is None else (papilo or 0) + (cu_pre or 0)
    lp = grab(text, rf"Concurrent time:\s*({NUM})")
    iters = grab(text, r"Iterations:\s*(\d+)", last=True)
    if "no integer feasible solution" in text:
        status = "no solution (\"no integer feasible solution\")"
    elif "Writing solution to file" in text:
        status = "solution written"
    else:
        status = "see log"
    obj = grab(text, rf"Best objective\s+({NUM})")
    if obj is not None:
        status = f"solution written, objective {obj:.7g}"
    if "Post solved solution violates constraints" in text:
        status += "; post-solve warning"
    if iters is not None:
        status += f"; PDLP iterations {int(iters)}"
    return pre, lp, status


def highs(text):
    pre = grab(text, rf"({NUM})\s*\(Presolve\)")
    solve = grab(text, rf"({NUM})\s*\(Solve\)")
    m = re.search(r"run s [\d.]+ status (.+)", text)
    status = m.group(1).strip() if m else "see log"
    if "no primal solution" in text:
        status += "; no primal solution"
    elif "max row viol" in text:
        status += "; " + re.search(r"max row viol.*", text).group(0)
    return pre, solve, status


def scip(text):
    pre = grab(text, rf"Presolving Time:\s*({NUM})")
    total = grab(text, rf"Solving Time \(sec\)\s*:\s*({NUM})")
    solve = total - pre if total is not None and pre is not None else None
    m = re.search(r"@@RESULT@@ (\S+) (\S+)", text)
    status = f"{m.group(1)}, objective {m.group(2)}" if m else "see log"
    return pre, solve, status


PARSERS = [("cuopt_pr_1", "cuOPT (PR build), run 1", cuopt), ("cuopt_pr_2", "cuOPT (PR build), run 2", cuopt),
           ("cuopt_orig", "cuOPT (released)", cuopt), ("highs", "HiGHS (native)", highs), ("scip", "SCIP via OR-Tools", scip)]

if len(sys.argv) != 2:
    sys.exit(__doc__)
d = sys.argv[1]
print("| solver | total (s) | presolve (s) | LP / solve (s) | status as printed by the solver |")
print("|---|---:|---:|---:|---|")
for key, label, parse in PARSERS:
    path = os.path.join(d, key + ".log")
    if not os.path.exists(path):
        continue
    text = open(path, errors="replace").read()
    wall = float(re.findall(r"^WALL\s+(" + NUM + ")", text, re.M)[-1]) if re.search(r"^WALL", text, re.M) else None
    pre, solve, status = parse(text)
    print(f"| {label} | {fmt(wall)} | {fmt(pre)} | {fmt(solve, 2 if key.startswith('cuopt') else 1)} | {status} |")
