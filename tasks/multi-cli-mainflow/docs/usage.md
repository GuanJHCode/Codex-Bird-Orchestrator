# 多 CLI 主流程验收入口

本入口会实际调用已登录的 Claude 和 AGY，使用 Haiku / Gemini 3.8 Flash Low，可能消耗模型额度。无需人工编写派工、ACK 或验收 JSON。

本轮已验证：同一个 run 中两个真实 CLI 读取任务专属随机文件，经正式 `invoke.sh` 完成 `owner-bind → provider-probe → submit → collect → ACK → accept → summary`。脚本分别校验文件内容与产物 SHA-256、ACK 不等于业务接受、重复 ACK/accept 幂等。

## 使用本轮保留的独立安装

在仓库根目录运行，每次只运行一份此验收脚本：

```sh
python3 tasks/multi-cli-mainflow/scripts/run_mainflow.py \
  --binary tasks/multi-cli-mainflow/tmp/install-03/installed/versions/0.2.0-runtime-check/bin/codex-orchestrator \
  --provider claude-code --provider antigravity-cli \
  --evidence tasks/multi-cli-mainflow/docs/replay.json
```

每次生成独立的 0700 `/private/tmp/multi-cli-flow-*` 运行目录，请求文件为 0600、消费后删除。终端打印每个任务的状态和证据路径；只有两个任务都完成内容核验及业务接受，脚本才退出 0。Provider 输出可以带说明或重复引用，但其中所有 `READ_OK_...` 值必须等于文件中唯一的随机值。

## 从源码重建

需要 Go 1.26+、Python 3，以及已安装并登录的 Claude / AGY。以下 `replay-install` 必须是尚不存在的目录：

```sh
mkdir -p tasks/multi-cli-mainflow/tmp
go -C tools/orchestrator build -o ../../tasks/multi-cli-mainflow/tmp/codex-orchestrator ./cmd/orchestrator
python3 tasks/provider-runtime-completion/scripts/verify_install.py \
  tasks/multi-cli-mainflow/tmp/codex-orchestrator \
  tasks/multi-cli-mainflow/tmp/replay-install
```

再将第一段命令的 `install-03` 换成 `replay-install`。安装脚本使用项目正式打包器，并检查真实 `install/doctor`；不会更新用户既有插件安装。

## 已知范围

- AGY 的读取任务明确选用 `view_file`；泛化提示曾走终端工具失败或超时。本轮未增加权限、延长超时或改写认证环境来放行。
- Grok 当前报告未认证，新 Profile 仍拒绝；Codex 的认证保护接线尚未完成，生产 guard 保留。
- 此入口是主流程验收脚本，控制者为它的存活进程；不是原生 Codex TUI 自动派工验收。
- 每次运行的状态和凭据保留用于审计/恢复。失败任务会请求 `stop`；不能确认退出的运行不清空、不重新派发。
- 未验证真实模型写代码、session 续接、带反馈返工和候选提交整合。
