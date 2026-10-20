# Coze / Dify / LangChain 对比与选型：从低代码平台到代码框架

> **本章要解决的问题**：企业要做一个 AI 应用，到底该用 **Coze（扣子）**、**Dify**，还是 **LangChain / LangGraph**？
> 三者经常被放在一起比较，但它们**根本不是同一类东西**——一个是产品化平台，一个是开源自托管平台，一个是开发者框架。选错的代价不是"多写几行代码"，而是**锁死迁移路径、返工三个月**。
>
> 本章给出一张定位表、一张 14 维能力矩阵、一棵选型决策树、三种企业常见组合、同一需求的三套实现，以及一份 30 分钟可执行的对比实验。

## 1. 先把三个东西放回正确的位置

| 类别 | 代表 | 本质 | 典型使用者 | 交付形态 |
|---|---|---|---|---|
| **产品化 Bot 平台** | **Coze（扣子）** | 一站式 AI Bot / Workflow / 插件平台（SaaS，另有开源的 Coze Studio / Coze Loop） | 业务运营、产品经理、轻量交付团队 | Bot、Web 页面、API、渠道发布 |
| **开源 LLM 应用平台** | **Dify** | 可视化 Workflow + RAG + Agent + 模型管理 + API 发布的 LLMOps 平台，可自托管 | 企业 AI 中台、中小研发团队 | Web App、API、嵌入式页面 |
| **开发者框架** | **LangChain / LangGraph / LangSmith** | 代码级组件库 + 有状态图编排 + 可观测与评测 | 平台团队、复杂业务、需要深度定制的团队 | 你自己的服务（没有现成 UI/权限/多租户） |

**一句话总结：**

```
Coze      最快上线，边界最硬 —— 平台给你什么，你就用什么
Dify      自托管与可视化之间最平衡 —— 有 UI、有 API、能改代码
LangChain 最自由，工程成本最高 —— 什么都能做，但什么都要自己做
```

> ⚠️ 最常见的认知错误：**把 LangChain 当成"开源的 Dify"**。LangChain 是库，不提供账号体系、多租户、权限、应用管理、发布渠道；这些在 Dify 里是产品能力。反过来，**把 Dify 当成"能写任意代码的框架"**也会失望——它的强项是标准化编排，不是无限定制。

## 2. 能力矩阵（14 维）

> 说明：以下为**定性对比**，具体能力随版本变化很快，落地前必须以当前版本文档为准。

| 维度 | **Coze（扣子）** | **Dify** | **LangChain / LangGraph** |
|---|---|---|---|
| **部署形态** | SaaS 为主；Coze Studio / Coze Loop 可自托管 | 开源自托管（Docker Compose / K8s），也有云版 | 纯代码，随你的服务部署 |
| **搭建方式** | 可视化拖拽 + 提示词 + 插件 | 可视化 Workflow / Chatflow + 少量代码节点 | 100% 代码 |
| **学习曲线** | 最低，半天可出 Demo | 中，1–2 天可跑通 | 高，需要理解抽象与状态机 |
| **RAG 能力** | 内置知识库、分段、召回 | 内置知识库 + 分段 + 混合检索 + 重排 + 引用 | 组件齐全但要自己组装（Loader/Splitter/Retriever/Rerank） |
| **Agent / Workflow** | Workflow 节点 + 插件调用 | Workflow / Chatflow + Agent 节点 + 循环/条件/变量 | LangGraph 有状态图，表达能力最强 |
| **工具与插件** | 官方插件市场 + 自定义插件 | 内置工具 + 自定义 OpenAPI 工具 + 插件市场 | 任意 Python/JS 函数、任意 SDK |
| **MCP 支持** | 以插件生态为主，需按版本确认 | 通过插件/工具接入，需按版本确认 | 原生可接任意 MCP Client/Server |
| **多模型接入** | 以平台支持的模型清单为准 | 支持多家云模型 + 本地模型（Ollama/vLLM 等） | 任意模型，自己写 Provider |
| **发布形态** | Bot / Web / API / 渠道 | Web App / API / 嵌入 | 自己实现 |
| **可观测与评测** | Coze Loop 提供调试、评测、观测能力 | 内置日志、标注、部分评测能力 | LangSmith（商业/自托管）或自己接 OTel |
| **权限与多租户** | 平台账号体系 | 社区版较简单，企业能力需看版本/商业版 | 完全自己实现 |
| **二次开发** | 受平台扩展点约束 | 可改源码、可写代码节点、可接外部服务 | 无限制 |
| **许可** | 平台服务条款；Coze Studio/Coze Loop 为 Apache-2.0 | **基于 Apache-2.0 的附加条件许可**（多租户 SaaS、品牌展示等有额外限制，必须读 LICENSE） | **MIT** |
| **适合规模** | 快速验证、轻量业务、运营驱动 | 中小型企业的 AI 中台、部门级平台 | 大型企业、复杂 Agent、长期自研 |

**关于许可的提醒**：Dify 的许可证不是"纯 Apache-2.0"，而是带附加条件的开源许可；n8n 使用的是 Sustainable Use License（fair-code，非 OSI 开源）。**任何"能不能商用/能不能做 SaaS/能不能去 logo"的问题，都必须回到 LICENSE 原文**，不要听二手结论。

## 3. 选型决策树

先回答**三个硬问题**，顺序不能乱：

```
Q1 数据能不能出企业边界？
   ├─ 不能 → 排除纯 SaaS，只能在「自托管 Dify」与「LangChain 自研」之间选
   └─ 能   → 进入 Q2

Q2 业务复杂度：是否需要自定义状态机、多 Agent、长任务恢复、人工审批？
   ├─ 需要 → LangGraph（或 Dify + 自研微服务混合）
   └─ 不需要 → 进入 Q3

Q3 谁来长期维护？
   ├─ 业务/运营团队 → Coze（或 Dify 的可视化应用）
   └─ 平台/研发团队 → Dify 自托管
```

**三条硬判据（比功能清单更重要）：**

| 判据 | 问法 | 选错的后果 |
|---|---|---|
| **数据合规** | 数据能不能离开企业/能不能出境？ | 上线前被安全否掉，全部返工 |
| **复杂度上限** | 未来 12 个月会不会出现"平台表达不了"的流程？ | 中途推倒重来，迁移成本极高 |
| **维护主体** | 谁能改、谁能排障、谁能升级？ | 平台建好了但没人维护，逐渐荒废 |

> 经验值：**先用 Coze 验证业务价值（1–2 周），再用 Dify 做部门级产品化（1–2 月），确有必要时用 LangGraph 做核心复杂链路**。反过来（一上来就全自研）是中小企业最常见的过度工程。

## 4. 企业里最常见的三种组合

### 组合 A：Coze 做前台，企业 API 做后端（最快验证）

```
用户 → Coze Bot（对话/Workflow/插件）
                 │ 调用
                 ▼
        企业 API 网关（鉴权/审计/限流）
                 │
                 ▼
        内部系统（工单/CRM/知识库/数据库）
```

- **适用**：业务方要在一两周内看到效果；数据本身不敏感，或只走"查询类"能力。
- **边界**：Coze 只做"交互与轻编排"，**真正的业务规则与写操作放在企业 API 里**，这样将来换平台时业务逻辑不丢。

### 组合 B：Dify 做 AI 中台 + LangGraph 做复杂 Agent（最推荐的中大型形态）

```
业务应用 / 前端
      │
      ▼
Dify（应用管理 + 知识库 + 可视化 Workflow + API 发布）
      │  复杂任务通过 HTTP/gRPC 调用
      ▼
LangGraph Agent 微服务（状态机 + 工具 + 人工审批 + Checkpoint）
      │
      ▼
统一 AI Gateway → 多模型 / 私有推理
```

- **适用**：既要"业务能自己配流程"，又要"核心链路能写代码"。
- **关键设计**：**Dify 管"应用与知识"，LangGraph 管"复杂状态与恢复"**，两者用稳定的 HTTP 契约解耦；不要把所有逻辑都塞进 Dify 的代码节点。

### 组合 C：全自研 LangChain / LangGraph（大型企业）

```
自研控制台（应用/版本/权限/配额）
        │
        ▼
LangGraph 编排层（状态/检查点/人工审批）
        │
        ▼
统一 AI Gateway → 模型服务 → GPU
        │
        ▼
OTel + Prometheus + Loki + Tempo（自建可观测）
```

- **适用**：有平台团队、有明确差异化需求、对合规和可控性要求极高。
- **代价**：UI、权限、多租户、发布、评测、审计**全部要自己建**。没有 3–5 人以上的平台团队，不要轻易走这条路。

## 5. 同一个需求，三套实现

**需求**：企业知识库问答；当用户问题命中"退款/投诉"意图时，调用工单 API 创建工单；创建前必须人工确认。

### 5.1 Coze 实现

1. 建**知识库**：上传产品文档/FAQ，配置分段与召回条数；
2. 建 **Workflow**：开始 → 意图识别（LLM 节点）→ 条件分支；
   - 普通问题：知识库检索 → LLM 生成（要求引用）→ 结束；
   - 退款/投诉：调用**自定义插件**（把工单 API 封装成插件）→ 返回工单号；
3. 配**变量与卡片**，把工单号渲染成可点击卡片；
4. 发布到 Web/渠道，配置权限与配额。

- **优点**：半天到两天可完成；运营可自己改提示词与分支。
- **注意**：人工确认节点、复杂重试、状态恢复能力有限，**写操作务必在企业 API 侧做二次校验与幂等**。

### 5.2 Dify 实现

1. **知识库**：创建数据集，配置分段规则、索引方式、召回与重排；
2. **Chatflow**：开始 → LLM 意图分类 → 条件分支；
   - 普通问答：知识库检索节点 → LLM 节点（引用）→ 回答；
   - 工单：**自定义工具**（OpenAPI Schema 导入）→ HTTP 请求节点 → 变量提取；
3. **人工确认**：用"人工介入/审批"类节点（按当前版本能力），或把确认动作回传给业务前端；
4. **发布**：发布为 Web App / API，接入企业 SSO 与网关；
5. **观测**：开启日志与标注，建立评测集回归。

- **优点**：自托管、数据不出域、有完整应用管理；业务与研发都能上手。
- **注意**：大版本升级有 breaking change，**升级前必须备份并先在测试环境跑通**。

### 5.3 LangGraph 实现（代码骨架）

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

class State(TypedDict, total=False):
    question: str
    docs: list[str]
    intent: str
    answer: str
    ticket_id: str

def classify(state: State) -> State:
    # 调用模型做意图分类：normal / refund / complaint
    return {"intent": "refund" if "退款" in state["question"] else "normal"}

def retrieve(state: State) -> State:
    return {"docs": ["...检索到的片段..."]}

def answer(state: State) -> State:
    return {"answer": "根据文档……（附引用）"}

def create_ticket(state: State) -> State:
    # 高风险写操作：先中断，等待人工确认
    decision = interrupt({"action": "create_ticket", "question": state["question"]})
    if decision.get("approved"):
        return {"ticket_id": "T-2026-0001"}   # 实际调用工单 API（需幂等键）
    return {"answer": "已取消创建工单"}

g = StateGraph(State)
g.add_node("classify", classify)
g.add_node("retrieve", retrieve)
g.add_node("answer", answer)
g.add_node("ticket", create_ticket)
g.add_edge(START, "classify")
g.add_conditional_edges(
    "classify",
    lambda s: "ticket" if s["intent"] in ("refund", "complaint") else "retrieve",
    {"ticket": "ticket", "retrieve": "retrieve"},
)
g.add_edge("retrieve", "answer")
g.add_edge("answer", END)
g.add_edge("ticket", END)

app = g.compile(checkpointer=MemorySaver())   # 生产环境换成持久化 checkpointer
# 运行：app.invoke({"question": "我要退款"}, config={"configurable": {"thread_id": "u-1"}})
# 恢复：人工确认后用同一 thread_id 继续执行
```

- **优点**：状态、分支、人工中断、断点恢复都可控；可接任意工具与模型。
- **代价**：检索、评测、权限、UI、发布全部要自己补。

> 骨架仅示意流程，实际使用时请以当前 LangGraph 版本文档为准（`interrupt`、checkpointer 的 API 在小版本间有演进）。

## 6. 企业落地坑（按平台）

### 6.1 Coze / 扣子

| 坑 | 表现 | 应对 |
|---|---|---|
| **平台锁定** | 业务逻辑长在平台里，想迁走要重写 | 业务规则与写操作放企业 API；平台只做交互与轻编排 |
| **数据出域** | 文档/对话进了第三方云 | 敏感数据先脱敏；或改用可自托管方案 |
| **私有化能力差异** | SaaS 有的功能，私有化版本没有 | 立项前用**目标版本**做 POC，不要看 SaaS 演示 |
| **插件权限与计费** | 插件调用超限、第三方插件不可控 | 自建插件 + 配额 + 审计；关键插件不要依赖第三方 |
| **复杂逻辑上限** | 多层循环、长任务、状态恢复做不了 | 复杂链路拆到后端服务 |
| **版本与灰度弱** | 改完直接生效，出问题难回滚 | 保留旧版本副本；发布前用测试 Bot 验证 |

### 6.2 Dify

| 坑 | 表现 | 应对 |
|---|---|---|
| **升级 breaking change** | 大版本升级后工作流/插件失效 | 锁版本；升级前备份数据库与对象存储；先在测试环境跑评测集 |
| **许可附加条件** | 做多租户 SaaS 或去 logo 时踩线 | 落地前读 LICENSE；商用/多租户咨询官方授权 |
| **插件质量参差** | 社区插件不稳定、无维护 | 关键工具自研；插件做版本锁定与超时/重试 |
| **大知识库检索性能** | 文档量大后召回慢、效果差 | 分段策略 + 混合检索 + 重排；按业务分库；定期评测 |
| **多租户与权限** | 社区版隔离能力有限 | 用命名空间/独立实例隔离；或使用企业版能力 |
| **备份与恢复** | 只备份了数据库，漏了文件/向量库 | 数据库 + 对象存储 + 向量库 + 配置**一起备份**，并做恢复演练 |

### 6.3 LangChain / LangGraph

| 坑 | 表现 | 应对 |
|---|---|---|
| **抽象层过厚** | 出问题不知道是 Prompt、解析器还是模型 | 关键链路自己写薄封装；打开 LangSmith/OTel Trace |
| **API 迭代快** | 升级后代码跑不通 | **锁版本**（requirements 精确到 patch）；升级前跑回归 |
| **过度工程** | 简单问答也上多 Agent、多工具 | 单 Agent 优先；能用一个链解决就不要上图 |
| **没有平台能力** | 缺 UI、权限、多租户、发布 | 要么自建，要么用 Dify 做外层 |
| **成本失控** | 循环 + 重试 + 长上下文烧钱 | 最大步数/最大 token/最大成本三件套 |
| **不可观测** | 线上答错无法复现 | 全量记录 trajectory + 版本号 + 模型参数 |

### 6.4 三者共性坑

1. **RAG 效果不由平台决定**，由**数据质量、分段策略、检索与重排、评测集**决定；
2. **Agent 复杂度要克制**——单 Agent 能搞定就不要多 Agent（见第 20 章「Communication is complexity」）；
3. **没有评测集就不要上线**，至少 30 条 Golden + 20 条边界 + 20 条对抗；
4. **成本从第一天就要计量**（token、调用次数、单任务成本），否则规模化后无法优化；
5. **写操作必须幂等 + 审批 + 审计**，平台不替你做这些。

## 7. 30 分钟对比实验（建议动手做一遍）

**统一任务**：同一份 20 页产品手册 + 5 个问题（3 个可答、1 个需跨段推理、1 个文档中没有），在三个平台各实现一遍。

**记录 6 个指标：**

| 指标 | 说明 | 权重 |
|---|---|---|
| 搭建耗时 | 从零到可回答问题 | 20% |
| 引用准确率 | 5 个问题中引用正确的比例 | 25% |
| 首字延迟 | P50 TTFT | 15% |
| 单次成本 | 每次问答的 token 成本 | 15% |
| 改一条业务规则的耗时 | 例如"命中退款时创建工单" | 15% |
| 迁移/导出难度 | 能否导出 Prompt、流程、知识库 | 10% |

**评分表模板：**

| 平台 | 搭建耗时 | 引用准确率 | TTFT | 单次成本 | 改规则耗时 | 迁移难度 | 总分 |
|---|---|---|---|---|---|---|---|
| Coze | | | | | | | |
| Dify | | | | | | | |
| LangGraph | | | | | | | |

> 经验结论（供参考，仍需自己验证）：**Coze 在"搭建耗时"上通常大幅领先；Dify 在"综合平衡"上最好；LangGraph 在"改规则/复杂逻辑"上最强，但搭建与迁移成本最高。**

## 8. 版本与事实基线（2026-10-20 实测）

| 项目 | 仓库 / 入口 | 星标 | 许可 | 最新版本 | 语言 |
|---|---|---:|---|---|---|
| Coze Studio | `coze-dev/coze-studio` | ≈21.7k | Apache-2.0 | v0.5.1 | TypeScript |
| Coze Loop | `coze-dev/coze-loop` | ≈5.8k | Apache-2.0 | v1.5.1 | Go |
| Dify | `langgenius/dify` | ≈159.0k | 基于 Apache-2.0 的附加条件许可 | 1.17.1 | Python |
| LangChain | `langchain-ai/langchain` | ≈148.1k | MIT | langchain-core 1.6.12 | Python |
| LangGraph | `langchain-ai/langgraph` | ≈43.5k | MIT | cli 0.4.37 | Python |
| n8n（参考） | `n8n-io/n8n` | ≈208.1k | Sustainable Use License（fair-code） | 2.43.8 | TypeScript |
| RAGFlow（参考） | `infiniflow/ragflow` | ≈92.5k | Apache-2.0 | v1.0.0-rc2 | Go |
| FastGPT（参考） | `labring/FastGPT` | ≈29.9k | 附加条件许可 | v4.17.2 | TypeScript |

> 星标与版本为快照，会随时间变化；引用时请注明查询日期。

## 9. 参考链接（2026-10-20 实测可访问）

| 主题 | 链接 |
|---|---|
| Coze 中国站（扣子） | <https://www.coze.cn/> |
| Coze 国际站 | <https://www.coze.com/> |
| Coze 文档 | <https://docs.coze.cn/> |
| Coze Studio（开源版） | <https://github.com/coze-dev/coze-studio> |
| Coze Loop（评测与观测） | <https://github.com/coze-dev/coze-loop> |
| Dify 官网 | <https://dify.ai/> |
| Dify 文档 | <https://docs.dify.ai/> |
| Dify 仓库 | <https://github.com/langgenius/dify> |
| LangChain 官网 | <https://www.langchain.com/> |
| LangChain 文档 | <https://docs.langchain.com/> |
| LangChain Python 文档 | <https://python.langchain.com/> |
| LangChain 仓库 | <https://github.com/langchain-ai/langchain> |
| LangGraph 仓库 | <https://github.com/langchain-ai/langgraph> |
| LangSmith 文档 | <https://docs.smith.langchain.com/> |
| n8n（参考：工作流自动化） | <https://n8n.io/> |
| n8n 仓库 | <https://github.com/n8n-io/n8n> |

> 关于"LangChain 中文社区"：中文资料更新速度通常落后于官方文档，**接口与参数以官方英文文档为准**，中文内容只用于建立直觉。

## 10. 与既有章节的衔接

| 想补什么 | 看哪章 |
|---|---|
| Agent Harness 的职责、组件与八个递进实验 | 第 02 章 AI Harness 企业落地教程 |
| Agent 身份、权限、Guardrail 三态授权 | 第 18 章 AI Native 研发范式 |
| 薄 Loop + 厚 Control Plane、WAL 恢复、Fail Fast | 第 20 章 Harness 横向对比与最新实现范式 |
| 推理服务、vLLM、路由、多副本、K8s 落地 | 第 04 章 AI Infra 企业平台教程 |
| 统一 AI Gateway / 模型路由 / Agent Runtime 的架构设计 | 第 22 章 AI 平台架构师岗位与面试 |
| RAG 评测、企业落地踩坑 | 第 10 章 企业落地常见坑与注意事项 |
| 毕业项目（含 RAG + Agent + 审批 + 评测） | 第 06 章 毕业项目 SOP 与验收 |