# 4. Troubleshooting

| Symptom | Likely cause | What to do |
|---|---|---|
| `no usable CUDA device (... err=999 ...)` right after a successful build | the build used a CUDA version higher than the driver supports | compare `nvidia-smi`'s `CUDA Version` with the `cuda-version` in your environment file; rebuild with a version that is not higher |
| the same error with a correct version, and `dmesg` shows `Xid 143`, `RmInitAdapter failed`, `Cannot initialize GSP firmware RM` | a GPU's firmware does not start (hardware or firmware fault) | needs the machine's administrator: usually a full power cycle, otherwise a hardware replacement. Do not try to fix it from the benchmark |
| the same error and `strace` shows `open("/dev/nvidia-uvm") = -1 EIO` | the UVM kernel module is in a bad state after a GPU dropped out | needs the administrator: reload `nvidia_uvm` or reboot. In the original case this happened once and a reload moved the failure on to the next fault |
| `cudaGetDeviceCount err=101 (invalid device ordinal)` and `open("/dev/nvidiaN") = -1 ENODEV` | a GPU has fallen out of the driver; CUDA enumerates devices and stops at the missing one, so `CUDA_VISIBLE_DEVICES` does not help | administrator: power cycle |
| `echo <pci-id> > /sys/bus/pci/drivers/nvidia/bind` hangs and cannot be killed | the driver hangs initialising a dead GPU; the process stays in uninterruptible sleep until reboot | **do not re-bind a GPU that failed to initialise** |
| `cuopt_cli: error while loading shared libraries` | `LD_LIBRARY_PATH` not set | `export LD_LIBRARY_PATH=<conda env>/lib` |
| SCIP: `INVALID_SOLVER_PARAMETERS` | more than one `key = value` in the parameter string | give exactly one |
| HiGHS says `Optimal` but then `Solve error`, or reports violated rows | HiGHS re-checks its own point against the original model and rejects it; numerically hard models do this | the model needs better scaling, or a different tolerance; HiGHS's own summary in the log shows how many rows are violated |
| two cuOPT runs differ a lot in time | other load on the machine, or randomness | check `uptime` / `nvidia-smi`, repeat |
| zsh: `no matches found: *.log` over `ssh` | the local shell expands the glob | put the remote command in single quotes |
| `date: invalid option -- 'N'` in `run_compare.sh` | macOS `date` | run the scripts on Linux |

## Things not to do on a shared machine

- Reload or reset GPU drivers, unbind PCI devices, or reboot without the administrator's agreement.
- Run two solvers at the same time and quote the times.
- Upload the model to an external service. Business models are often confidential; share only what you are allowed to.
