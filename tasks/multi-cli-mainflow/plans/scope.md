# 多 CLI 调用主流程

## 本轮目标

用户同意先把不同 CLI 的主流程跑通。优先验证生产安装中的统一入口：
`owner-bind → provider-probe → submit → collect → 校验产物 → ACK → accept → summary`。
真实任务读取任务专属随机内容文件；不以提示词回显或 fake Provider 算成功。

## 边界与验收

- 保留已有工作区修改；本轮基线在 `data/baseline-files.json` 和任务临时副本中记录。
- 不修改既有账号、认证文件、全局配置、Provider Lock 或用户插件安装；使用独立真实安装。
- 先只读 Profile。原生审批、Codex 认证保护、未验证 session 限制不通过降级绕过。
- 回归定位短命进程身份丢失；复验远端失败涉及的三个用例。
- 逐 Provider 记录实际状态；未认证、未完成保护接线不能计为真实成功。
- 每个成功任务验证随机文件内容与产物 SHA-256，ACK 不改变业务状态，ACK 和 accept 重放幂等。
- 保存失败和成功证据；无法证明执行树退出的运行时保留用于恢复。

## 实施项

1. 修复已复现的 `Wait` 早于 birth 登记竞态。
2. 按真实 help/协议补齐 AGY reviewer 调用；修复 stderr help 及选项前缀误判。
3. 通过真实安装运行 Claude/AGY 完整链路，并依据结果修复接线问题。
4. 核实 Grok 认证及 Codex guard 条件，明确仍受阻的能力。
5. 独立审查、Go 全套/race/vet、相称 Python 与打包检查，更新支持矩阵和交付记录。
