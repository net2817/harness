# Harness 横向对比与最新实现范式（Pi / Aider · 2026）

> **本章素材**：InfoQ 原文《人人都能整个"自己的 DeepSeek Harness"，那我们为啥还在给 Claude Code 们充会员？》（2026-08-31，作者 Tina；受访者：TiDB 唐刘、腾讯研究院茹炳晟、Floatboat 架构师 Remy、字节 Trae 天猪）+ Pi / Aider 官方仓库实测数据（截至 2026-10-11）。
> **本章回答三个问题**：① 这篇文章到底说了什么？② Pi 和 Aider 这类 Harness 怎么比、怎么选？③ 「按最新方式实现一个 Harness」到底该长什么样？

## 1. 文章讲了什么（核心论点）

| # | 论点 | 原文依据 |
|---|---|---|
| 1 | **模型在日常编程任务上已拉不开差距** | Amp 联创 Thorsten Ball「模型已经死了」；OpenCode 联创 Dax Raad「用哪个都一样」；Pi 作者 Mario Zechner 认为新版本甚至可能能力倒退（厂商难保旧能力不退化） |
| 2 | **竞争从"模型层"下沉到"Harness 层"** | 厂商推自家 Harness，因为「Harness 是唯一能控制的部分，至少能把变化锁住」 |
| 3 | **Harness 正在趋同，但趋同不是终点** | 大厂底层路径越来越相似：Agent Loop 读写上下文、调工具、反复执行、用测试和权限兜底 |
| 4 | **最内层 Agent Loop 只有几百行** | Ralph Loop 作者 Geoffrey Huntley：「重建 Cursor 不过 300 行代码的一个 while 循环」；Amp 用 315 行 Go 写出能在终端读、搜、改文件的 Coding Agent |
| 5 | **真正拉开差距的是 Loop 之外的系统** | TiDB「**薄 Agent Loop，厚 Control Plane**」；状态持久化、权限收口、副作用控制、失败恢复、可审计 |
| 6 | **长程稳定性是下一代分水岭** | Floatboat 实测：同一模型，长程任务上 **Harness 多贡献 23%**；难点是依赖链深度、状态跨越时间与工具数、目标开放度、操作可逆性、错误反馈轮数 |
| 7 | **多 Agent 是例外，不是默认** | 「Communication is complexity」；「真正好的多 Agent 系统，反而可能看起来非常安静」；只有两个场景值得引入多 Agent：缓解上下文压力、交叉验证与发散探索 |
| 8 | **Coding 只是 Harness 最早跑通的场景** | ChatGPT Work 与 Codex「用的是同一套 Harness」；腾讯 CodeBuddy→WorkBuddy、阿里 Qoder/Qoder Work、字节 Trae IDE/Trae Work 都是一面两体 |

**最有工程价值的三句话：**

```
薄 Agent Loop，厚 Control Plane          —— TiDB 唐刘
Retry is dangerous. Fail fast is underrated. —— TiDB 唐刘
状态可以丢，但日志不能丢，丢了日志就丢了真相。 —— Pi Harness v2（WAL 思路）
```

## 2. 一个 Harness 由什么组成

```
┌──────────────────────────────────────────────────────────────┐
│  Control Plane（厚）                                          │
│  权限 / 沙箱 · 状态持久化(WAL) · Checkpoint·Rollback·Failover │
│  任务编排 · 配额 · 多租户隔离 · 审计 · 确定性验证 · 灰度回滚   │
└───────────────────────────┬──────────────────────────────────┘
                            │  只暴露少量稳定接口
┌───────────────────────────┴──────────────────────────────────┐
│  Agent Loop（薄，约 200 行量级）                               │
│  读上下文 → 规划 → 调工具 → 写日志，循环                       │
└───────────────────────────┬──────────────────────────────────┘
                            │
   Tool 层：Planner / Coder / Reviewer / Search / Edit / Shell / MCP
```

**为什么 Loop 要薄**：模型协议、Tool Calling、Streaming、Reasoning 变化最快、也最容易被 LLM 厂商和云厂商标准化 —— 在这一层内卷投入产出比最低。**为什么 Control Plane 要厚**：状态持久化、权限收口、副作用边界、失败恢复、结果可证明、故障可审计，是二十年分布式系统反复证明过的、必须自己掌握的部分。

> 关键收益：**换模型、换 Agent Core 不必推倒重来**。TiDB 团队最初用 OpenCode，后换成 Pi，「不管上面的 Agent 怎么换，下面的 Sandbox、权限、状态和控制面都不需要跟着重写」。

## 3. Pi vs Aider 对比

### 3.1 事实卡（截至 2026-10-11，仓库实测）

| 项目 | **Pi** | **Aider** |
|---|---|---|
| 仓库 | `earendil-works/pi`（原 `badlogic/pi-mono`） | `Aider-AI/aider` |
| 发起人 | Mario Zechner（奥地利）个人发起 | Paul Gauthier（加拿大）一人发起 |
| 首次发布 | 2025-08-09 | 2023-05-09 |
| 语言 / 许可 | TypeScript / MIT | Python / Apache-2.0 |
| 星标 | **≈114.2k**（fork ≈14.5k） | **≈49.5k** |
| 最近活跃 | 2026-10-11 | 2026-05-22 |
| 官方定位 | "a minimal, extensible **agent harness** that you can make your own" | "AI **pair programming** in your terminal" |

### 3.2 设计哲学差异（这是选型的分水岭）

| 维度 | **Pi：可改造的 Harness 框架** | **Aider：终端里的结对编程工具** |
|---|---|---|
| 核心隐喻 | 给你一副**骨架**，自己长成需要的形状 | 给你一把**好用的工具**，开箱即用 |
| 默认复杂度 | **刻意极简**：官方明确"skips features like sub-agents and plan mode" | **功能齐全**：repo map、多种编辑格式、自动提交、lint/test 循环 |
| 扩展方式 | **代码级**：extensions / skills / prompt templates / themes，打包成 Pi packages 走 npm 或 git 分发；另有 TypeScript SDK | **配置级**：YAML 配置、`/` 命令、脚本、模型别名 |
| 上手方式 | `curl -fsSL https://pi.dev/install.sh \| sh`（或 npm `@earendil-works/pi-coding-agent`、Nix） | `pip install aider-install && aider-install`（Python 生态） |
| 使用形态 | 交互式 TUI、print/JSON 模式、**RPC**、TypeScript SDK 四种 | 交互式 REPL、`--message` 单次、watch 模式 |
| 与 Git 的关系 | 由扩展/工具决定（默认不绑定） | **Git 原生**：每次改动自动生成提交，回滚 = revert |
| 上下文策略 | 交给扩展与 Skills | **repo map**：用 tree-sitter 建代码图，按 token 预算自动挑选相关代码 |
| 编辑格式 | 由扩展决定 | 多种可选：diff / whole / udiff / editor-diff 等 |
| 失败恢复 | **Harness v2：执行状态入 WAL**（操作意图、执行步骤、Tool 状态、消息队列全部落盘，按 Operation Log 判断安全恢复点） | 依赖 Git 提交历史与 `/undo` |
| 生态 | pi-skills（2.6k★）、pi-diff-review（314★）、pi-subagent（178★）、pi-telegram、pi-terminal-bench、durable-bench | 插件较少，但模型接入面最广（OpenRouter / Anthropic / OpenAI / DeepSeek / 本地 Ollama…） |
| 最适合 | **想自己搭/改 Harness 的平台与 Infra 团队**；要把自己的 Control Plane（权限、审计、配额）挂上去 | **想立刻在终端里改代码的开发者**；要天然可审计、可回滚的增量修改 |

### 3.3 一段话选型

- **要做"自己的 Harness"** → 选 **Pi**：它把 Loop 做薄、把扩展点做齐，允许你把自己的 Control Plane（权限/沙箱/持久状态/审计）接上去，并且换模型换 Core 不用重写底座。
- **要马上提效、要审计与回滚** → 选 **Aider**：Git 原生 + repo map，在存量代码库上做增量修改最顺手。
- **要跑生产级长程任务** → 两者都需要**外挂** Control Plane；差别在于 Pi 的 SDK/扩展点更适合"自己造"，Aider 的 Git 工作流更适合"直接用"。

## 4. 更广的 Harness 版图（2026）

| 项目 | 定位 | 关键特征 |
|---|---|---|
| **Claude Code**（Anthropic） | 产品化 Harness | Dynamic Workflows：给目标，自己拆任务、调度数百子 Agent 搜索/编码/验证/汇总 |
| **Codex**（OpenAI） | 产品化 Harness | 与 ChatGPT Work **共享同一套 Harness**，只是调用的工具不同 |
| **OpenCode** | 开源 Coding Agent | TiDB 团队最初使用的 Agent Core |
| **Cline / Cursor / Windsurf** | 2022–2023 期产物 | 4000 Token 上下文时代，用工具调用 / MCP / RAG 管理上下文的产物 |
| **Reasonix** | 面向 DeepSeek 优化 | 游戏引擎开发者 YHH 个人发起，后发展为数万 Star 社区项目 |
| **Amp**（Thorsten Ball） | 极简 Agent | 315 行 Go 实现终端读/搜/改文件 |
| **Gas Town**（Steve Yegge） | 多 Agent 编排 | 一人持续管理 20–30 个并发 Coding Agent（本地单机） |
| **Floatboat** | 通用工作 Agent | 全栈自研 Runtime / Agent Loop / Tools / Infra + 自进化系统 FloatSail；原生文件协议、GUI-Agent 双向协议 |
| **Pi / Aider** | 个人起家 → 社区 | 见第 3 节 |

## 5. 「最新的实现方式」：八条铁律

### 铁律 1 —— 薄 Agent Loop，厚 Control Plane
Loop 只做四件事；权限、沙箱、持久化、恢复、审计全部在 Loop 之外。**判断标准**：如果换一个模型 / 换一个 Agent Core 需要改 Control Plane，说明分层错了。

### 铁律 2 —— 执行状态持久化：WAL / Operation Log
Pi 的 Harness v2 把**操作意图、执行步骤、Tool 状态、消息队列**全部落盘，进程崩溃后按 **Operation Log** 判断"安全恢复点"。这与数据库 **WAL** 完全同构：**先写日志，再改状态；状态可以丢，日志不能丢。**

### 铁律 3 —— Fail Fast 优于 Retry
「Retry is dangerous. Fail fast is underrated.」推理期一个不起眼的偏差，如果在第 11–50 步还被当作事实继续消费，最后你根本不知道从哪一步开始错的。做法：**错误计数 + 连续错误阈值 + 立即停止**，而不是重试放大。但 Fail Fast 必须搭配两件事：**限制错误传播**、**从最近一个可信状态恢复**。

### 铁律 4 —— 确定性验证（外部不变量）
Agent 说"我修好了"没有意义。必须由**外部不变量**证明：编译通过、测试通过、类型正确。Coding Harness 要与 CI 打通，覆盖 测试生成 → 测试执行 → 结果分析 → 错误反馈 → 代码修正。**并且验证结果要三态**：`PASS / BLOCKED / UNKNOWN`（UNKNOWN 不默认放行，升级为人工或异步复核）。

### 铁律 5 —— 长程稳定性是分水岭
「能用」和「能连续跑 50 小时还知道自己干过什么」是两回事。长程难度不看步数，看**依赖链深度、状态跨越的时间与工具数、目标开放度、操作可逆性、错误被发现前要经过多少轮反馈**。

### 铁律 6 —— 多 Agent 是例外，不是默认
「Communication is complexity.」十个组件频繁通信的系统大概率难 Debug、性能也差。**只要单 Agent 能搞定就不要引入多 Agent** —— 复杂度不会消失，只会转移。值得付出成本的两个场景：① 缓解上下文压力；② 交叉验证与发散探索。

### 铁律 7 —— 自进化必须受控闭环
`发现问题 → 生成改动 → 隔离评测 → 门槛校验（质量/成本/时延/安全）→ 灰度 → 保留回滚`。没有版本管理和可观测性，自进化只是在积累技术债。Human-Centric：**人在环中 → 人在环上**（局部优化自动完成，人管目标、边界、例外和系统级治理）。

### 铁律 8 —— 从命令式编排走向声明式目标
模型越强，一部分显式编排必然消失 —— 很像数据库：早期要告诉它"怎么 Join、从哪张表开始"，Optimizer 变强后，人只说"我要什么"。**但边界不能因为"上层更聪明"就消失**：SQL / Optimizer 可以越来越聪明，Transaction / Privilege / Durability 必须稳定。

## 6. 参考实现：按最新范式写一个可运行的 Harness

> 完整可运行代码：**[examples/harness_wal.py](examples/harness_wal.py)**（单文件、无第三方依赖，`python harness_wal.py` 即可跑通 5 个演示）。
> 它把上面八条铁律中的 1/2/3/4/7 落成了可执行代码。

### 6.1 结构

```
harness_wal.py
├── OpLog          WAL：追加写 + fsync + 哈希链，可回放校验
├── Workspace      持久状态：由 WAL 回放重建，可快照 / 可回滚
├── Policy         厚 Control Plane：工具白名单 + 路径沙箱
├── Guardrail      确定性验证：PASS / BLOCKED / UNKNOWN + evidence
├── Harness        薄 Loop：读上下文 → 规划 → 调工具 → 写日志
│   └── recovery_point()   崩溃后找"安全恢复点"
└── SelfEvolutionGate      受控自进化门禁（质量/成本/时延）
```

### 6.2 WAL：状态可以丢，日志不能丢

```python
class OpLog:
    """先写日志再改状态；每条记录带 prev 指针 + digest，形成哈希链。"""
    def append(self, kind: str, payload):
        self._seq += 1
        rec = {"seq": self._seq, "ts": round(time.time(), 3),
               "kind": kind, "payload": payload, "prev": self._prev}
        rec["digest"] = _digest(rec)
        self._fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._fh.flush()
        os.fsync(self._fh.fileno())      # 关键：进程崩溃也不丢日志
        self._prev = rec["digest"]
        return rec

    @staticmethod
    def replay(path):
        """回放 + 校验哈希链；任何不一致都抛 Corruption，绝不静默继续。"""
        records, prev = [], "genesis"
        for lineno, line in enumerate(open(path, encoding="utf-8"), 1):
            if not line.strip():
                continue
            rec = json.loads(line)
            digest = rec.pop("digest", None)
            if digest != _digest(rec):
                raise Corruption(f"第 {lineno} 行内容与摘要不符（日志被改写）")
            if rec["prev"] != prev:
                raise Corruption(f"第 {lineno} 行哈希链断裂（日志被截断或重排）")
            prev = digest
            rec["digest"] = digest
            records.append(rec)
        return records
```

### 6.3 安全恢复点：崩溃后怎么知道从哪继续

```python
@staticmethod
def recovery_point(records):
    """最后一个 tool.call 若没有配对的 tool.result，就是崩溃点。

    语义：该操作的副作用结果『未知』—— 既不能当成功继续，也不能当失败重试。
    正确处理 = 回滚到最近 checkpoint，让操作变成幂等的重放。
    """
    results = {r["payload"]["call_id"] for r in records if r["kind"] == "tool.result"}
    last_step, pending = 0, None
    for r in records:
        if r["kind"] in ("tool.result", "tool.error", "loop.finish"):
            last_step = max(last_step, r["payload"].get("step", 0) + 1)
        if r["kind"] == "tool.call" and r["payload"]["call_id"] not in results:
            pending = r["payload"]
    return last_step, pending
```

### 6.4 薄 Loop：四步循环 + 两侧护栏

```python
for step in range(start_step, self.max_steps):
    plan = self.planner(ctx)                       # ① 规划（模型决策）
    tool, args = plan["tool"], plan.get("args", {})

    ok, why = self.policy.check_tool(tool)         # ② Control Plane 前置
    if ok and "path" in args:
        ok, why = self.policy.check_path(args["path"])
    if not ok:
        self.log.append("policy.deny", {"tool": tool, "reason": why, "step": step})
        if self._count_error(step, why) == "fail_fast":
            break                                  # 铁律 3：不 Retry 放大

    call_id = uuid.uuid4().hex[:8]
    self.log.append("tool.call", {"call_id": call_id, "tool": tool, "args": args})  # ③ 先写日志
    try:
        result = self.tools[tool].fn(**args)       #    再执行副作用
    except Exception as exc:
        self.log.append("tool.error", {"call_id": call_id, "error": repr(exc)})
        if self._count_error(step, repr(exc)) == "fail_fast":
            break
        continue

    v = self.guardrail.check(tool, args, result)   # ④ Control Plane 后置：确定性验证
    self.log.append("guard.verdict", {"call_id": call_id, "state": v.state, "evidence": v.evidence})
    if v.state == "BLOCKED":
        self.log.append("tool.result", {"call_id": call_id, "accepted": False})
        if self._count_error(step, "blocked") == "fail_fast":
            break
        continue

    self.log.append("tool.result", {"call_id": call_id, "accepted": True, "result": result})
    self.workspace.apply(self._as_state_kind(tool), {**args, **(result or {})})
    self.consecutive_errors = 0
    if step and step % self.checkpoint_every == 0:
        self.checkpoint()                          # 定期落盘快照 → 可回滚点
```

### 6.5 实测运行输出

```text
Demo 1：正常执行 —— 薄 Loop + WAL + Checkpoint
  [checkpoint] 已落盘：3 个文件
状态: finished      文件: ['docs/design.md', 'src/app.py', 'src/util.py']
WAL 记录数: 15；最后一条: loop.finish

Demo 2：崩溃后按 Operation Log 恢复
>> 模拟崩溃：def456 已发起但未记录结果
恢复后工作区文件: ['committed.txt']
→ def456 被判定为「未知结果」，回滚到最近 checkpoint；committed.txt 保留

Demo 3：权限拒绝 + Fail Fast
  [error] policy denied: 路径越出沙箱：../../etc/passwd（第 1 次）
  [FAIL FAST] 连续 2 次错误，立即停止
状态: fail_fast      工作区文件: []（never.txt 未产生 → Loop 已停止）

Demo 4：Guardrail 三态判定
  write_file  -> PASS     {"bytes": 8}
  write_file  -> UNKNOWN  {"reason": "内容为空，需人工确认"}
  write_file  -> BLOCKED  {"reason": "写入超过大小上限", "bytes": 300000}
  run_tests   -> BLOCKED  {"reason": "测试未通过", "failed": ["test_add"]}

Demo 5：受控自进化门禁
  候选 {'quality': 0.96, 'cost': 1.05, 'latency': 1.1} -> 准入：进入灰度（保留一键回滚）
  候选 {'quality': 0.91, ...}                          -> 拒绝：质量未达标
  候选 {'quality': 0.97, 'cost': 1.3, ...}             -> 拒绝：成本上升超阈值
```

### 6.6 从这个骨架到生产，还差什么

| 缺口 | 生产做法 |
|---|---|
| 单机日志 | 换成分布式 WAL（如 etcd / Postgres / 对象存储 + 版本号），支持多副本 |
| 脚本化 planner | 接真实模型：统一 LLM API + Tool Calling + Streaming |
| 本地文件沙箱 | 换成容器 / 微虚拟机（Firecracker）+ 文件系统快照 |
| 静态权限 | 接 IAM / ABAC，动作分 `allow / deny / **challenge**` 三态 |
| 简单 Guardrail | 接 CI：测试生成 + 执行 + 结果分析 + 错误反馈闭环 |
| 无并发控制 | 加"单写者"选主、任务幂等键、配额与多租户隔离 |
| 无观测 | OpenTelemetry（GenAI 语义约定）+ 轨迹（trajectory）分析 |

## 7. 落地清单

- [ ] Loop 与 Control Plane **分层清晰**：换模型 / 换 Core 不需要改 Control Plane；
- [ ] 所有副作用操作**先写日志、后执行**，日志带哈希链与 fsync；
- [ ] 崩溃恢复走 **Operation Log + 安全恢复点**，不做"结果未知就重试"；
- [ ] 连续错误达阈值**立即 Fail Fast**，并限制错误向上下文传播；
- [ ] 每个工具都有**确定性验证器**，验证结果三态且带 evidence；
- [ ] **Checkpoint / Rollback** 可一键执行，且有演练记录；
- [ ] 多 Agent 只在"上下文压力 / 交叉验证"两类场景启用，拓扑尽量简单；
- [ ] 自进化走**隔离评测 → 门槛 → 灰度 → 保留回滚**，全程可观测可溯源；
- [ ] 全链路可观测：模型调用、工具调用、Guardrail 判定、恢复动作均可查询。

## 8. 与既有章节的衔接

| 想补什么 | 看哪章 |
|---|---|
| Agent Harness 的职责与四大能力 | 第 02 章 AI Harness 企业落地教程 |
| Agent 身份、权限、Guardrail 三态授权 | 第 18 章 AI Native 研发范式 |
| 推理服务可靠性、MTTR、故障演练 | 第 19 章 大模型推理服务可靠性工程师 |
| GPU / NCCL / 集群故障处理 | 第 07 / 08 章 |
| 推理引擎（vLLM/SGLang）与性能调优 | 第 04 章 AI Infra |
| 企业落地常见坑 | 第 10 章 |

> **一句话总结本章**：模型会持续被替换，Harness 也会持续趋同；能穿越这两次替换的，只有你**自己掌握的那层 Control Plane** —— 状态、权限、副作用边界和恢复能力。