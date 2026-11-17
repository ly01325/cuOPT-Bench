# 中文操作手册:编译 cuOPT 的 PR 分支,并与 OR-Tools(SCIP / HiGHS)做性能对比

适用对象:第一次接手的人。照做可以从一台装好 GPU 驱动的 Linux 机器出发,编译出 PR 版 `cuopt_cli`,在同一个模型上跑完 cuOPT、HiGHS、SCIP,并独立核对每个解。

英文版文档见 [../01-build-cuopt.md](../01-build-cuopt.md) 起的四篇;这里是浓缩的中文版,命令一致。示例 PR 是 [NVIDIA/cuopt PR 2338](https://github.com/NVIDIA/cuopt/pull/2338)(`Set correct MIP tolerances for reduced-to-LP problems`),换别的 PR 或模型,步骤相同。

---

## 0. 目标与产出

**背景(一句话):** 在一个大型排产 MIP 上,预处理把所有整数变量消掉,只剩纯 LP。cuOPT 26.10 把这个 LP 解对了,但最后输出「没有整数可行解」,解文件为空;PR 2338 把这条路径的容差改成 MIP 的设置后,cuOPT 输出了解。

| 产出 | 说明 |
|---|---|
| PR 版 `cuopt_cli` | 从 PR 分支编译 |
| 一张对比表 | 总耗时、预处理、LP/求解阶段、状态 |
| 每个解的独立复核 | 目标值、整数是否取整、约束最大违反与违反行数 |
| 一份日志包 | 所有 `.log`(不含大的 `.sol`) |

**不要做的事:** 不要擅自重载/重置 GPU 驱动、不要重启共享服务器、不要把业务模型上传到外部服务。这些要先问机器管理员或模型负责人。

---

## 1. 前置条件(只读命令)

```bash
nvidia-smi                       # 看 Driver Version 和右上角的 CUDA Version
nvidia-smi -L                    # 应列出所有预期的 GPU
nproc; free -g | head -2
df -h .                          # 编译环境约需 20-30 GB
curl -sI -m 8 https://github.com | head -1
```

- **编译所用的 CUDA 版本不能高于 `nvidia-smi` 右上角显示的版本。** 选高了,程序能启动但看不到 GPU,报 `cudaGetDeviceCount err=999`。
- GPU 数量正确,没有掉卡。
- 编译时机器应基本空闲;测性能时必须独占。

---

## 2. 一键编译

```bash
PR=2338 bash scripts/build_cuopt_pr.sh ~/cuopt_work
```

脚本会:拉取并切到 PR 分支、安装 micromamba、按驱动的 CUDA 版本建环境、只编译命令行需要的部分(约 10 分钟,224 线程机器)。结束时打印 `cuopt_cli` 路径和库目录(运行时设为 `LD_LIBRARY_PATH`)。

想手动执行或排错,见英文版 [01-build-cuopt.md](../01-build-cuopt.md)。要点:

1. PR 分支通常基于**开发版**,与发布版不是同一代码,后面比耗时时要考虑这一点;
2. 仓库自带的 conda 环境文件写死了 `cuda-version`,必须改成驱动支持的版本;
3. 编译参数 `./build.sh libcuopt --skip-tests-build --skip-routing-build --skip-grpc-build --skip-c-python-adapters`。

> 说明:`build_cuopt_pr.sh` 里的各条命令在真实机器上逐步执行过,但这个包装脚本是之后整理的,**没有完整端到端跑过**,首次使用请先在备用机器上试一遍。

---

## 3. 冒烟测试

```bash
python scripts/convert_lp_to_mps.py examples/tiny_schedule.lp tiny.mps
export LD_LIBRARY_PATH=~/cuopt_work/mm_root/envs/cuopt_build/lib
CUDA_VISIBLE_DEVICES=0 ~/cuopt_work/cuopt_src/cpp/build/cuopt_cli tiny.mps --time-limit 10 2>&1 | head -15
```

- 成功:日志里有 `CUDA 13.0, device: NVIDIA ... (ID 0), VRAM: ...`。
- 失败:`cuOpt selected CPU memory backend: no usable CUDA device (... err=999 ...)`。先看第 8 节,**不要继续往下做**。

---

## 4. 准备测试环境与模型

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install ortools highspy numpy
python scripts/convert_lp_to_mps.py my_model.lp my_model.mps     # cuopt_cli 读 MPS
```

所有求解器用同一个 MPS 文件。想要公开的测试集,可用 MIPLIB 2017(https://miplib.zib.de,先解压 `.mps.gz`)。

可选:再安装 26.10 发布版 `cuopt-cu13` 的 wheel 到另一个虚拟环境,用它的 `cuopt_cli` 作为对照组(`ORIG_CLI`),用来证明差异来自 PR 而不是环境。

---

## 5. 运行对比

**测量要求:**

- 每次只跑一个求解器,不要并行(它们都吃满 CPU,并行会互相拖慢)。
- 机器上没有其他任务:先 `uptime`、`nvidia-smi` 看一眼。
- cuOPT 有随机性,PR 版脚本里跑两次。
- 记录环境:CPU、GPU、驱动、CUDA 版本、cuOPT 提交号、OR-Tools 版本。

```bash
MODEL=my_model.mps \
PR_CLI=~/cuopt_work/cuopt_src/cpp/build/cuopt_cli \
PR_LIB=~/cuopt_work/mm_root/envs/cuopt_build/lib \
PY=$(which python) \
ORIG_CLI=/path/to/released/cuopt_cli \
bash scripts/run_compare.sh out_cmp
python scripts/summarize_logs.py out_cmp
```

长任务用 `nohup ... &`,看 `out_cmp/DONE` 判断是否结束。每个日志最后一行 `WALL <秒>` 是整个进程的墙钟时间。

| 日志 | 命令 |
|---|---|
| `cuopt_pr_1.log`、`cuopt_pr_2.log` | PR 版 `cuopt_cli`,默认限时 600 秒,单卡 |
| `cuopt_orig.log` | 发布版 `cuopt_cli`(设置了 `ORIG_CLI` 才有) |
| `highs.log` | 原生 highspy 跑 HiGHS |
| `scip.log` | OR-Tools 调 SCIP,`numerics/feastol = 1e-5`(可用 `SCIP_PARAM` 修改) |

**两个容易踩的坑:**

1. **SCIP 的参数只能传一个 `key = value`。** 多个参数写在一个字符串里会报 `INVALID_SOLVER_PARAMETERS`。
2. **不要把「HiGHS 经 OR-Tools」和「原生 HiGHS」混在一张表里。** OR-Tools 会对 HiGHS 的解做二次检查并可能改状态。选一条路径并写明。

---

## 6. 独立复核每个解

```bash
python scripts/verify_solution.py my_model.mps out_cmp/cuopt_pr_1.sol
python scripts/verify_solution.py my_model.mps out_cmp/scip.sol
```

在原始模型上重新计算:目标值、约束最大违反、违反超过 1e-6 的行数、变量界最大违反、整数变量偏离整数的最大值。解文件是「名字 值」的行,以 `#` 开头的头部行(cuopt_cli 解文件里有)会被忽略。

原生 HiGHS 脚本写出的是 HiGHS 自己的格式(`highs_native.sol`),`verify_solution.py` 读不了;HiGHS 的违反情况看它自己的日志。

---

## 7. 读结果,判断「成功」

**「成功」不要用求解器自己打印的状态。** 对所有求解器用同一把尺子:

1. 写出了非空的解文件(cuOPT 约 20 字节的解文件表示没有解);
2. 目标值与其他求解器一致;
3. 整数变量全部取整(偏离不超过 1e-6);
4. 约束最大违反**和违反的行数**在业务上可接受,两个都要报告。

目标值相同的两个解,违反方式可以完全不同:一个违反行少但幅度大,另一个违反行多但幅度小。哪种可接受,取决于这些行在业务上的含义。

**写报告时必须说清:**

1. **PR 版和发布版是不同的代码。** 示例中 PR 版预处理比发布版快很多,但日志里线程预算不同(`Papilo thread budget`),提速来自开发分支,而不是只改了容差的 PR。
2. **收紧容差会改变计算量。** 示例中 PR 让 PDLP 迭代 2300 次而不是 10 次,LP 时间从 0.26 秒变成 0.46 秒,结果却从「无解」变成「有解」。
3. **预处理可能占大头。** 整数被消光后 LP 阶段很小,总耗时被读入、预处理和写出主导,要比各阶段,不要只比总数。
4. **放宽容差能让求解器交出一个点。** 比如 SCIP 在数值很差的模型上需要 `numerics/feastol = 1e-5`,表里要注明。
5. **运行次数少、单个模型、单台机器**,结论不能外推。

通过相减得到的阶段耗时,报告里写「估算」。参考数据见 [../reference-results.md](../reference-results.md)。

---

## 8. 常见问题

| 症状 | 原因 | 处理 |
|---|---|---|
| 编译成功后 `no usable CUDA device (… err=999 …)` | 编译用的 CUDA 版本高于驱动支持的版本 | 对照 `nvidia-smi` 的 `CUDA Version` 与环境文件里的 `cuda-version`,不高于它重新编译 |
| 版本正确,`dmesg` 有 `Xid 143`、`RmInitAdapter failed`、`Cannot initialize GSP firmware RM` | 某块 GPU 固件起不来(硬件/固件故障) | 找管理员:通常要整机断电重启,否则换硬件。不要自己处理 |
| `strace` 显示打开 `/dev/nvidia-uvm` 返回 `EIO` | GPU 掉线后 UVM 内核模块进入坏状态 | 找管理员重载 `nvidia_uvm` 或重启 |
| `cudaGetDeviceCount err=101` 且 `/dev/nvidiaN` 返回 `ENODEV` | 有 GPU 掉出驱动,CUDA 枚举到它就停了,`CUDA_VISIBLE_DEVICES` 也没用 | 找管理员整机断电重启 |
| `echo <pci-id> > /sys/bus/pci/drivers/nvidia/bind` 卡死、杀不掉 | 驱动在坏卡上初始化挂住,进程保持不可中断状态直到重启 | **不要重新绑定初始化失败的 GPU** |
| 运行报找不到 `.so` | 没设置 `LD_LIBRARY_PATH` | `export LD_LIBRARY_PATH=<conda 环境>/lib` |
| SCIP 报 `INVALID_SOLVER_PARAMETERS` | 参数字符串里有多个 `key = value` | 只传一个 |
| HiGHS 先报 `Optimal` 随后 `Solve error` | HiGHS 对自己的点做二次检查后拒绝 | 模型缩放不好;看日志里违反的行数 |
| 两次 cuOPT 耗时差别很大 | 机器上有别的负载,或随机性 | 检查 `uptime`、`nvidia-smi`,多跑几次 |
| zsh 报 `no matches found: *.log` | 本地 shell 展开了通配符 | 远程命令用单引号 |
| `run_compare.sh` 里 `date: invalid option -- 'N'` | macOS 的 `date` | 在 Linux 上运行 |

**共享机器上不要做的事:** 重载或重置 GPU 驱动、解绑 PCI 设备、未经管理员同意重启;同时跑两个求解器并引用耗时;把模型上传到外部服务。

---

## 9. 交付前清单

- [ ] 记录了 `git log --oneline -1` 和 `VERSION`
- [ ] `nvidia-smi` 的 CUDA 版本不低于编译所用的 `cuda-version`,GPU 数量正确
- [ ] 冒烟测试出现 `CUDA ..., device: ...`
- [ ] 四个求解器的 `WALL` 都有,且是每次独占运行
- [ ] 每个有解的求解器都跑了 `verify_solution.py`,数值写进报告
- [ ] 报告里写明第 7 节的五点
- [ ] 日志(不含 `.sol`)已打包;业务模型未外传
