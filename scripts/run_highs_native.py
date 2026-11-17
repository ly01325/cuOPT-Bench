"""Solve an MPS model with HiGHS through its native Python interface (highspy), without OR-Tools in between.

usage: python run_highs_native.py model.mps TIME_LIMIT_S OUTDIR [key=value ...]

Extra HiGHS options are given as key=value (numbers are typed automatically), e.g. primal_feasibility_tolerance=1e-9.
OR-Tools re-checks a HiGHS solution and may report a different status than HiGHS itself, so use this
script when you want HiGHS's own behaviour. If HiGHS returns a primal solution, the script prints the
largest row violation and writes OUTDIR/highs_native.sol.
"""
import sys
import time

import highspy
import numpy as np

if len(sys.argv) < 4:
    sys.exit(__doc__)
mps, tl, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]

h = highspy.Highs()
h.setOptionValue("output_flag", True)
h.setOptionValue("log_to_console", True)
h.setOptionValue("time_limit", tl)
h.setOptionValue("mip_rel_gap", 0.01)
for kv in sys.argv[4:]:
    k, v = kv.split("=", 1)
    try:
        v = int(v)
    except ValueError:
        try:
            v = float(v)
        except ValueError:
            pass
    print("option", k, v, h.setOptionValue(k, v), flush=True)

h.readModel(mps)
t = time.time()
h.run()
print("run s", round(time.time() - t, 1), "status", h.modelStatusToString(h.getModelStatus()), flush=True)
info = h.getInfo()
print("primal obj", info.objective_function_value, "bound", info.mip_dual_bound, "gap", info.mip_gap, flush=True)

if info.primal_solution_status == 2:  # a feasible primal solution is available
    lp = h.getLp()
    sol = h.getSolution()
    ax = np.array(sol.row_value)
    rl, ru = np.array(lp.row_lower_), np.array(lp.row_upper_)
    viol = np.maximum(np.maximum(rl - ax, ax - ru), 0)
    print("max row viol", viol.max(), "rows viol>1e-6:", int((viol > 1e-6).sum()), flush=True)
    h.writeSolution(f"{out}/highs_native.sol", 1)
else:
    print("no primal solution", flush=True)
