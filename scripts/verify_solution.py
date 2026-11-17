"""Independent check of a solution against the ORIGINAL model. Do not trust a solver's own "optimal" status.

usage: python verify_solution.py model.mps solution.txt

solution.txt holds "name value" lines for the variables (variables that are not listed count as 0).
Lines that do not end in a number, such as the "# Status: ..." header of a cuopt_cli solution file,
are ignored. The same file layout is written by run_ortools.py.

Reports: objective value, largest row violation (absolute and relative to the row's right-hand side),
number of rows violated by more than 1e-6, largest bound violation, largest distance of an integer
variable from an integer.
"""
import sys

import highspy
import numpy as np

if len(sys.argv) != 3:
    sys.exit(__doc__)

h = highspy.Highs()
h.setOptionValue("output_flag", False)
h.readModel(sys.argv[1])
lp = h.getLp()
n, m = lp.num_col_, lp.num_row_
idx = {nm: i for i, nm in enumerate(lp.col_names_)}

x = np.zeros(n)
for ln in open(sys.argv[2]):
    parts = ln.rsplit(" ", 1)
    if len(parts) != 2 or parts[0] not in idx:
        continue
    try:
        x[idx[parts[0]]] = float(parts[1])
    except ValueError:
        pass

A = lp.a_matrix_  # column-wise sparse matrix
cnt = np.diff(np.array(A.start_))
ax = np.bincount(np.array(A.index_), weights=np.array(A.value_) * np.repeat(x, cnt), minlength=m)
rl, ru = np.array(lp.row_lower_), np.array(lp.row_upper_)
viol = np.maximum(np.maximum(rl - ax, ax - ru), 0)
rhs = np.maximum(1.0, np.maximum(np.abs(np.where(np.isfinite(rl), rl, 0)), np.abs(np.where(np.isfinite(ru), ru, 0))))
bl, bu = np.array(lp.col_lower_), np.array(lp.col_upper_)
bviol = np.maximum(np.maximum(bl - x, x - bu), 0)
is_int = np.array([t != highspy.HighsVarType.kContinuous for t in lp.integrality_])
frac = np.abs(x[is_int] - np.round(x[is_int])) if is_int.any() else np.zeros(1)
obj = float(np.dot(np.array(lp.col_cost_), x)) + lp.offset_

print(f"vars={n} rows={m} nonzero vars={int((x != 0).sum())}")
print(f"objective = {obj:.6f}")
print(f"row violation: max abs {viol.max():.3e}, rows>1e-6 abs: {int((viol > 1e-6).sum())}, "
      f"rows>1e-6 rel(to rhs scale): {int((viol / rhs > 1e-6).sum())}, max rel {(viol / rhs).max():.3e}")
print(f"bound violation max {bviol.max():.3e}; integer fractionality max {frac.max():.3e}, >1e-6: {int((frac > 1e-6).sum())}")
