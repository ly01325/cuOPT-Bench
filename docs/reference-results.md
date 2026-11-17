# Reference results from the original case

One data point to check your own setup against. The model is a confidential business scheduling MIP and is not included, so you
cannot reproduce these numbers exactly; use them to see whether your run behaves the same way.

## The model, described without the data

- A large scheduling MIP (binary and general-integer variables, continuous flows), maximising a weighted sum of fulfilled demand.
- It contains Big-M constants (1e9) and a very wide coefficient range (largest about 1.7e10); cuOPT warns about the coefficient range.
- Presolve in cuOPT (Papilo), SCIP and HiGHS removes **all** integer variables, so what remains is a pure LP. The LP relaxation value
  therefore equals the MIP optimum.

## Environment

| Item | Value |
|---|---|
| CPU | 2 x AMD EPYC 9575F (112 cores / 224 threads), 2.2 TB RAM |
| GPU | NVIDIA RTX 6000D, 83 GiB, one GPU used for cuOPT |
| Driver / CUDA | 580.95.05 / CUDA 13.0 (the PR build was compiled with `cuda-version=13.0`) |
| cuOPT | released 26.10.0, and a build of PR 2338 (commit 700828b, development branch 26.12) |
| OR-Tools / HiGHS / SCIP | OR-Tools 9.15; HiGHS 1.15 (native run); SCIP through OR-Tools |

## What the PR changes

When presolve leaves a pure LP, cuOPT solves it with the concurrent LP solvers and returns the result without mapping it back through the
usual MIP checks. Before the PR that LP used default LP tolerances. The PR sets the primal tolerances to the MIP settings and turns on
per-constraint residuals:

```diff
+ settings.per_constraint_residual = true;
+ settings.tolerances.absolute_primal_tolerance = context.settings.tolerances.absolute_tolerance;
+ settings.tolerances.relative_primal_tolerance = context.settings.tolerances.relative_tolerance;
```

Effect on this model:

| | released 26.10 | PR 2338 build |
|---|---|---|
| PDLP iterations | 10 | 2300 |
| absolute primal residual of the LP | 8.95e3 | 2.6e-7 |
| LP stage | 0.26 s | 0.46 s |
| result | `Problem has no integer feasible solution.`, solution file of 21 bytes | solution written |

## Timings (one solver at a time, idle machine)

| solver | total (s) | presolve (s) | LP / solve (s) | status as printed |
|---|---:|---:|---:|---|
| cuOPT, PR build, run 1 | 33.0 | 11.0 | 0.46 | solution written; post-solve warning |
| cuOPT, PR build, run 2 | 32.9 | 10.7 | 0.47 | solution written; post-solve warning |
| cuOPT, released 26.10 | 98.3 | 74.8 | 0.26 | no solution |
| HiGHS (native) | 116.9 | 91.3 | 16.7 | `Solve error`, no primal solution |
| SCIP via OR-Tools, `numerics/feastol = 1e-5` | 310.2 | 53.2 | about 238 | OPTIMAL |

The SCIP solve time is `Solving Time` minus presolve, an estimate.

## Solution quality (independent check on the original model)

| | cuOPT, PR build | SCIP, feastol 1e-5 | HiGHS |
|---|---|---|---|
| objective | 300289200.000000 | 300289199.999997 | no usable solution |
| integer variables, largest distance from an integer | 0 | 0 | |
| bound violation, largest | 1.4e-14 | 4.8e-7 | |
| row violation, largest (absolute) | 7.3e-4 | 1.3e-5 | |
| rows violated by more than 1e-6 | 4 | 2927 | |

Both solutions reach the common LP optimum; they are different solutions (different numbers of nonzero variables). The cuOPT solution
violates few rows by a larger amount, the SCIP solution many rows by a small amount; the violated rows carry coefficients up to 1e10.
Which is acceptable depends on the application.

## Caveats

- The PR build presolved much faster than the released build (about 9 s against 73 s for Papilo). The logs show a different thread budget
  (16 against 219 CPU feasibility-jump threads), so this comes from the development branch, not from the PR.
- Single model, one machine. cuOPT was run twice with the PR build; the other solvers once.
- Whether the "no solution" symptom and the problem described in the PR are the same code path was not confirmed by reading the source; the
  behaviour on this model is consistent with it.
