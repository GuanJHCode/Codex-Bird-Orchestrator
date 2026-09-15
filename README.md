# Codex Bird Orchestrator

让一个现有 Agent CLI 负责目标、派工、验收和后续决策。协调器负责持久化与执行边界，Worker 负责有明确范围的任务。

```text
主脑：任务简报 → submit → wait-events / collect → 验证产物
                                              ├─ accept / reject
                                              ├─ answer
                                              └─ retry
```

收到结果、进程退出 0、delivery ACK 都不代表验收通过。主脑压缩上下文后，可以用 `summary` 从同一 SQLite 数据库恢复待处理、运行中、阻塞任务和允许动作。

## 实现与边界

- Go + SQLite、持久化 DAG、默认并发 2；支持全局、Provider 和工作区限制。
- spool 先落盘，协调器事务提交后 durable ACK；确认前保留记录，确认后归档，恢复仍能读取历史。
- owner 的 PID/birth 和控制能力绑定；通用本机 owner 可直接收集结果，Codex 原生回注是可选接入。
- 模型、思考、权限与超时使用类型化 Execution Profile；Provider Lock 固定协议、版本和二进制摘要。升级需要用户确认。
- reviewer 对工作区只读；implementer 必须使用授权的独立 Git worktree。Git 候选版本与审核绑定仍由既有 Git Host 流程处理。
- Worker 默认不能派工。owner 丢失、未知进程和恢复都保留原安全约束；`unknown` 未确认退出前继续占资源。

生产运行时目前面向 macOS。支持程度以 [支持矩阵](docs/support-matrix.md) 和实际验证记录为准。

## 开始使用

1. 按 [安装与运行演示](docs/installation.md) 构建、打包并安装到指定私有目录。
2. 主脑加载 [orchestrate Skill](plugins/codex-orchestrator/skills/orchestrate/SKILL.md)，建立 owner，冻结任务简报与 Provider Lock。
3. 使用 `submit → wait-events/collect → 验证 → accept/answer/retry` 闭环；保留控制文件路径和结果游标。

接口详见 [CLI README](tools/orchestrator/README.md)、[配置与恢复](docs/provider-runtime.md)、[运行协议](docs/runtime-protocols.md) 和 [Git 协议](docs/git-cleanup-protocol.md)。协议文档中的设计目标不等同于全部已实测能力。

## 开发与验证

Go 1.26+、Python 3。常用命令：

```sh
cd tools/orchestrator
go build ./...
go test -count=1 ./...
go test -race -count=1 ./...
go vet ./...
```

[分层测试说明](docs/testing.md) 区分单元/协议、多进程、真实 Provider 和原生 TUI 验收。[CI](.github/workflows/ci.yml) 不使用模型凭据；本地模型测试需显式 opt-in。

## 许可证与参考

项目许可证仍待维护者明确确认；未将候选许可证当成已授权许可。[参考项目与许可记录](docs/reference-projects.md) 列出已核实的版本、BSL 限制及借鉴范围。本轮采用设计思路，未复制参考项目的受限实现。
