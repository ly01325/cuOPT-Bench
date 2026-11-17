"""Solve an MPS model with an OR-Tools solver (SCIP, HiGHS, ...) through model_builder.

usage: python run_ortools.py SOLVER model.mps TIME_LIMIT_S [SOLVER_PARAMS] [SOLUTION_OUT]

  SOLVER          scip | highs | ... (any name accepted by ModelSolver)
  SOLVER_PARAMS   passed to set_solver_specific_parameters. SCIP accepts exactly ONE "key = value" here,
                  e.g. "numerics/feastol = 1e-5". Several parameters in one string are rejected
                  with INVALID_SOLVER_PARAMETERS. Use "" to skip.
  SOLUTION_OUT    optional: write every nonzero variable as "name value" (input of verify_solution.py)

The last line printed is  @@RESULT@@ <status> <objective> solve_s <seconds>  (parsed by summarize_logs.py).
"""
import sys
import time

from ortools.linear_solver.python import model_builder as mb

if len(sys.argv) < 4:
    sys.exit(__doc__)
name, mps, tl = sys.argv[1], sys.argv[2], float(sys.argv[3])
params = sys.argv[4] if len(sys.argv) > 4 else ""
sol_out = sys.argv[5] if len(sys.argv) > 5 else ""

m = mb.ModelBuilder()
t = time.time()
if not m.import_from_mps_file(mps):
    sys.exit(f"could not import {mps}")
print("import s", round(time.time() - t, 1), flush=True)

s = mb.ModelSolver(name)
s.enable_output(True)
s.set_time_limit_in_seconds(tl)
if params:
    s.set_solver_specific_parameters(params)
    print("params:", params, flush=True)

t = time.time()
status = s.solve(m)
wall = time.time() - t
ok = status.name in ("OPTIMAL", "FEASIBLE")
print("@@RESULT@@", status.name, s.objective_value if ok else None, "solve_s", round(wall, 1), flush=True)

if ok and sol_out:
    with open(sol_out, "w") as f:
        for v in m.get_variables():
            x = s.value(v)
            if x != 0:
                f.write(f"{v.name} {x!r}\n")
    print("solution written", sol_out, flush=True)
