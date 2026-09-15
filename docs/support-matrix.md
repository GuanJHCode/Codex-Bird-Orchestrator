# 支持矩阵

核验环境：2026-09-15，macOS arm64 / Apple M3 Pro、Go 1.26.8、Python 3.14。结论只覆盖注明的层次。

| 功能 | 状态与证据 | 边界 |
|---|---|---|
| Go 调度、SQLite、DAG、summary | 自动化测试 | 无第二套任务数据库或队列 |
| 本机 owner / collect / ACK / accept | 真实安装 wrapper 下 Claude + AGY 同 run 完整链路；ACK 与 accept 重放幂等 | 主脑控制由验收脚本执行；未验收原生 TUI 主脑自动派工 |
| reviewer 写入隔离 | 实际 macOS sandbox + shell/Git 测试 | 限制文件写入；保留既有 Provider 读取/认证环境，并非全系统读取白名单 |
| Claude Code 2.1.267 reviewer | 真实 Haiku 读取随机文件、产物哈希、收集与验收通过 | 仅覆盖小型读取任务；不是复杂代码审查验收 |
| implementer | 类型化授权 + linked worktree + 实际 OS 写入边界测试 | 保留 Provider 原生审批；尚未验证真实模型编辑任务 |
| 新 profile 的 session resume | **拒绝** `profile_resume_not_verified` | 实际 Claude 续接试验得到 exit 1 / `process_tree_unknown`，未声称可用 |
| Claude 旧 stream-json 协议 | 解析/会话/恢复 fixture 与 CLI 框架测试 | 旧配置不自动获得新角色隔离能力 |
| Codex 0.154.0 协议 | 版本 fixture、结果完整性测试 | 生产 guard 保留；新 profile 和真实任务启动仍拒绝 |
| AGY 1.2.3 reviewer | 新 Profile；真实 Gemini 3.8 Flash Low 使用 `view_file` 读取随机文件并完成收集与验收 | 未开放 implementer/session；泛化任务选用 `run_command` 的路径出现失败/超时，尚未定因 |
| AGY / Grok 旧协议 | 固定参数、解析与 session fixture | 不代表新角色隔离或真实续接可用 |
| Grok 1.0.30 | 当前本机 `grok models` 报告未认证；新 Profile 仍拒绝 | help 与旧适配参数存在差异，真实执行尚未验收 |
| 原生 Codex 回注 | 既有 Python 接入、owner 和 history proof 保留 | 本轮没有真实 Codex TUI 回注验收；通用调度不依赖它 |
| Python 正式 runtime | 独立导入、包装路径和真实本机 service fixture 测试 | 安装目录仍用 `runtime/g0`，以兼容既有 pin |
| 全局 / Provider / 工作区并发限制 | SQLite 调度测试 | 默认 2，unknown 保留资源；配置下次协调器启动生效 |
| spool / quota 性能 | 固定事件量的本机基准 | 不代表 20 分钟日志洪峰、端到端延迟或内存 SLO |
| 安装 | 真实构建二进制、打包、私有目录 install/doctor | 没有修改用户现有插件安装或 Provider 锁 |
| GitHub Actions | `0469efd6` 的 run `34936854048` 已失败 | 普通 Go 测试失败，后续 race/vet/Python 未执行；本轮本地改动未推送，不能称远端已修复 |
| Linux / Windows 生产执行 | 未支持 | native process / sandbox / peer 身份边界明确拒绝 |

最新主流程证据见 [多 CLI 验收](../tasks/multi-cli-mainflow/docs/real-mainflow-07.json)，此前完整记录见 [运行时交付](../tasks/provider-runtime-completion/docs/delivery.md)。绿色 fixture 测试不提升矩阵中未完成的真实验收项。
