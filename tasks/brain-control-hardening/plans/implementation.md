# 主脑编排增量完善

基准：2026-09-15，`8f6ee011`，保留用户原有修改。

## 基线（先于计划和实现）

- `tools/orchestrator`：仓库工具链 Go 1.26.8，`go test -count=1 ./...`，全部 14 个有测试的包通过，contract 无测试。
- 默认 PATH 无 Go，默认 Python 无 pytest；使用 `tasks/g0-macos/data/go/bin/go` 与本任务临时 venv（pytest 9.1.1）。
- Python bridge + trial：134 passed、2 skipped、1 现有 SyntaxWarning；详见 `../docs/baseline-python.log`。未运行真实模型或 native TUI 验收。

## 复核与顺序

1. **结果完整性（本轮已实现）**：12 个回归用例确认超长 Codex message 会丢失并返回旧草稿；现已显式失败，并通过 Host/spool 写入受控 incomplete artifact。补充分片、EOF、会话顺序、0.154.0 夹具、IPC 版本拒绝测试。另修复晚安装 session observer 时解析错误被误判为 observer 持久化失败的时序问题。空 message 原已被解析器拒绝，跳过改实现。
2. **主脑入口（本轮已实现）**：本地 manifest 声明的 `skills/orchestrate/SKILL.md` 已存在，但 GitHub 发布缺该文件，差异见核验文档。打包现拒绝缺失/不安全 skills 路径；完善任务契约、验收及等待事件闭环。新增 owner 授权的 `summary`，直接从同一 SQLite 读取状态，不另建任务状态；重启恢复、跨 owner 拒绝、动作前置状态、unknown 占资源及真实 orchestrator 多进程入口已测。
3. **Provider**：`ExtraArgs` 已拒绝，pin 已校验；跳过重复修复。模型/思考参数硬编码，Permission.Mode 是字符串，需拆协议、类型化 Execution Profile 和 Provider Lock。能力未通过检测不得扩大权限；implementer 隔离工作区授权独立验收。
4. **接入边界**：现有 Skill 的 submit 依赖 native bridge，打包直接引用 11 个 tasks/g0 Python 文件。先理清 owner proof / delivery proof 调用链与打包依赖再改；保留显式 rebind、权限与 Python。
5. **维护性能**：当前 ClaimReady 默认/上限 2，unknown 被计入 active；跳过直接释放资源这一推测。后续增加全局/Provider/工作区限制、先测 spool/额度计数基准再优化、版本化迁移及 runtime.go 职责拆分；补安装/矩阵/分层 CI。许可证选择待用户明确确认，不擅自添加许可证。

每个小步先复现或建立行为测试，再实现、验证并记录；以上静态观察不代表真实 CLI 缺陷已确认。保留 Go + SQLite、DAG、durable ACK、owner、显式恢复、Git 候选版本审核绑定。

第 3–5 项仍为后续增量，不能用本轮的单元/集成通过声明这些架构工作已经完成。本轮不迁移生产 runtime、不开放 implementer 权限、不更新 provider pin、不选许可证。
