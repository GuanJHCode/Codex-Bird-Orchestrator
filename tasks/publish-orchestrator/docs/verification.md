# 推送前验证

日期：2026-09-15。目标：`GuanJHCode/Codex-Bird-Orchestrator` 的 `main`。

远仓基底为 `be76b0b2d9bd6605a6e15a7b9385cc80d103e828`，与本地开发历史无共同祖先。发布检出基于该远仓提交，仅加入本轮源码、测试、文档和必要依赖，保留原发布历史，不使用 force push。

远仓原快照缺失的 `codex-success.jsonl`、`native_product_plan.py`、`proxy_native_runtime.py` 从本地已提交基线补齐。用户另有的 `proxy_native_runtime.py` 工作区单行改动、`tasks/real-user-trial/plans/scope.md`、本地 AGENTS 和临时运行态均未加入本次提交。

在独立发布检出执行：

- `go test -count=1 ./...`：14 个有测试的包通过（[日志](go-test.log)）。
- `go test -race -count=1 ./...`：14 包通过（[日志](go-race.log)）。
- `go build ./...`、`go vet ./...`：均退出 0。
- `python -m pytest -p no:cacheprovider tools/native-product-bridge tools/real-user-trial tasks/brain-control-hardening/scripts/test_package_skills.py tasks/provider-runtime-completion/scripts/test_runtime_layout.py -q -rs`：142 passed / 2 skipped / 1 既有 warning（[日志](python-test.log)）。
- `git diff --cached --check`：通过。发布副本去除了 3 个 pytest 历史日志的行尾空白；本地原始日志保留，结果内容未改。

环境为 macOS arm64、Go 1.26.8、Python 3.14，pytest 9.1.1、PyYAML 6.0.3。本次推送没有再调用模型或进行原生 TUI 验收；前轮验证及保留限制见 [交付记录](../../provider-runtime-completion/docs/delivery.md)。许可证仍待维护者确认，未增加正式 LICENSE；本次不创建 release 或 tag。
