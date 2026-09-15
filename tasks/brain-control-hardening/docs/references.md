# 参考项目核验

核验日期：2026-09-15。默认分支提交与许可证内容 SHA256 见 [reference-revisions.json](../data/reference-revisions.json)。仅借鉴设计，没有复制参考项目代码或 Skill 文本，也没有安装这些项目。

| 项目 / 本次提交 | 核验的当前实现 | 许可证及采用边界 |
| --- | --- | --- |
| backnotprop/orchestrator / `583acf4b` | [主脑 Skill](https://github.com/backnotprop/orchestrator/blob/583acf4b469b91131f96ae2136797749c788b4c7/skills/orchestrator/SKILL.md) 使用 CLI、实时能力/模型发现、compact JSON、等待结果及 owner 决策；另有后台 parent 模式。借鉴简洁契约与等待语义。 | [BSL 1.1](https://github.com/backnotprop/orchestrator/blob/583acf4b469b91131f96ae2136797749c788b4c7/LICENSE)：额外使用授权允许生产/内部业务用途，但不允许向第三方提供商业托管或代管 Agent 编排服务；列明 Change Date 2029-07-09、Change License Apache 2.0。当前不能按 Apache 2.0 处理，原作和衍生副本受其条件约束。 |
| PAL MCP / `7afc7c1c` | [clink/models.py](https://github.com/BeehiveInnovations/pal-mcp-server/blob/7afc7c1cc96e23992c8f105f960132c657883bb1/clink/models.py) 分 CLI client、role、resolved runtime；runner/parser 分目录。[Codex 配置](https://github.com/BeehiveInnovations/pal-mcp-server/blob/7afc7c1cc96e23992c8f105f960132c657883bb1/conf/cli_clients/codex.json) 含绕过 sandbox/approval 参数。只借职责分离，不采用自由参数或放宽权限默认值。 | [Apache 2.0](https://github.com/BeehiveInnovations/pal-mcp-server/blob/7afc7c1cc96e23992c8f105f960132c657883bb1/LICENSE)。 |
| Gas Town / `649b832b` | 原地址已重定向至 `gastownhall/gastown`。[prime.go](https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/internal/cmd/prime.go) 有角色上下文、checkpoint 输出和 compact/resume 快路径；formula/hook/sling 仍是独立工作流操作。只借持久化上下文恢复，不引入其角色层级、Dolt/beads 或第二套状态。 | [MIT](https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/LICENSE)。 |
| MCP Agent Mail / `ac4966c6` | [README](https://github.com/Dicklesworthstone/mcp_agent_mail/blob/ac4966c64d7e39692a4fb9c707448a1718ab29db/README.md) 说明 inbox/thread/ACK 与文件预约语义；本轮未引入或执行其投递实现。 | [MIT with OpenAI/Anthropic Rider](https://github.com/Dicklesworthstone/mcp_agent_mail/blob/ac4966c64d7e39692a4fb9c707448a1718ab29db/LICENSE)，对指定主体及相关代表有额外限制，不是普通无附加条件的 MIT；不复制其实现。 |

Codex 的[官方非交互文档](https://learn.chatgpt.com/docs/non-interactive-mode)区分 JSONL 事件与最终回答。通用文档不能证明已固定的 `codex-cli 0.154.0` 每个字段；本轮保持已有 pin/usage 校验，版本夹具及测试明确标注 synthetic，没有因新版文档放松协议或权限。

## 本地与 GitHub 发布版本

- 本地基准：`8f6ee011`；GitHub `GuanJHCode/Codex-Bird-Orchestrator` main：`be76b0b2d9bd6605a6e15a7b9385cc80d103e828`（2026-09-14 发布）。
- 本地未配置 origin，通过 `gh api` 核对并只读 fetch 到 `FETCH_HEAD`；未改分支、未合并或推送。
- `git diff FETCH_HEAD HEAD -- tools/orchestrator plugins/codex-orchestrator tasks/g1-g4-delivery/scripts/package-plugin.sh`：运行时代码相同；本地额外有 `tools/orchestrator/README.md`、`plugins/codex-orchestrator/skills/orchestrate/SKILL.md`、`internal/adapter/testdata/codex-success.jsonl`。
- 因此“缺 Skill”只能在本地视为已解决，GitHub 发布仍需包含以上三个文件；本次打包检查验证工作区与包内 Skill。基线测试是在本地工作区运行，未冒充 GitHub 发布快照基线。

本项目许可证本轮未选择或改动；后续需用户明确确认。
