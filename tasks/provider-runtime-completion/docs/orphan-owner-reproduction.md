# Source Host 终止后的 orphan Worker owner-bind 复现

日期：2026-09-15。此记录针对修复前已构建的
`tasks/provider-runtime-completion/tmp/codex-orchestrator`；复现脚本、运行态目录和进程均已在记录后清理。

## 目的

确认在 Source Host 已经 `process.Start` Worker、但尚未把该 Worker 的
`PID + birth` 作为 `spawned` 事件持久化时，Worker 杀死 Source Host 并被
init 重新收养后，能否绕过 ancestry 检查注册新的 local owner。

## 步骤

1. 在独立目录 `/private/tmp/runtime-boundary-repro-fast` 中创建两个 fake
   worker：`gate` 等待一个文件后结束；`target` 的依赖为 `gate`。`target`
   启动后记录自身 PID/birth，杀死自己的 PPID（Source Host），等待 PPID
   变为 1，再以自身 PID/birth 调用 `owner-bind`。
2. 以 `ORCHESTRATOR_ENABLE_TEST_FAKE=1` 用上述已构建二进制提交 DAG，并
   accept `gate`，使 `target` 被同一个 Source Host 调度。
3. 以独立 macOS `kqueue` 监视器监视 `fast-worker` 的 exec；当第二个
   Worker（`target`）exec 时立即 `SIGSTOP` Source Host。这样 Source Host
   已完成 `process.Start`，但不能继续写入 `spawned` 的 spool/event。
4. 让 `target` 继续执行其 kill/owner-bind 逻辑，随后检查 owner-bind 退出
   状态以及 SQLite 持久化身份。

## 关键输出

```
source=27262
target=27324

ready pid=27262 path=/private/tmp/runtime-boundary-repro-fast/fast-worker
fork pid=27262 path=
target pid=27324 path=/private/tmp/runtime-boundary-repro-fast/fast-worker
stopped_source pid=27262 path=/private/tmp/runtime-boundary-repro-fast/fast-worker

worker_pid=27324
worker_birth=Tue Sep 15 13:50:12 2026
source_pid=27262
postkill_ppid=1
owner_bind_exit=0
{"controller_thread":"reparented-worker",...,"origin_pid":27324,
 "owner_capability":"/private/tmp/.../owners/owner-8e1....json",...}
```

对应 SQLite 状态：

- `runtime_hosts` 中 Source Host `pid=27262`，状态为 `offline`；
- `runtime_events` 中 target 只有 `prepared`，没有带 target PID/birth 的
  `spawned` 或 `running` 事件；
- 同一个 launch 的 `gate` 已有 PID/birth 事件；
- `owner_grants` 出现新的 `origin_pid=27324`、
  `controller_thread=reparented-worker` grant。

因此这不是仅由静态推断得到的窗口：重收养的 Worker 确实能够在没有控制
capability 的情况下成功取得 owner capability。修复的拒绝条件必须按每个
活跃 `segment_id` 判断是否已有持久化的 PID+birth，不能只检查整个 Host
launch 是否已经存在任一 Worker identity；本例的 `gate` identity 会使后者
错误放行。


## 修复后最终二进制的复验边界（未命中缺失 identity 时序窗口）

复验使用最终二进制
`tasks/provider-runtime-completion/tmp/codex-orchestrator`，且仅使用真实 macOS
进程配合 `ORCHESTRATOR_ENABLE_TEST_FAKE=1` 的 fake Provider；它不是实际模型
Provider 验证。为控制时序，第二轮让 target Worker 在启动后立即终止其 Source
Host 并等待被 init 重新收养。

该轮确实观察到重收养，但 Source Host 已在 target 执行终止动作前持久化了 target 的
`spawned`/`running` PID+birth。因此请求返回的是已有 worker ancestry 保护的
`worker_dispatch_forbidden`，而不是新加入的
`owner_registration_deferred`：

```
worker_pid=50741
source_pid=50706
postkill_ppid=1
owner_bind_exit=2
{"error":"worker_dispatch_forbidden","status":"error","version":1}
native_submit_exit=2
{"error":"worker_dispatch_forbidden","status":"error","version":1}
```

截至复验截止时间，未能在最终二进制上再次命中“target 仅有 `prepared`、尚无
持久化 PID+birth”的精确窗口。因此这不能作为新 per-segment deferred gate 的
真实时序验收证据；该 gate 的覆盖以源码审查和项目内回归测试为准。原先修复前的
真实漏洞证据仍见本记录前半部分。计划中的 DYLD 故障注入没有在时限内启动，未把它
计入结果。

复验创建的 `/private/tmp/orphan-owner-*` 目录、coordinator、Worker 和监视
进程均已按 PID/命令行核验并清理。
