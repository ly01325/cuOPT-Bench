# 3. Interpreting the results

## 3.1 Where each number comes from

| Number | Source |
|---|---|
| total time | last line `WALL <s>` of each log: the whole process, including reading the model and writing the solution |
| cuOPT presolve | `Papilo presolve time` + `cuOpt presolve time` |
| cuOPT LP | `Concurrent time` (root LP of the presolved problem; PDLP, dual simplex and barrier race) |
| cuOPT "restore and output" | total minus read, presolve and LP (an estimate) |
| HiGHS presolve / solve | the `Timing` block HiGHS prints at the end |
| SCIP presolve / solve | `Presolving Time`; `Solving Time` minus presolve (an estimate) |

`summarize_logs.py` does this for you. Whatever you derive by subtraction, call it an estimate in the report.

## 3.2 What counts as a "success"

Do not use the status a solver prints. Use one yardstick for all solvers, on the original model, with `verify_solution.py`:

1. a solution file exists and is not empty (a cuOPT solution file of about 20 bytes means "no solution");
2. the objective agrees with the other solvers (when the LP relaxation equals the MIP optimum, all optimal solutions share one value);
3. integer variables are integral (distance from an integer at most 1e-6);
4. the largest constraint violation, and the **number** of violated rows, are acceptable for your application. Report both.

Two solutions with the same objective can fail differently: one can violate few rows by a large amount, another many rows by a
small amount. Which is acceptable depends on what those rows mean.

## 3.3 Things that distort a comparison

- **PR build versus released build are different code.** A PR is usually based on the development branch. In the original case
  the PR build presolved the model much faster than the released version, but the log showed a different thread budget
  (`Papilo thread budget` line), so the speed-up came from the branch, not from the PR, which only changed tolerances.
  Always read the log lines that describe thread budgets and versions before attributing a speed-up.
- **Tolerance changes can change the work done.** In the original case the PR made PDLP run 2300 iterations instead of 10 because it
  had to meet a tighter tolerance. Its LP time went up (0.26 s to 0.46 s) while the end result went from "no solution" to a solution.
- **Presolve can dominate.** When presolve removes all integers, the LP stage is tiny and the total is dominated by reading,
  presolve and writing. Compare stages, not only totals.
- **Relaxed tolerances help solvers return a point.** SCIP needed `numerics/feastol = 1e-5` on the numerically hard model; say so
  in any table that includes it.
- **Few runs.** cuOPT is randomised and the other solvers were run once. One model on one machine says little about other problems.

## 3.4 A reporting checklist

- the cuOPT commit and `VERSION`, OR-Tools version, HiGHS and SCIP versions (they are printed in the logs);
- CPU, GPU, driver and CUDA version;
- the exact command and every non-default parameter, including the SCIP parameter;
- total time **and** stage times, with the estimated ones marked;
- for each solver: whether a usable solution was returned, plus the objective, the largest violation and the number of violated rows;
- how many runs each number is based on.
