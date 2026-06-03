# Releases

这个目录保存 SDK release note 和 versioned docs 入口。

规则：

- release tag 指向的仓库快照就是该版本文档；
- main 分支文档代表当前开发态或下一 patch；
- 每次发布至少更新对应 package 版本、Quickstart 安装命令和 API Reference 包版本表；
- release workflow 必须构建 wheel 并在干净虚拟环境里跑 install smoke；
- package tag 使用 `rd-<package-name>-v<version>`。

当前推荐接入版本：

- `rd-agent-contracts-v1.14.1`
- `rd-llm-adapter-v1.1.2`
- `rd-agent-core-v0.1.3`

Release notes：

- `rd-agent-core-v0.1.3.md`
- `rd-llm-adapter-v1.1.2.md`
- `rd-agent-contracts-v1.14.1.md`
- `rd-agent-core-v0.1.2.md`
- `rd-agent-core-v0.1.1.md`
- `rd-agent-core-v0.1.0.md`
