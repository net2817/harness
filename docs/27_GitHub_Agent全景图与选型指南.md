# GitHub Agent 全景图与选型指南（137 项目 × 17 赛道）

> **数据快照**：2026-11-24 · 137 个仓库 / 17 个赛道 / 累计 8,460,332 星标 / 121 个近 45 天有提交
> **数据来源**：[GitHub Agent 项目全景图](https://xiaowang018.github.io/agent-landscape/)（元数据抓自 GitHub REST API，赛道、中文定位与上手门槛为上游人工标注）
> **在线章节**：[net2817.github.io/harness/#doc-26](https://net2817.github.io/harness/#doc-26)

---

## 0. 这份文档解决什么问题

第 17 章（Harness 横向对比）讲的是「一个 Harness 内部该怎么设计」，第 18 章（Coze / Dify / LangChain）讲的是「平台、框架、代码三者的边界」；但真正开始动手时，第一个问题还要更靠前一步：**到底该从哪个仓库开始看？**

这份文档把 GitHub 上 Agent 相关的 137 个项目按 17 个赛道摊开，给出三样东西：

1. **坐标**：每个项目属于哪条赛道、什么门槛、维护状态如何；
2. **判断**：从全量数据里读出的六条趋势，以及八种真实场景的组合建议；
3. **映射**：每条赛道对应本手册的哪一章，读到卡住时该去翻哪些仓库。

它是**附录**性质：正文给判断框架，本文给项目坐标。两者配合使用——先用正文判断「我要的是哪一类能力」，再用本文找到这类能力里值得先装、先读源码的那两三个仓库。

| 文档 | 回答的问题 | 什么时候看 |
| --- | --- | --- |
| DOC 17 Harness 横向对比 | 一个 Harness 内部该怎么设计（薄 Loop、WAL、Fail Fast、外部验证） | 决定自研或改造 Harness 时 |
| DOC 18 Coze / Dify / LangChain | 平台、框架、代码三者边界在哪 | 决定「买平台还是写代码」时 |
| **DOC 27（本文）** | 137 个项目的坐标、赛道热度与上手门槛 | 决定「先看哪个仓库」时 |

> 页面里本章锚点是 `doc-26`、编号 DOC 27，追加在修订记录之后，是为了不移动 `doc-00`～`doc-25` 的既有锚点（见修订记录第 4 节「锚点稳定」约定）。

---

## 1. 数据与方法

### 1.1 字段与来源

| 字段 | 来源 | 说明 |
| --- | --- | --- |
| 星标、Fork、语言、许可证、最后提交时间、是否归档、创建时间 | GitHub REST API `/repos/{owner}/{repo}` | 机器抓取，不是人工录入；会随时间变化 |
| 赛道、中文定位、适用人群、点评、上手门槛 | 上游人工标注 | 主观判断，可讨论；同一项目可能跨赛道 |

### 1.2 维护状态判定

按 GitHub 数据自动判定，**归档优先于提交日期**（刚归档的仓库最后一次提交也可能很近）：

| 状态 | 判定规则 | 本次快照 | 选型建议 |
| --- | --- | :--: | --- |
| 已归档 | 仓库被 owner 归档，只读停更 | 6 | 不作为新项目选型，仅作历史参考 |
| 活跃 | 45 天内有提交 | 121 | 可以跟进，但要看 issue 区响应 |
| 维护中 | 210 天内有提交 | 6 | 可用，注意版本兼容 |
| 沉寂 | 超过 210 天无提交 | 4 | 不作为新项目选型 |

### 1.3 上手门槛

按「装完能不能直接跑」分三档：

| 门槛 | 含义 | 本次快照 |
| --- | --- | :--: |
| 易 | 装完能跑，配置为主 | 60 |
| 中 | 要读文档、改代码才能跑通 | 63 |
| 难 | 要理解它的架构或研究背景 | 14 |

「教程 / 学习资料」赛道里的门槛指**阅读门槛**：易＝零基础能读，中＝要会写代码，难＝要懂架构。

### 1.4 许可证

137 个项目里只有 **105 个**是纯 MIT / Apache-2.0，剩下 **32 个**带附加条款：NOASSERTION、Sustainable Use、AGPL-3.0、MIT + 企业版、闭源分发、Elastic-2.0 等。

**星标高不等于能商用。** 标为 `NOASSERTION` 的（n8n、Dify、AutoGPT、Flowise 等）多是「附加条款 / Sustainable Use」这类不完全开放的许可；AGPL-3.0 的项目（如 Skyvern、khoj、ChatDev）在对外提供服务时有源码义务。落地前逐条读 LICENSE，按 DOC 20 的上线红线走。

### 1.5 收录边界与局限

- **只收 Agent**：纯 LLM 应用框架、模型推理框架、聊天客户端不在内，判断标准是「这东西能不能自己决定下一步做什么」；
- **两个例外单独成赛道**：技能包（不做决策，但决定 Agent 干得靠不靠谱）与教程（连程序都不是，但常常是「从哪开始」的真正答案）；
- **局限**：星数受传播效应影响，不等于工程质量；人工标注有主观性；快照不是实时数据；「活跃」只说明 45 天内有提交，不说明它没有回归。

---

## 2. 全景：17 个赛道

### 2.1 赛道分布

按赛道总星标排序。「活跃」指近 45 天有提交的项目数。

| 赛道 | 说明 | 项目数 | 累计星标 | 活跃 | 建议先看 |
| --- | --- | :--: | --: | :--: | --- |
| 编码 Agent | 写代码、改仓库、跑测试 | 21 | 222.0 万 | 17 | mini-swe-agent、DeepSeek Harness、OpenCode |
| 通用自主 Agent | 给个目标自己拆解执行 | 9 | 104.7 万 | 8 | Hermes、OpenClaw |
| 编排框架 / SDK | 搭 Agent 的底层骨架 | 21 | 100.3 万 | 19 | smolagents、LangGraph、pydantic-ai |
| 技能包 / 工作流 | 把工程纪律写进提示词层 | 4 | 78.2 万 | 4 | obra/superpowers、backnotprop/pstack |
| 低代码平台 / 工作流 | 拖拽或节点式搭建，少写代码 | 7 | 66.4 万 | 5 | Dify、Coze Studio |
| 知识库 / RAG | 把私域文档变成 Agent 的上下文 | 8 | 50.3 万 | 7 | RAGFlow、LightRAG |
| 教程 / 学习资料 | 先读别人怎么做的，再决定自己动手 | 12 | 43.9 万 | 11 | hello-agents、learn-claude-code |
| 工具协议 / MCP | 给 Agent 装手脚的标准接口 | 9 | 37.4 万 | 9 | FastMCP、MCP servers、A2A |
| 深度研究 / 检索 | 自动调研并产出报告 | 6 | 29.1 万 | 4 | deer-flow、GPT-Researcher |
| 记忆层 | 跨会话记住人和事 | 7 | 26.6 万 | 7 | mem0、graphiti、cognee |
| 多智能体协作 | 多个角色分工配合 | 6 | 24.8 万 | 5 | MetaGPT、ag2 |
| 浏览器操作 | 让 Agent 自己上网 | 6 | 23.4 万 | 6 | browser-use、Playwright MCP |
| 桌面 / 电脑操作 | 看屏幕、动鼠标、控本机 | 6 | 17.3 万 | 5 | midscene、UI-TARS、Agent-S |
| Agent 可观测 / 评测 | 看得见它干了什么、跑得好不好 | 6 | 10.7 万 | 5 | Langfuse、promptfoo、inspect_ai |
| Agentic RL / 训练环境 | 训练 Agent 自己的策略 | 5 | 4.9 万 | 5 | verl、OpenEnv |
| 语音 Agent | 能听会说的实时对话 | 3 | 4.4 万 | 3 | pipecat、LiveKit Agents |
| Agent 基础设施 | 沙箱、运行时等底座 | 1 | 1.5 万 | 1 | E2B |

### 2.2 星标前 12

| # | 项目 | 星标 | 赛道 | 门槛 | 状态 |
| :-: | --- | --: | --- | :-: | --- |
| 1 | [morluto/rea](https://github.com/morluto/rea) | 475,682 | 编码 Agent | 难 | 活跃 |
| 2 | [openclaw/openclaw](https://github.com/openclaw/openclaw) | 395,121 | 通用自主 Agent | 易 | 活跃 |
| 3 | [mattpocock/skills](https://github.com/mattpocock/skills) | 331,701 | 技能包 / 工作流 | 易 | 活跃 |
| 4 | [obra/superpowers](https://github.com/obra/superpowers) | 325,437 | 技能包 / 工作流 | 易 | 活跃 |
| 5 | [affaan-m/ECC](https://github.com/affaan-m/ECC) | 309,604 | 编排框架 / SDK | 中 | 活跃 |
| 6 | [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) | 286,111 | 编码 Agent | 易 | 活跃 |
| 7 | [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) | 265,675 | 通用自主 Agent | 易 | 活跃 |
| 8 | [anomalyco/opencode](https://github.com/anomalyco/opencode) | 228,818 | 编码 Agent | 易 | 活跃 |
| 9 | [n8n-io/n8n](https://github.com/n8n-io/n8n) | 211,913 | 低代码平台 / 工作流 | 易 | 活跃 |
| 10 | [Significant-Gravitas/AutoGPT](https://github.com/Significant-Gravitas/AutoGPT) | 188,155 | 通用自主 Agent | 中 | 活跃 |
| 11 | [langgenius/dify](https://github.com/langgenius/dify) | 161,747 | 低代码平台 / 工作流 | 易 | 活跃 |
| 12 | [langflow-ai/langflow](https://github.com/langflow-ai/langflow) | 156,881 | 低代码平台 / 工作流 | 易 | 活跃 |

### 2.3 其它分布

| 维度 | 分布 |
| --- | --- |
| 语言 | Python 71 · TypeScript 41 · JavaScript 5 · Jupyter Notebook 5 · Go 4 · Rust 3 · Shell 3 · 未识别 3 · C# 1 · MDX 1 |
| 门槛 | 易 60 · 中 63 · 难 14 |
| 创建年份 | 2019：2 · 2021：1 · 2022：5 · 2023：35 · 2024：35 · 2025：46 · 2026：13 |

语言这一行有个反直觉的地方：Python 项目最多（71 个），但编码 Agent 的头部几乎全在 TypeScript / Rust——终端 TUI、沙箱、权限这些工程部件需要的是分发与进程控制，不是训练生态；Python 主导的是训练、评测和研究侧。

另外，**59 个项目（43%）创建于 2025–2026 年**。这个赛道一年半就换了一茬，所以选型时「最近一次提交」比「星数」更能说明它还活着。

---

## 3. 六条判断

### 判断一：入口从「自己搭」变成「装完直接用」

星标前八里有六个是成品 Agent / Harness（rea、OpenClaw、ECC、DeepSeek Harness、Hermes、OpenCode），传统框架 LangChain 排到第 16。这不是说框架没用了，而是**默认入口变了**：目标是把事做完，先装一个成品；目标是做成产品，再回到框架层。

### 判断二：技能包成了独立的一层

4 个技能包合计 78.2 万星（占全榜 9.2%），mattpocock/skills 与 obra/superpowers 都在 32 万以上，比绝大多数框架高。它们不写代码，写的是「Agent 该怎么干活」的纪律：先对齐意图、按 SDLC 走完、每步留证据。实践里更常见的是**挑一两个混用**而不是全装——技能太多会挤占上下文，还会互相抢命令名（两个「总入口」都想接管 `/tdd`）。

### 判断三：框架没有消失，而是下沉成「被组合的零件」

LangGraph 用「图 + 状态」把长流程、人审、断点续跑讲清楚，因此被大量产品当作状态机内核；Dify / Coze 这类平台则把框架包进可视化层。选型问题已经从「选哪个框架」变成「**哪一层自己写、哪一层买**」。

### 判断四：「接线层」补齐了，它决定能不能上生产

MCP 9 个项目 37.4 万星、记忆层 7 个 26.6 万星、评测 6 个 10.7 万星；A2A 补上了 MCP 没管的另一半——Agent 之间怎么发现彼此、怎么委派任务。这一层做不出 Demo 效果，但少了它，前面装的东西都只能停在演示阶段。

### 判断五：训练层出现，Agentic RL 从论文走进仓库

verl、slime、prime-rl、ART、OpenEnv 五个项目组成新赛道。研究重心明显从「怎么调提示词」挪到「怎么造可验证的环境和 verifier」。对工程团队的实际含义是：**跑通的流程可以考虑固化成小模型**，把每次推理的钱省下来——但前提是先把评测基线做出来。

### 判断六：星数通胀与许可证风险并存

前 20 名占 52.8% 星，前 10 名占 35.7%，中位数只有 31,543；32 个项目带非标准许可；6 个已归档、4 个沉寂。三条合一：**星标是传播指标，不是可用性指标**。选型时先过三关——许可证、维护状态、有没有可复现的评测。

---

## 4. 按场景选型：八张组合牌

不要把「赛道第一」当成「我的第一」。下面按真实场景给组合：一列是**先装哪个**（当天能跑起来的），一列是**再加什么**（跑通之后补的能力），最后一列是最容易踩的坑。

| 场景 | 先装一个 | 再加两个 | 注意什么 |
| --- | --- | --- | --- |
| 个人终端提效 | DeepSeek Harness 或 OpenCode | cc-switch（多 CLI 统一入口）+ 低门槛技能包 | 别一上来装五套；先记录一个真实任务的步数、token 和失败点 |
| IDE 内编码 | Cline / Kilo Code / Continue | Roo-Code 的多模式提示词作参考；mini-swe-agent 读源码 | 插件形态依赖各家 API Key，权限范围要按仓库收紧 |
| 团队并行编码 | Orca 或 OpenHands | claude-task-master 做任务 DAG；SWE-agent 做评测基线 | 并行任务必须共享同一套验证命令，否则无法比较产出 |
| 企业内部平台 | Dify 或 Coze Studio | LangGraph 写复杂状态流转；n8n 做系统集成 | 平台解决搭起来，框架解决改得动；两个都要，别只买一个 |
| 知识与研究 | RAGFlow / LightRAG | deer-flow、GPT-Researcher（调研产出）；graphify、graphiti（关系与时效） | 先定评测集再换方案，否则永远在换 embedding |
| 浏览器与桌面自动化 | browser-use、Playwright MCP | midscene / UI-TARS / Agent-S（桌面与 GUI） | 登录态、验证码、页面改版是最常见的稳定性来源 |
| 上线前评测与观测 | Langfuse 或 promptfoo | DeepEval、inspect_ai（可审计评测）；AgentOps 做回归 | 评测要能进 CI；只看榜单分数会把配置差异当模型差异 |
| 数据不出内网 | OpenHands / Cline 自托管 + 本地模型 | vLLM 或 SGLang 起模型服务；Continue 接自有网关 | 先确认许可证：AGPL、Sustainable Use、闭源分发这几种要单独过法务 |

### 三条不要

1. **不要因为星数高就选它**——先看它是否归档、许可证是否能过法务、issue 区最近三个月是否还在回。
2. **不要一开始就上多 Agent**——榜单里 6 个多智能体项目合计 24.8 万星，但「通信即复杂度」；单 Agent 能解决的，加协作只会把失败点转移到调度层（DOC 17 铁律 6）。
3. **不要拿别人的 Benchmark 当自己的结论**——同一模型换一套工具和提示，SWE-bench 分数可以差出十几个点；用自己的任务集复测，哪怕只有 20 条。

---

## 5. 与本书章节的映射

读到某一章卡住时，从这张表倒查该看哪些仓库：

| 本手册章节 | 对应赛道 | 建议先看的项目 |
| --- | --- | --- |
| DOC 03 AI Harness 企业落地教程 | 编排框架 / SDK · 技能包 · Agent 基础设施 | smolagents（最小实现）、LangGraph（状态机）、E2B（沙箱） |
| DOC 17 Harness 横向对比与最新实现范式 | 编码 Agent · 编排框架 | mini-swe-agent（100 行读源码）、DeepSeek Harness、OpenCode |
| DOC 18 Coze / Dify / LangChain 选型 | 低代码平台 · 编排框架 | Dify、Coze Studio、n8n、LangGraph |
| DOC 12 AI Native 研发范式 | 技能包 · 记忆层 · 评测 | superpowers、mem0、Langfuse |
| DOC 05 AI Infra 企业平台教程 | Agent 基础设施 · Agentic RL | E2B、verl、slime |
| DOC 13–15 岗位与面试 | Agent 可观测 / 评测 · Agentic RL | promptfoo、inspect_ai、OpenEnv |
| DOC 19 FastAPI × MCP × React | 工具协议 / MCP | FastMCP、python-sdk、A2A |
| DOC 25 最新资料与来源索引 | 教程 / 学习资料 | hello-agents、ai-agents-for-beginners、learn-claude-code |

---

## 6. 从 30 分钟到 1 天的上手路径

1. **30 分钟：装并跑通一个成品。** DeepSeek Harness 或 OpenCode 二选一，用一个真实的小任务（改一个 bug、补一个测试），记录步数、token、失败点各一次。目的不是学会它，而是建立「成品 Harness 已经能做什么」的基线。
2. **2 小时：读最小的实现。** mini-swe-agent（约 100 行）和 smolagents（核心约千行）各读一遍，重点看三件事：循环怎么退出、工具返回错误怎么进上下文、什么时候停下来问人。这一层读完，DOC 17 的八条铁律才有落点。
3. **1 天：做一个对照实验。** 同一个任务，用「成品」和「框架」各实现一次（例如 OpenCode vs LangGraph），比较：完成率、步数、token、人工介入次数、失败可复现性。结论写成一页，参照 DOC 24 的验收格式存档。

**验收清单（做完打勾）**：

- [ ] 能说清你选的方案在「薄 Loop / 厚 Control Plane」里的位置；
- [ ] 工具调用有超时、幂等和权限边界，失败会进日志而不是被模型忽略；
- [ ] 有外部验证（编译 / 测试 / 类型检查），不是模型自评；
- [ ] 知道崩溃后从哪里恢复（WAL 或等价机制）；
- [ ] 评测集是你自己的 20 条任务，不是榜单分数。

---

## 7. 数据维护与更新

本手册页面里的清单**不是手写 HTML**，而是由脚本从数据文件生成的：

| 文件 | 作用 |
| --- | --- |
| `docs/data/agent-landscape-2026-11-24.json` | 合并后的单文件快照（137 条 + 17 个赛道定义） |
| `scripts/merge_landscape_data.py` | 合并上游 `data.json` + `annotations.json` + `tracks.json`，校验双向一致、算维护状态 |
| `scripts/build_landscape.py` | 生成页面章节（CSS / 导航 / HTML / JS），`--apply` 写入 `index.html`，`--check` 校验 |

更新步骤：

```bash
# 1. 在上游仓库刷新元数据（需要 GitHub token，未认证只有 60 次/小时）
git clone https://github.com/xiaowang018/agent-landscape
cd agent-landscape && GITHUB_TOKEN=xxx python scripts/fetch.py

# 2. 合并成快照
cd ..
python scripts/merge_landscape_data.py --src ../agent-landscape --date 2026-11-24

# 3. 生成并写入 index.html（只替换 LANDSCAPE 标记块，可重复执行）
python scripts/build_landscape.py --apply

# 4. 校验：卡片数、锚点、导航一致性
python scripts/build_landscape.py --check
```

维护约定：

1. **先改数据、再改结论**：星数、归档状态、赛道归属变化后，第 2、3 节的数字和判断要一起复核；
2. **不要手改卡片**：`--apply` 会覆盖标记块内的内容，手改会在下次生成时丢失；
3. **快照命名**：数据文件按抓取日期命名（`agent-landscape-YYYY-MM-DD.json`），脚本默认取字典序最后一个；换快照时同步改本章页面的 `doc-source` 与修订记录；
4. **新增项目先补标注**：上游 `annotations.json` 里缺标注的仓库会被合并脚本拒绝（避免页面少卡或字段空白）；
5. **上游署名**：数据整理自 agent-landscape 项目，更新时保留其来源链接与许可证说明。

---

## 8. 来源与免责

- 上游项目：[xiaowang018/agent-landscape](https://github.com/xiaowang018/agent-landscape)；在线版：[xiaowang018.github.io/agent-landscape](https://xiaowang018.github.io/agent-landscape/)；
- 元数据：GitHub REST API（快照 2026-11-24）；中文标注与门槛：上游人工标注；
- 本文只整理公开信息与公开元数据，各项目的版权与许可证归其原作者；标注为「见仓库」「NOASSERTION」的，请以仓库 LICENSE 文件为准；
- 数据会过时：做采购或架构决策前，请用当日数据复核，并按 DOC 20 的上线红线逐项检查。
