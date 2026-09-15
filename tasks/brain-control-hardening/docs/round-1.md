# 第一轮交付：结果完整性与主脑入口

## 结论与边界

已完成本轮优先级 1、2 的实现与验证。优先级 3–5 仍未实现，完整目标未完成；后续从 Provider 配置开始，详见 [实施计划](../plans/implementation.md)。没有提交、推送或修改已安装插件。用户已有修改与未跟踪产物保留。

本地基准 `8f6ee011`；GitHub 发布基准 `be76b0b2`。相关生产源码相同，但发布快照缺本地已有 Skill、README 和 Codex fixture；后续发布必须一并包含。详见 [参考与版本核验](references.md)。

## 已复现并修复

1. **超长最终结果回退旧草稿**：修复前 12 个用例都返回 `old draft` 且无错误。覆盖每次 1、127、4096、65536 字节写入、JSON 字段重排和 Unicode 转义 type。现在超长 Codex 结构化记录明确失败；不输出旧草稿。Host 写入受控 artifact：`{"status":"incomplete","reason":"provider_critical_event_too_large"}`，并生成 failed 事件进入既有 spool/durable ACK 路径。
2. **晚安装 session observer 的错误分类**：快速输出的解析错误原先会阻止合法会话回调，Host 把它当成持久化失败进入 unknown。现区分解析错误与 observer 持久化错误；前者交给 Finish 的失败结果路径，后者仍保持安全失败。
3. **主脑操作入口**：已有 Skill 补任务目标、输入、文件/工作区范围、权限约束、产物及验收条件，明确 Worker 不递归派工；使用等待事件、持久化结果与 owner 验收闭环，不将 delivery ACK 当验收。
4. **运行摘要**：新增 `summary --task-id <run中任一任务> --control-file <原始回执路径>`。直接读取同一 SQLite 中经 owner 授权 run 的任务状态、分组计数、work revision、active segment 数及保守的状态允许动作。读取不派工、不恢复，不返回 prompt/token/整段日志；命令仍校验事件/问题绑定，resume 仍需显式恢复授权。
5. **打包校验**：拒绝缺失或空 skills、越界声明、目录/文件 symlink，验证包清单包含 Skill。

## 复核后跳过的推测

- 本地 Skill 已存在，未重建目录；远端缺失单独记录。
- ExtraArgs 已明确拒绝，binary pin 校验已存在，未重复实现。
- 空 Codex message 已被解析器拒绝（`event_text_invalid`），无旧草稿回退；只保留边界测试。
- unknown 已占用 active 配额；新增摘要测试确认不提示 resume，状态机也拒绝恢复。
- Worker report failure 单独到达不等于 Host 确认失败。探针发现这种情况下 QueueRetry 本就返回 conflict，因此未按静态推测扩展摘要权限；保留对应特征测试。

## 修改文件

生产代码及使用文档：

- `tools/orchestrator/internal/host/protocol.go`：超长记录策略、observer 错误分类。
- `tools/orchestrator/internal/host/host.go`：不完整结果的受控失败 artifact。
- `tools/orchestrator/internal/store/summary.go`（新增）：owner 范围的持久化运行摘要。
- `tools/orchestrator/internal/coordinator/server.go`：summary 控制请求。
- `tools/orchestrator/internal/ipc/ipc.go`：新增 summary 消息种类，协议版本仍为 1。
- `tools/orchestrator/cmd/orchestrator/main.go`：CLI 入口。
- `plugins/codex-orchestrator/scripts/invoke.sh`：允许 summary。
- `plugins/codex-orchestrator/skills/orchestrate/SKILL.md`：任务/验收/恢复契约。
- `tasks/g1-g4-delivery/scripts/package-plugin.sh`：Skill 完整性校验。
- `tools/orchestrator/README.md`：命令与兼容边界。

测试：

- `tools/orchestrator/internal/host/{protocol_test.go,host_test.go}`。
- `tools/orchestrator/internal/ipc/ipc_test.go`。
- `tools/orchestrator/internal/coordinator/summary_test.go`（新增）。
- `tools/orchestrator/internal/store/{runtime_test.go,summary_test.go}`（后者新增）。
- `tools/orchestrator/cmd/orchestrator/main_test.go`。
- `tasks/brain-control-hardening/scripts/test_package_skills.py`（新增）。

计划、参考 SHA/许可证 hash、回归 red/green 与最终测试记录保存在本任务目录。

## 实际验证

Go 命令均在 `tools/orchestrator` 下，以 `../../tasks/g0-macos/data/go/bin/go`（1.26.8）执行。表中用 `go` 简写该绝对可复现工具链。

| 命令 | 实际结果 / 证据 |
| --- | --- |
| 基线 `go test -count=1 ./...` | 14 个有测试包全部通过，contract 无测试；先于计划及实现执行。 |
| 基线 Python bridge + trial | 134 passed、2 skipped、1 warning，[日志](baseline-python.log)。默认 Python 无 pytest，使用任务临时 venv。 |
| 超长结果聚焦回归 | 修复前 12 用例失败，修复后通过：[red](result-integrity-red.log)、[green](result-integrity-green.log)。 |
| observer 聚焦回归 | 修复前两个用例均未调用 observer：[red](observer-red.log)；修复后 host 聚焦组通过：[green](result-incomplete-green.log)。 |
| 最终 `go test -count=1 ./...` | 全部 14 个有测试包通过，[日志](final-go-test.log)。包含构建并运行真实 orchestrator/coordinator/source-host 的多进程 CLI 测试；Provider 是测试夹具。 |
| `go test -race -count=1 ./internal/host ./internal/adapter ./internal/ipc` | 3 包通过，[日志](protocol-race.log)。 |
| `go test -race -count=1 ./internal/store ./internal/coordinator` | 2 包通过，[日志](summary-race.log)。 |
| `go build ./...`、`go vet ./...` | 均 exit 0。 |
| `python -m pytest -p no:cacheprovider tools/native-product-bridge tools/real-user-trial tasks/brain-control-hardening/scripts/test_package_skills.py -q -rs` | pytest 9.1.1，140 passed、2 skipped、1 warning，[日志](final-python.log)。 |
| `sh tasks/g1-g4-delivery/scripts/test-package-executable-modes.sh` | 以已解析的 Python 3.14 可执行文件设置 G4_TEST_PYTHON，exit 0，[日志](package-modes.log)。 |
| skill-creator `quick_validate.py plugins/codex-orchestrator/skills/orchestrate` | `Skill is valid!`，只证明结构，不证明主脑行为。 |
| `git diff --check` | 无错误。 |

Python 跳过项：`test_local_product_driver.py:89` 需要集成后的最终 G1 二进制；`test_native_auth_tripwire.py:1337` 需要固定二进制 native opt-in。现存 warning 来自 `native_product_case.py:1348` 的 finally 中 return，未修改。

**没有运行真实 Provider 模型请求、Codex 原生 TUI 回注或安装后端到端验收。** 不以 mock/fixture 通过替代这些结论。独立只读审查结论 PASS，无阻断项；审查复跑了 host/store/coordinator/ipc/CLI 聚焦组及 6 个打包测试。

## 兼容影响与剩余工作

- 单条 Codex JSONL 超过 64 KiB 现在失败，包括无法安全分类的超长结构化诊断；普通原始诊断仍可丢弃。没有提高内存/事件额度，没有保存大段原始日志。
- summary 是新增命令，旧二进制不支持；数据库无需迁移，现有控制与业务命令约束不变。allowed_actions 是保守的状态提示，不是新权限，也不能替代新鲜事件绑定。
- 保留 Go + SQLite、DAG、spool + durable ACK、owner、显式恢复及 Git 候选版本/审核机制。
- 第 3 项：Adapter/Execution Profile/Provider Lock 拆分、类型化模型/思考/权限/超时、能力检测、reviewer/implementer 与升级确认尚未实现。
- 第 4 项：通用 owner 授权与 native 返回方式解耦、正式 runtime 迁移尚未实现。
- 第 5 项：Provider/工作区并发限制、spool/额度基准及优化、DB 迁移、runtime.go 拆分、完整安装演示/支持矩阵/CI 尚未实现；许可证等待用户明确选择。

## 临时文件清理

清理对象仅为 `tasks/brain-control-hardening/tmp/venv/`（本轮创建的 pytest/PyYAML 环境）及空 tmp 目录。交付代码、测试、计划、报告、参考元数据与验证日志保留；用户原有文件和旧临时目录未删除。
