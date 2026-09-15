# 第 3–5 项交付记录

日期：2026-09-15；macOS arm64 / Apple M3 Pro，Go 1.26.8，Python 3.14。修改留在当前工作区，未提交、未推送，也未替换用户现有安装或 Provider Lock。

## 结果与修改文件

| 范围 | 主要文件 | 解决的问题 |
|---|---|---|
| Provider | `tools/orchestrator/internal/adapter/{adapter,profile,protocol,lock,probe}.go`；`cmd/orchestrator/{main,provider}.go`，对应 tests | 启动/解析/恢复协议与类型化执行配置、二进制锁分离；拒绝任意参数、不支持的能力及未核实的 typed resume。探测实际 version/help，锁更新要求确认摘要。 |
| 执行边界 | `internal/host/{host,profile,report}.go`；`internal/process/{process,ancestry}.go`，对应 tests | reviewer 写入隔离、授权 implementer 限于 linked worktree；阻止访问控制凭据和其他 launch capability；执行前再次验证真实 Provider 二进制 pin。 |
| 通用主脑接入 | `cmd/orchestrator/local_owner.go`；`internal/{ipc/peer,coordinator/local_owner,coordinator/server,store/owner_grants,store/collection}.go`，对应 tests | owner 授权与返回方式分离；本机 owner、显式 rebind、持久化 collect receipt 与 durable ACK；ACK 不替代业务验收。 |
| 启动竞态 | `internal/store/owner_grants.go`、`owner_grants_test.go`；`internal/coordinator/{server,local_owner_test}.go` | 真实进程复现 Host 丢失后 orphan Worker 在身份未落库时注册主脑；逐 segment 暂缓新 owner/native submit，未绑定 peer 不能借恢复/验收入口派工。 |
| 正式运行时 | `runtime/native/*.py`（11 个实现）；原 `tasks/g0-*` 路径兼容入口；`tasks/g1-g4-delivery/scripts/package-plugin.sh`；`tools/native-product-bridge/test_local_service_chain.py` | 生产 Python 移出实验目录；打包从正式 runtime 取源，安装目录保留 `runtime/g0`。保留独立 shim 的原导入行为，修复迁移时发现的 native probe 回归。 |
| 调度、存储、性能 | `internal/store/{limits,migrations,storage_migration,quota,scheduling,reports,host_events}.go`；`internal/coordinator/limits.go`；`internal/events/{events,incremental_test}.go`，对应 tests | 默认并发 2，Provider/工作区限额，unknown 保留资源；spool 增量读取与确认后归档；SQLite 事务额度计数，artifact 有界读取并计费。 |
| store 拆分 | `internal/store/runtime.go` 及新增 `admission.go`、`decisions.go`、`delivery.go`、`hash.go`、`lifecycle.go`、`owner.go`、`snapshot.go`、`schema.go` 等 | 沿既有职责拆文件，保留同一 SQLite 状态系统；版本化、可回滚迁移代替每次打开时散布 DDL。 |
| 操作与维护 | 根 `README.md`；`docs/{provider-runtime,installation,support-matrix,testing,reference-projects}.md`；`runtime/native/README.md`；`tools/orchestrator/README.md`；插件 `scripts/invoke.sh` 和 `skills/orchestrate/SKILL.md`；`.github/workflows/ci.yml` | 主脑闭环、上下文恢复、通用/原生模式一致的操作契约，安装演示、支持矩阵、分层 CI。 |

相对较早轮次的结果完整性、summary 和 skills 打包检查保留，详见 [前轮交付](../../brain-control-hardening/docs/round-1.md)。没有重写 Go/SQLite、DAG、spool+durable ACK 或 Git 候选/审核绑定；没有引入第二套数据库或消息投递系统。

## 实际验证

本轮先跑基线，再制定 [实施计划](../plans/implementation.md)：Go 14 个有测试的包通过，Python 140 passed / 2 skipped。下表是最后相关改动后的验证；`contract` 无测试文件，不计入 14 包。

以下 Go 命令在 `tools/orchestrator` 执行，本机 `go` 路径为 `../../tasks/g0-macos/data/go/bin/go`；Python 使用本任务临时 venv。

| 命令 / 验证 | 实际结果与证据 |
|---|---|
| `go test -count=1 ./...` | 最终 14 包通过：[日志](final-go-tests.log)。 |
| `go test -race -count=1 ./...` | 14 包通过：[日志](final-go-race.log)。 |
| `go build -o ../../tasks/provider-runtime-completion/tmp/codex-orchestrator ./cmd/orchestrator`；`go vet ./...` | 均退出 0。 |
| `go test -count=1 ./...`，分别在 `tools/g0-probe`、`tools/g0-return-lab` | 均实际运行并通过（probe 11.1s、hook 3.0s；return-lab 35.3s）。 |
| `python -m pytest -p no:cacheprovider tools/native-product-bridge tools/real-user-trial tasks/brain-control-hardening/scripts/test_package_skills.py tasks/provider-runtime-completion/scripts/test_runtime_layout.py -q -rs` | 142 passed，2 skipped，1 原有 warning：[日志](final-python.log)。跳过的是需显式最终二进制/原生 auth tripwire 的测试；warning 来自原 `native_product_case.py` 的 finally return。 |
| `go test -count=1 ./internal/store ./internal/coordinator` | owner gate、真实 socket 授权、artifact/额度/collection 等通过：[日志](owner-gate-green.log)。回归先失败的证据：[owner](owner-gate-red.log)、[native submit](native-enrollment-red.log)、[dispatch peer](dispatch-peer-red.log)。 |
| `ORCHESTRATOR_REAL_CLAUDE=1 go test -count=1 ./cmd/orchestrator -run TestRealClaudeReviewerProfile -v` | **真实 Claude Code 2.1.267 模型请求**在 reviewer sandbox 下返回预期标记：[日志](real-claude-final.log)。不是 mock 结论。 |
| `python tasks/provider-runtime-completion/scripts/verify_install.py <built-binary> <private-test-root>` | 真实打包、install、doctor 成功；11 个正式 runtime 文件：[日志](install-check.log)。 |
| `G4_TEST_PYTHON=<resolved-python> sh tasks/g1-g4-delivery/scripts/test-package-executable-modes.sh` | 退出 0。该脚本用 shell fixture binary 验证打包执行位；真实 Go 二进制安装另见上一行。 |
| Skill `quick_validate.py`；CI YAML 解析；两个改动 shell 入口 `sh -n`；`git diff --check` | 均通过；没有在 GitHub runner 实际执行 CI。 |

### 失败与复查，未隐藏为绿色结论

- 一次全套 Go 运行中，本机 CLI 测试等待结果超过其 20 秒 deadline，随后状态调用失败；日志为空，不能据此归因。保留 [失败记录](go-status-timeout.log)。同一源码该测试 `-count=5` 全通过（[记录](local-cli-recheck.log)），随后全套及 race 通过。**超时根因尚未确认，未声称修复此偶发问题，也未放宽超时或安全检查。**
- 扩展的历史实验 Python 测试首轮 **382 passed / 57 failed**：[记录](historical-runtime-tests.log)。其中 3 个 cold-start native probe 失败是本次 shim 导入路径回归，已修复并重跑相关 6 项通过：[记录](native-probe-migration-green.log)。未重跑整个扩展矩阵，不声称 57 项全部解决。
- 历史失败还涉及缺少固定 `main-verify` 二进制、websockets 依赖、原安全解释器 pin，以及旧用例行为/超时。只对部分做了 HEAD 归档对照：[基线比较](historical-baseline-comparison.log)、[deep JSON 同样失败](deep-json-baseline.log)；不能把全部失败一概归为旧问题。
- 真实 Claude resume 试验第二段 exit 1，得到 `process_tree_unknown`：[记录](real-claude-resume.log)。原因未确认；新 profile 当前明确拒绝 resume，保留旧协议兼容路径，没有静默降级。
- Host-kill/orphan 的复现属于**真实 macOS 进程 + fake Provider**，不能替代真实模型联调。修复后两轮仅命中已持久化身份的拒绝路径，没有再次命中缺失身份窗口；不能当作新增 gate 的真实时序验收。源码审查与回归测试通过。证据见 [独立复核](orphan-owner-reproduction.md)。

独立运行时边界审查结论：**PASS，无阻塞项**。审查覆盖 provider、owner/IPC、Host sandbox、spool、quota 与迁移；保留精确时序复验未命中的限制，不将静态复核当作端到端命中证据。

## 性能测量

先记录基线再优化，命令为 `go test -run '^$' -bench BenchmarkPendingSpool -benchmem -count=3 ./internal/events` 和对应 store 的 `BenchmarkQuotaAdmission`（使用短 benchtime）。仅代表固定输入下本机测量：

| 场景 | 修改前 | 修改后 |
|---|---|---|
| spool 共 1000 条、990 条已 ACK，仅取待处理记录 | 29–31 ms/op；约 2.78 MB、16033 次分配 | 0.25–0.27 ms/op；约 27 KB、188 次分配 |
| 5000 条已存事件下额度准入查询 | 7.8–9.4 ms/op | 23–30 μs/op |

原始证据：[spool 前](spool-before.log) / [后](spool-after.log)，[quota 前](quota-before.log) / [后](quota-after.log)。没有实际运行 20 分钟洪峰/SLO 验收，不能将这些数字外推成端到端保证。

## 兼容影响

- SQLite 迁移到 **schema v5**，DDL/回填/version 在同一事务中；旧二进制拒绝较新 schema。需要回退时使用升级前备份，不能直接对已升级库降级运行。
- 新 typed profile 只开放已核验的 Claude 启动能力；Codex 生产 guard 继续拒绝，AGY/Grok 新 profile 拒绝。旧参数/协议路径保留，但不会自动获得新 profile 的角色隔离保障。
- reviewer 是**写入隔离**，保留既有 Provider 读取/认证环境，不是全系统文件读取白名单。implementer 需授权 linked worktree，仍保留 Provider 原生审批，不使用 bypass/acceptEdits 解决兼容。
- 执行前重验原 Provider pin；最后一次哈希与内核按路径执行之间仍受既有同 UID 文件修改威胁边界限制，未宣称原子执行锁定。
- 运行时凭据目录保持 0700、文件 0600。新 profile 的 report artifacts 使用独立子目录。单个结果 artifact 上限 1 MiB；额度涵盖提交记录和登记 artifact 的 bytes，不能阻止 Provider 在提交前写任意未登记大文件，不是 OS 文件系统配额。
- owner 身份与 return transport 分开。本机收集 proof 不能代替 native history proof；ACK 不会把 `result_ready` 变成验收通过。
- 任一 active/unknown segment 无持久 PID/birth 时，新 owner 注册与 native submit 暂缓；恢复/验收入口需已有主脑祖先身份。已有 local owner 可继续提交，查询/停止仍可用。owner 同时丢失时，须先进程对账再登记/rebind；不通过清除 unknown 解锁。
- 并发默认仍为 2；配置下次协调器启动生效；unknown 计入所有资源限制。旧 Python 源路径是兼容 shim，安装包中的 `runtime/g0` 路径保留。

## 参考、许可证与未完成项

参考项目当前版本/许可已核实：[记录](../../../docs/reference-projects.md)。backnotprop/orchestrator 当前为 BSL 1.1（禁止向第三方提供商业托管/受管 agent orchestration 服务，不是已生效 Apache）；Agent Mail 有额外 rider；未复制受限实现。

尚待明确处理：

1. **项目许可证待用户选择**。Apache-2.0 候选文本已准备，未写入根 LICENSE；待回答问题不是运行异常。
2. 真实 implementer 编辑、Codex 原生 TUI 回注、AGY/Grok 模型联调未运行；Codex 生产启动与新 typed resume 仍按支持矩阵拒绝。
3. 历史实验矩阵的剩余失败、一次 CLI 偶发等待超时和真实 Claude resume 失败尚未全部定因；新增 owner gate 的精确竞态窗口未完成修复后真实时序验收。
4. GitHub Actions 尚未远程执行；未执行长时洪峰/SLO；未对用户安装做升级、发布或提交。

清理仅涉及本轮临时 venv、基线归档、独立测试安装和生成缓存；保留本目录报告、回归脚本、候选许可证，以及归属不明/用户原有文件。
