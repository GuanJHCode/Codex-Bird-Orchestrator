# 多 CLI 主流程交付

日期：2026-09-15。本记录为推送前的本地验收快照；未更新用户既有安装。

## 已跑通

在独立真实安装下，Claude Code 2.1.267（Haiku）和 AGY 1.2.3（Gemini 3.8 Flash Low）作为同一个 run 的两个任务，均完成：

`owner-bind → provider-probe → submit → 实际读取随机文件 → collect → 校验内容/产物哈希 → ACK → accept → summary`

调用控制入口经过安装内 `scripts/invoke.sh`。未设置 `ORCHESTRATOR_ENABLE_TEST_FAKE`；Provider 使用既有来源环境，没有登录、复制凭据、改写账号配置或替换用户 Provider Lock。

最终证据：[real-mainflow-07.json](real-mainflow-07.json)（第 06 轮也通过，第 07 轮复验最后的探测环境改动）。两个任务均 `completed`、`read_verified=true`、`ack_idempotent=true`、`accept_idempotent=true`；summary 为 completed=2、running=0、blocked=0，两个任务 active_segments=0。ACK 后另查状态仍为 `result_ready`，业务接受由后续 `accept` 独立完成。

随机值只放在工作区文件中，不放进提示词。输出中的全部随机值必须与输入一致，输入文件不得变化，同时核对产物大小及 SHA-256。允许 Provider 以 Markdown 包装或重复引用同一内容；不接受别的随机值、空结果或哈希不一致。

复现说明：[usage.md](usage.md)。本轮是脚本驱动的真实多 CLI 主流程验收，尚不是原生 Codex TUI 主脑经 Skill 自主派工的验收。

## 最小实现改动

- **进程身份**：先查询并登记 birth，再启动 `cmd.Wait()` 回收；避免短命子进程被回收后 `ps` 无法查询身份。新增 20 个真实短命子进程回归，旧实现首个 `/usr/bin/true` 即报 `process_birth_unknown`，修复后通过。未延长超时、放宽 unknown 或更改停止权限。
- **AGY Profile**：仅开放 reviewer，映射原生 `--mode plan`、`--model`、`--effort`，保留 macOS 写入隔离；implementer/session 继续拒绝。
- **能力探测**：`--help` 接收独立且有界的 stdout/stderr；版本探测仍只用 stdout。精确匹配完整选项，避免 `--model` 被当作支持 `--mode`。探测子进程与 Worker 一样设置 `AGY_CLI_DISABLE_AUTO_UPDATE=true`，不修改父环境。
- **AGY 解析**：允许非文本步骤缺失/为空的 `text_delta`，允许失败结果的空 response；成功/问题仍须有非空 response。[官方协议](https://antigravity.google/docs/cli/headless/)明确区分步骤状态与文本增量。
- **操作闭环**：扩展本机 CLI 测试覆盖 collect/ACK/accept 和重复决定；Skill 补上 ACK 必填的 `version: 1`。新增自动生成私有请求文件的真实验收脚本。

本轮源码文件列表见 [changed-files.json](../data/changed-files.json)，增量以本次提交与父提交的差异为准。本地保留相对本轮开始时工作区生成的补丁备份；该备份不随提交发布，既有未提交修改保持原样。

## 验证

Go 命令在 `tools/orchestrator` 执行，工具链为仓库既有 `tasks/g0-macos/data/go/bin/go`（Go 1.26.8）。

| 检查 | 结果 |
|---|---|
| `go test -count=1 ./...` | 14 个有测试的包通过；[最终日志](final-go-test-03.log) |
| `go test -race -count=1 ./...` | 14 包通过；[日志](final-go-race-02.log) |
| `go vet ./... && go build ./...` | 退出 0 |
| 原远端失败的三个测试，`-count=5` | 全部通过；[日志](ci-regressions.log) |
| 本机 CLI 的扩展 collect/ACK/accept 链路 | 通过；[日志](local-mainflow.log) |
| Python runtime/bridge/trial/Skill 打包矩阵 | 142 passed、2 skipped、1 既有 warning；[日志](final-python.log) |
| 真实打包、私有 install/doctor | 通过；[日志](install-03.log) |
| 打包执行位测试、`git diff --check` | 退出 0；执行位日志见 [final-package.log](final-package.log) |

Python 跳过的两个用例是 integrated-final-binary 与 native-auth-tripwire opt-in；warning 是既有 finally return。未将这些跳过项计为通过。

## 失败与定因记录

保留 `real-mainflow-01` 至 `05` 的失败证据：stderr help 未被读取；未安装二进制被 package pin 拒绝；过度要求模型逐字只回 token；ACK 缺少 version；AGY 泛化读取提示最终超时。前三次未形成双 Provider 完成证据；后续才修复验收脚本并通过正式安装完整验证。

AGY no-tools 探针在默认日志和 scratch 日志下均成功，长 scratch 也成功，因此没有把日志路径或路径长度当成根因、没有加入 `/dev/null` 日志参数。泛化读取探针选用 `run_command` 并失败，随后出现空 SUCCESS；显式 `view_file` 成功。最终主流程固定验证原生文件读取，**未宣称修复 AGY 任意终端工具的失败/超时**。探针日志见 `agy-*-probe.log`。

新增帮助探测测试在全套中重复触发 2s 超时，单跑 count5 通过。追加诊断显示，同一脚本由 `/bin/sh` 解释约 5ms，直接执行约 1.22s，首次直接启动超过 2s，见 [启动诊断](probe-launch-diagnostic.log)。测试改为复用已经运行的 Go 测试二进制，继续执行真实子进程/stdio，不修改生产 2s 期限。修改后完整 Go 与 race 均通过；此前失败日志仍保留。

原远端 `0469efd6` 的三个失败现象与本地短命子进程竞态一致，但未对远端三项逐一做旧版本稳定复现，不能声称已证明所有失败同根因。截至此验收快照，远端 run `34936854048` 为失败；后续提交的 CI 状态以对应 GitHub Actions 运行结果为准。

## 仍需后续处理

- Codex Worker：`codex_trial_guard_not_ready` 保留；认证保护及可信元数据接线未完成。
- Grok：当前 `grok models` 报告未认证，且新 Profile 仍拒绝；当前 help 与旧参数/流格式存在差异，未声称真实可用。
- AGY：只验收 reviewer/view_file；终端工具、编辑、session 续接均未开放或未验收。
- 真实 implementer、未提交修改冻结为候选提交、带反馈返工、独立代码审查与整合，仍按上一轮建议后续推进。

独立审查最终 **PASS**，见 [review.md](review.md)。

保留独立安装及真实运行状态/产物，以对应成功与中断任务的证据和恢复绑定；不删除 unknown 或恢复凭据来清空间。临时源码副本、测试 venv 和重复打包源已清除，记录见 [cleanup.json](cleanup.json)。
