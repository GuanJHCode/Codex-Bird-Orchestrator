# Provider、owner 与运行时配置

## 三个独立层次

1. **协议 Adapter**：构造固定参数、解析版本化事件、识别 session。禁止 `extra_args`；未知协议/能力显式拒绝。
2. **Execution Profile v1**：`role`、`model`、`reasoning`、`permission`、`timeout_ms`。模型名不当作命令参数拼接；思考值仅 `low` / `medium` / `high`；超时 1–3,600,000 ms，仍受 segment 已授预算约束。
3. **Provider Lock v1**：`provider`、`protocol`、`binary.path/version/sha256`。启动前验证版本/能力和摘要，在最终进程启动边界再次核对原 Provider 摘要；sandbox wrapper 不替换 Provider 的锁身份。

请求中的 `adapter` 示例：

```json
{
  "provider": "claude-code",
  "provider_lock": {
    "version": 1,
    "provider": "claude-code",
    "protocol": "claude-stream-json-v1",
    "binary": {"path": "/canonical/claude", "version": "observed --version", "sha256": "observed 64 hex digest"}
  },
  "profile": {
    "version": 1,
    "role": "reviewer",
    "permission": "read-only",
    "reasoning": "medium",
    "timeout_ms": 30000
  },
  "directory": "/canonical/workspace",
  "prompt": "目标、输入、范围、约束、产物、验收条件"
}
```

省略 `model` 使用 Provider 的当前默认模型；需要可复现的模型选择时填写明确模型 ID。`provider_lock` 与旧 `binary_*` 字段不能混用。旧请求保留兼容层；新 profile 的权限不可与旧 allow/deny 列表混用。

### 角色与隔离

只读指文件写入权限：保留既有 Provider 读取/认证环境，不宣称只允许读取 cwd 的全系统白名单。

- reviewer：`permission=read-only`，Claude 原生 `plan` 权限，加 macOS 文件写入隔离。
- implementer：`permission=workspace-write`，必须是经授权的 Git linked worktree。保留 Claude 原生 `default` 审批；只允许工作区内容及受控临时/产物目录写入，拒绝 `.git` 和公共 Git 元数据写入。主脑仍需通过现有 Git Host 生成/审查/整合候选。
- 控制数据库、owner/control/bootstrap 凭据和其他任务的 spool/report capability 不向新 profile Worker 开放。当前任务可以读取自己的报告能力文件，在其 `artifacts/` 子目录写报告产物。
- 不添加 bypass、自动接受所有工具、`acceptEdits` 或全盘写权限参数。Provider 原生审批拒绝时，任务失败或等待，主脑不能伪造审批。

当前新 profile 的真实续接测试未通过，故拒绝 session resume：`profile_resume_not_verified`。Codex 生产启动仍被 `codex_trial_guard_not_ready` 拒绝；AGY/Grok 的新 profile 返回 `execution_profile_unsupported`。旧协议的显式恢复接口与已有安全校验保留，不能通过退回旧 profile 规避新请求的权限要求。

### 探测与升级

```text
orchestrator provider-probe --request /private/probe.json
orchestrator provider-lock  --request /private/confirmed-lock.json
```

探测请求：`provider`、`binary_path`，可带 `lock_file`。路径须规范化且不指向 symlink。仅运行有界的 `--version` / `--help`，不会调用模型或修改锁。输出给出锁候选及 profile / resume 能力结论。

写入锁必须提供用户确认的 `confirm_sha256`；更新已有锁还必须提供其 `previous_sha256`。模型不得自行替用户确认升级。已有版本漂移时拒绝启动，重新探测、展示差异并取得确认。控制面的文件权限不隔离任意同 UID 恶意进程；最后一次摘要检查与 OS path exec 之间仍有这一既有威胁模型之外的竞态窗口。

## Owner 与返回方式

`owner_mode` 和 `delivery_mode` 分别表示授权来源和结果返回方式；均默认 `native`，不是同一个开关。

通用接入先准备 `0600` 的 owner 请求：

```json
{"controller_thread":"stable-main-agent-id","origin_pid":12345,"origin_birth":"OS process birth identity"}
```

执行 `owner-bind --state-dir <state> --request <file>`。PID/birth 必须是该控制连接的当前进程或同 UID 祖先进程；应选择持续存活的主脑进程。`birth` 使用进程身份探针，与协议中的 `process.Birth` 一致，不能只传 PID。返回投影字段和 `owner_capability` 路径，不返回 token。

提交时把这些 owner 字段加入现有 submit 请求，设置：

```json
{"owner_mode":"local","delivery_mode":"collect"}
```

协调器再次校验能力文件、已登记的 token 哈希、IPC peer 祖先链和 owner 身份。已登记 Source Host 的后代在 Worker 第一条事件到达前也不能派工；历史 Host 身份在 offline/rebind 后仍参与校验，PID 复用以 birth 区分。

若任一活跃执行片段尚无持久化 PID/birth，`owner-bind` 与新 native submit 返回 `owner_registration_deferred`，防止 Host 意外退出后被重新收养的 Worker 自行取得主脑身份。判定按 segment 进行；同一 Host 的其他 Worker 身份不能代替它。已有 local owner 可继续提交；resume/retry/accept/answer/rebind 在此期间还要求连接祖先中存在已登记主脑身份。查询和停止仍使用原控制凭据。若 owner 同时丢失，须先通过显式 Host 恢复与进程对账解决不明片段，再登记/rebind 新 owner；不能清除 unknown 状态或删除数据库绕过检查。

`collect` / `wait-events` 返回紧凑事件与 `delivery_id`、`collection_proof_sha256`。本机收集模式的 ACK 使用这两个值，绑定该页所有 actionable event 的 ID/revision/hash/action slot；不可替换成 native `history_proof_sha256`。native 模式仍使用已有 history proof。ACK 只确认事件处置，`accept` / `answer` / `retry` 仍分别执行原有业务校验。

### 显式 rebind

旧 owner 丢失后，先用新主脑身份执行 `owner-bind`，再提交：

```json
{
  "version": 1,
  "owner_mode": "local",
  "owner_capability": "/private/state/owners/new-grant.json",
  "control_file": "/private/state/control/original-control.json"
}
```

执行 `rebind-owner --state-dir <state> --request <file>`。旧 owner 必须已失效，新 owner 必须当前存活且满足 peer 校验。原 run 的 `origin_context_id` 保留；rebind 不启动 Worker。后续恢复仍需要显式 `resume` 和进程对账。原生 rebind 的 attachment 证明流程不变。

## 并发与数据库

在私有 state 目录创建 `0600` 的 `runtime-limits.json`，由下次协调器启动读取并事务保存到同一个 SQLite 数据库：

```json
{
  "version": 1,
  "global": 2,
  "providers": {"claude-code": 1},
  "workspaces": {"/canonical/worktree": 1}
}
```

数值范围 1–32；未指定的 Provider/工作区沿用全局值。默认全局 2。路径按规范工作区归一化；不合法字段、版本、权限或数值拒绝启动，不静默忽略。修改配置在下一次安全重启后生效；删除配置文件不会撤销数据库中已保存的策略。降低上限不杀现有任务；prepared/running/stopping/unknown 均计数。符合其他资源限制的 ready 任务可继续启动。

数据库当前 schema v5：v2 归并既有 runtime schema，v3 增加 local owner / collection receipt，v4 保存并发策略，v5 增加事务额度计数。DDL、回填与 schema 版本更新在同一事务中提交。旧二进制拒绝新 schema；升级前应在协调器安全停止后备份整个 state，不能直接降级覆盖。

spool 的 `ReadAfter` 只读取未归档后缀；`Read` 包括历史，供会话与进程恢复使用。ACK 前缀先持久化，再归档；中断产生的双份记录按 sequence/content 对账。归档不等于清理或释放存储额度。额度由 SQLite triggers 跟随事件 insert/update/delete 同事务变化，包含全局、run 和报告 capability；回滚不会泄漏计数。

### 受控报告产物

新提交报告的单个 artifact 上限与 Host 输出一致，为 1 MiB。协调器在读取内容前校验真实文件大小，再通过同一个 NOFOLLOW 文件描述符有界计算哈希，并核对前后文件身份。新 profile 的报告根目录限定为当前 capability 的 `artifacts/`；旧报告 capability 的已注册根目录保留兼容，但不允许 symlink 穿越。

已接受 artifact 的引用字节计入原有 segment/run/global 存储准入与事务计数，旧记录在迁移时回填。因此接近原额度的工作流可能更早被拒绝。相同文件被多个独立报告引用时保守重复计费；归档或 ACK 不退费，删除相应持久记录才更新计数。额度管理的是已提交记录及其产物，不是未提交工作区文件的 OS 文件系统配额。
