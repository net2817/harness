# AI Harness / AI PDE / AI Infra 企业级完整学习方案

本仓库包含可直接部署到 GitHub Pages 的完整 HTML 学习手册。

- `index.html`：自包含单页手册，支持搜索、主题切换、代码复制和打印导出 PDF。
- 内容覆盖 AI Harness、AI PDE、AI Infra、GPU 物理集群、HPN/RDMA、NVLink、HGX、NVL72、智算集群 v3.3（GLM-5.3、存储、网络、骨干环网、异构算力）、国产 GPU、千卡集群和公有云 GPU，并附大模型推理服务可靠性工程师的岗位解读与模拟面试问答，以及 Pi / Aider Harness 横向对比、可运行的薄 Loop + WAL 参考实现、两篇典型岗位面试题库（推理 SRE / AI 平台架构师）、Coze / Dify / LangChain 选型对比、FastAPI × MCP × React × AIGC 全栈集成、DCS 专项教程与 3 套模拟试卷，以及修订记录。
- **DOC 27「GitHub Agent 全景图与选型指南」**（`#doc-26`）：把 GitHub 上 137 个 Agent 相关项目按 17 个赛道摊开（数据快照 2026-11-24），页面内可搜索、按赛道 / 语言 / 门槛 / 活跃度筛选并按星数或更新时间排序；正文给六条趋势判断、八种场景组合、与本书章节的映射，以及「30 分钟 → 1 天」的上手路径。数据来自 [agent-landscape](https://xiaowang018.github.io/agent-landscape/)，本仓库保存合并快照并可重复生成。
- **`landscape.html` 独立浏览页**：同一份 137 条数据单独成页，加载更快，筛选状态写进地址栏可直接分享（如 `#q=rust&cat=coding&sort=upd`），支持明暗主题与打印。
- Agent Harness 架构图：展示会话与上下文、任务编排、提示与策略、模型与工具路由、记忆与状态、安全护栏、执行运行时和可观测性。

## 仓库结构

```
index.html                                   # 单页手册（GitHub Pages 入口）
landscape.html                               # Agent 全景图独立浏览页（脚本生成）
docs/                                        # 章节 Markdown 源（01–27）
docs/data/agent-landscape-2026-11-24.json    # DOC 27 的合并快照（137 条）
scripts/merge_landscape_data.py              # 合并上游 data/annotations/tracks，校验并归一化
scripts/build_landscape.py                   # 生成 DOC 27 的 CSS/导航/章节/JS（--apply / --check）
examples/harness_wal.py                      # 薄 Loop + WAL 参考实现
assets/                                      # 架构图与配图
```

DOC 27 由脚本生成，**不要手改 `index.html` 里的卡片**：

```bash
python scripts/merge_landscape_data.py --src ../agent-landscape   # 合并快照
python scripts/build_landscape.py --apply                          # 同时写入 index.html 与 landscape.html
python scripts/build_landscape.py --check                          # 校验卡片数 / 锚点 / 导航 / 离线自包含
```

## 启用 GitHub Pages

仓库 Settings → Pages → Build and deployment → Source 选择 `Deploy from a branch` → 选择 `main` 和 `/ (root)` → Save。
