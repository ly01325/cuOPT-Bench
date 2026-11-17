"""Convert an LP (or any format HiGHS reads) file to MPS. cuopt_cli reads MPS directly.
usage: python convert_lp_to_mps.py model.lp model.mps"""
import sys
import time

import highspy

if len(sys.argv) != 3:
    sys.exit(__doc__)

h = highspy.Highs()
h.setOptionValue("output_flag", False)
t = time.time()
if h.readModel(sys.argv[1]) != highspy.HighsStatus.kOk:
    sys.exit(f"could not read {sys.argv[1]}")
lp = h.getLp()
print(f"read   {time.time() - t:6.1f} s   rows={lp.num_row_} cols={lp.num_col_} nnz={lp.a_matrix_.start_[-1]}")
t = time.time()
h.writeModel(sys.argv[2])
print(f"wrote  {time.time() - t:6.1f} s   {sys.argv[2]}")
