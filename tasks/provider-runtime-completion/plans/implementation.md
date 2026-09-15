# 第 3–5 项实施

基线：2026-09-15，延续上一轮工作区；Go 1.26.8 全部 14 个测试包通过，Python 140 passed / 2 skipped / 1 既有 warning。

1. Provider：保留旧请求兼容层，新增版本化 Execution Profile / Provider Lock 与实际 --version/--help 探测。明确 model、reasoning、role、permission、timeout；拒绝任意参数。新 reviewer/implementer 用 OS 写入隔离，implementer 必须绑定独立 Git worktree。Codex trial guard 保留，能力输出明确不可生产启动；锁更新要求精确摘要确认，不自动升级。
2. 接入：新增通用本机 owner 身份登记及显式 rebind，验证 IPC peer / PID birth / 祖先关系并拒绝 Worker 递归登记；结果采用原 collect/wait/ACK，native owner 接入和原生 history proof 保留为可选模式，不伪造 native 交付证明。
3. runtime：迁移 11 个生产 Python 模块到 runtime/native；打包只从正式目录取实现；旧实验路径留下兼容入口，测试和验收仍在 tasks。验证正式目录与安装包独立导入。
4. 维护：先记录 spool/额度基准，再做增量读取与 durable ACK 后归档、事务额度计数。数据库升级改为单事务版本化迁移，失败回滚且旧二进制拒绝新库；拆分 runtime.go。保持默认 2，增加全局/Provider/工作区限制，unknown 占用保留。
5. 交付：README、安装演示、支持矩阵、分层 CI、本地验证和独立审查。许可证文本与选择说明准备完成后，要求用户明确确认，未收到确认不擅自添加。

不调整用户已有修改；不复制受限参考代码；不把合成 Provider / CLI 框架测试宣传为真实模型请求成功。
