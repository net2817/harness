# FastAPI × MCP × React：AI 应用与 AIGC 全栈集成

> 本章把三件事连成一条完整链路：**FastAPI 做后端、MCP 做工具协议、React 做前端**，并在此基础上落地 **AIGC（图像/视频生成）** 场景。
>
> 适用人群：要把 Agent/LLM 能力做成"可上线产品"的工程师；只做过 Demo、没处理过流式/取消/长任务/进度回传的同学重点看第 2、4、5 节。

## 1. 一条请求怎么走

```
React（浏览器）
   │  ① POST /api/chat/stream（fetch + ReadableStream）
   ▼
FastAPI（无状态 API 层）
   │  ② 鉴权 / 限流 / 参数校验（Pydantic）
   │  ③ 调用 Agent 或 MCP Client
   ▼
MCP Server（工具层）
   │  ④ tools/list、tools/call（Streamable HTTP 或 stdio）
   ▼
模型服务 / 内部系统 / GPU 任务
   │  ⑤ 结果或进度
   ▼
FastAPI  →  SSE 事件流  →  React 增量渲染
```

**AIGC 是另一条路径**：因为图像/视频生成是**秒级到分钟级**的任务，不能占着 HTTP 连接同步等待，必须走 **提交任务 → 查询/订阅进度 → 取产物** 的异步模式（见第 5 节）。

## 2. FastAPI 侧：把 AI 服务写对

### 2.1 四个必备设计

| 设计 | 要点 | 常见错误 |
|---|---|---|
| **契约先行** | 请求/响应/错误全部用 Pydantic 建模，生成 OpenAPI | 用 `dict` 裸传，前端字段对不上 |
| **全异步** | `async def` + 异步客户端（httpx/异步 DB 驱动） | 在 async 里写同步 `requests`/`time.sleep`，阻塞事件循环 |
| **流式优先** | LLM 输出用 SSE，边生成边返回 | 等模型全部生成完再一次性返回，TTFT 极差 |
| **可追踪** | 每个请求生成 `request_id`，贯穿日志/Trace/计费 | 出问题无法把前端请求和后端调用对上 |

### 2.2 流式 Chat API（代码骨架）

```python
import asyncio, json, uuid
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

app = FastAPI(title="AI Platform API")

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=32_000)
    session_id: str | None = None

async def fake_llm(message: str):
    for ch in f"收到：{message}":
        await asyncio.sleep(0.02)
        yield ch

async def event_stream(req: ChatRequest, request: Request):
    rid = uuid.uuid4().hex
    yield f"event: meta\ndata: {json.dumps({'request_id': rid})}\n\n"
    try:
        async for token in fake_llm(req.message):
            if await request.is_disconnected():      # 客户端断开 → 及时停止，省算力
                break
            yield f"event: token\ndata: {json.dumps({'text': token}, ensure_ascii=False)}\n\n"
        yield "event: done\ndata: {}\n\n"
    except Exception as exc:
        payload = json.dumps({"message": str(exc)}, ensure_ascii=False)
        yield f"event: error\ndata: {payload}\n\n"

@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest, request: Request):
    return StreamingResponse(
        event_stream(req, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",   # 关键：关闭 Nginx 缓冲，否则前端会"憋一大段"
        },
    )
```

**三个容易忽略的点：**

1. **`X-Accel-Buffering: no`** —— 不关掉反向代理缓冲，SSE 会变成"最后一次性吐出"；
2. **`request.is_disconnected()`** —— 用户关页面/点停止后，后端要尽快取消模型调用，否则白烧 GPU；
3. **心跳** —— 长任务建议每 15–30 秒发一个 `: ping` 注释行，防止中间设备掐断空闲连接。

### 2.3 生产必备能力

| 能力 | 做法 |
|---|---|
| **鉴权** | Bearer Token / OIDC / 网关统一鉴权，业务层拿 `tenant_id`、`user_id` |
| **限流** | 按租户 + 接口 + 模型三维度；令牌桶 + 并发数双控 |
| **幂等** | 写操作带 `Idempotency-Key`，服务端去重并返回同一结果 |
| **取消** | 前端 `AbortController` → 后端 `is_disconnected()` → 取消上游调用 |
| **超时** | 分连接超时、读超时、总超时；流式场景要单独设"首字节超时"和"总时长上限" |
| **错误码** | 统一错误结构 `{code, message, request_id, retryable}`，不要抛裸 500 |
| **CORS** | 只放行可信域名；带 Cookie 时不能用 `*` |
| **可观测** | 每个请求记录：模型、token 数、TTFT、总耗时、错误码、成本 |

## 3. MCP 集成

### 3.1 MCP 是什么（30 秒版）

**MCP（Model Context Protocol）** 是"模型 ↔ 工具/数据"的开放协议。三个角色：

```
Host（宿主，如 IDE/Agent 应用）
  └─ Client（协议客户端）
        └─ Server（工具/资源提供方）
```

Server 暴露三类能力：

| 能力 | 用途 | 例子 |
|---|---|---|
| **Tools** | 可被模型调用的函数 | 查 GPU 使用率、创建工单、查数据库 |
| **Resources** | 可被读取的数据 | 文件、配置、文档 |
| **Prompts** | 预定义提示模板 | 故障复盘模板、代码评审模板 |

两种传输方式：

| 传输 | 适用 | 特点 |
|---|---|---|
| **stdio** | 本地进程、IDE 插件 | 简单、无网络暴露；但只能本机 |
| **Streamable HTTP** | 远程服务、生产部署 | 可跨网络、可做鉴权与网关；**生产首选** |

> 注意区分两个包：`mcp`（官方 Python SDK，内含 `mcp.server.fastmcp.FastMCP`）与独立的 `fastmcp`（社区增强版）。本文示例用官方 SDK 的 API；两者 API 相近但不完全等价，**以当前版本文档为准**。

### 3.2 最小 MCP Server

```python
# mcp_server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ops-tools")

@mcp.tool()
def get_gpu_usage(node: str) -> dict:
    """查询指定节点的 GPU 使用率。"""
    return {"node": node, "gpu_util": 87, "mem_used_gb": 61}

@mcp.tool()
def create_ticket(title: str, severity: str = "P2") -> dict:
    """创建工单。写操作，需要审批与审计。"""
    return {"ticket_id": "T-2026-0001", "title": title, "severity": severity}

if __name__ == "__main__":
    mcp.run(transport="streamable-http")   # 默认监听 127.0.0.1:8000/mcp
```

**工具设计的三条原则**（直接决定 Agent 好不好用）：

1. **一个工具只做一件事**，名字动词开头（`get_gpu_usage` 而不是 `gpu`）；
2. **参数少而明确**，用类型注解 + 默认值 + 枚举，避免"自由文本参数"；
3. **返回结构化、可截断**，大结果要分页/摘要，别把 10MB JSON 塞回模型。

### 3.3 两种集成方式

#### 方式 A：独立 MCP 服务（**生产推荐**）

```
FastAPI（API 层） --HTTP--> MCP Server（独立进程/独立 Deployment）
                                     │
                                     └─ 工具实现（只读/写操作分开）
```

**优点**：故障隔离、可独立扩缩容、可独立做鉴权与审计、升级不影响 API 层。
**做法**：把 `mcp_server.py` 打成镜像，用 K8s Deployment 部署，FastAPI 通过 MCP Client 调用。

#### 方式 B：挂载到 FastAPI（同一进程，适合小规模）

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from mcp_server import mcp

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp.session_manager.run():
        yield

app = FastAPI(lifespan=lifespan)
app.mount("/mcp", mcp.streamable_http_app())
```

**优点**：部署简单、一个进程搞定。
**代价**：MCP 工具与 API 共享资源与生命周期，工具崩溃可能影响 API；**生产规模上来后建议拆开**。

> ⚠️ 挂载方式对 SDK 版本较敏感（`session_manager`、`streamable_http_app` 的签名可能变化），升级前先在测试环境验证。

### 3.4 FastAPI 作为 MCP Client 调用工具

```python
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCP_URL = "http://mcp-server:8000/mcp"

async def call_tool(name: str, arguments: dict):
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
            return result
```

生产上建议**复用连接/会话**而不是每次新建；并给 `call_tool` 加上**超时、重试（仅幂等工具）、熔断、审计日志**。

### 3.5 MCP 的安全与治理（企业落地重点）

| 风险 | 控制 |
|---|---|
| 工具越权 | 工具白名单 + 按租户授权；写操作强制审批 |
| Prompt 注入 | 工具返回内容视为**不可信数据**，不要让模型把工具输出当指令执行 |
| 参数注入 | 严格 Schema 校验；路径参数做沙箱校验（禁止 `../`） |
| 资源耗尽 | 超时、最大返回大小、并发限制、单次调用配额 |
| 供应链 | 只允许可信来源的 MCP Server；镜像签名与扫描 |
| 审计 | 记录"谁、在什么会话、调用了什么工具、参数摘要、结果状态、耗时" |
| 敏感数据 | 工具结果脱敏后再回给模型；日志中不落明文 |

> **铁律**：MCP 工具是"给模型装的手"，**权限边界必须在工具侧强制执行**，不能指望模型"自觉不调用"。

### 3.6 调试与测试

- 用 **MCP Inspector** 连接 Server，手动调用 `tools/list` / `tools/call`，验证 Schema 与返回；
- 为每个工具写**契约测试**（正常 / 缺参 / 越权 / 超时 / 大返回）；
- 在 CI 里跑"工具调用回放"，防止改工具后 Agent 行为退化。

## 4. React 侧：流式 AI 界面

### 4.1 技术选型

| 层 | 推荐 | 理由 |
|---|---|---|
| 构建 | **Vite + React + TypeScript** | 启动快、类型安全 |
| 数据请求 | `fetch` 原生即可；复杂场景用 TanStack Query | SSE 需要 POST + 自定义 Header，`EventSource` 不够用 |
| Markdown | `react-markdown` + `remark-gfm` + `rehype-sanitize` | 渲染 LLM 输出且防 XSS |
| 状态 | `useReducer` 或轻量状态机 | 流式场景状态多，`useState` 容易乱 |
| 样式 | Tailwind / CSS Modules 均可 | 重点是状态可视化 |

### 4.2 SSE 的正确写法

`EventSource` 只支持 GET、不能加自定义 Header，所以 **LLM 对话场景推荐用 `fetch` + `ReadableStream` 手动解析 SSE**：

```tsx
export type ChatState = "idle" | "sending" | "streaming" | "done" | "error";

export function useChatSSE() {
  const [text, setText] = React.useState("");
  const [state, setState] = React.useState<ChatState>("idle");
  const abortRef = React.useRef<AbortController | null>(null);

  async function send(message: string) {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setText("");
    setState("sending");

    try {
      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        body: JSON.stringify({ message }),
        signal: ctrl.signal,
      });
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

      setState("streaming");
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const chunks = buffer.split("\n\n");
        buffer = chunks.pop() ?? "";
        for (const chunk of chunks) {
          const lines = chunk.split("\n");
          const event = lines.find((l) => l.startsWith("event:"))?.slice(6).trim();
          const data = lines
            .filter((l) => l.startsWith("data:"))
            .map((l) => l.slice(5).trim())
            .join("\n");
          if (!data) continue;

          if (event === "token") setText((prev) => prev + JSON.parse(data).text);
          if (event === "error") throw new Error(JSON.parse(data).message);
        }
      }
      setState("done");
    } catch (err) {
      if ((err as Error).name !== "AbortError") setState("error");
    }
  }

  return { text, state, send, cancel: () => abortRef.current?.abort() };
}
```

**四个关键点：**

1. **必须处理"半包"**：网络返回的 chunk 不保证按 `\n\n` 切好，要用 buffer 拼接；
2. **必须用 `AbortController`**：用户点"停止"要真的取消请求；
3. **`decoder.decode(value, {stream: true})`**：处理多字节中文被切断的情况；
4. **错误要能区分**：`AbortError` 是用户主动取消，不应显示为故障。

### 4.3 状态机（别用一堆布尔值）

```
idle ──send──> sending ──首个 token──> streaming ──done──> done
                   │                        │
                   └──── error ─────────────┴──> error
```

对应 UI：发送按钮置灰、显示"思考中"、逐字渲染、完成后显示引用与重试、失败时显示错误码与"重试"。

### 4.4 渲染与体验

```tsx
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";

export function Message({ content }: { content: string }) {
  return (
    <div className="prose" aria-live="polite">
      <Markdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
        {content}
      </Markdown>
    </div>
  );
}
```

- **必须 sanitize**：LLM 输出可能包含 `<script>`、恶意链接；
- **`aria-live="polite"`**：让屏幕阅读器能读出流式内容；
- **长会话要虚拟列表**：几百轮之后全量渲染会卡；
- **`React.memo` + 稳定的 key**：避免每个 token 触发整个列表重渲染；
- **代码块高亮要按需加载**：别把整个高亮库打进首屏。

### 4.5 一个可用的聊天页骨架

```tsx
export default function ChatPage() {
  const { text, state, send, cancel } = useChatSSE();
  const [input, setInput] = React.useState("");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || state === "streaming") return;
    const q = input.trim();
    setInput("");
    await send(q);
  }

  return (
    <main className="mx-auto max-w-3xl p-4">
      <div className="min-h-[50vh] rounded-lg border p-4">
        {text ? <Message content={text} /> : <p className="text-gray-500">问我任何问题…</p>}
        {state === "sending" && <p className="text-gray-500">正在思考…</p>}
        {state === "error" && <p className="text-red-600">请求失败，请重试</p>}
      </div>
      <form onSubmit={onSubmit} className="mt-4 flex gap-2">
        <input value={input} onChange={(e) => setInput(e.target.value)} className="flex-1 rounded border p-2" />
        {state === "streaming"
          ? <button type="button" onClick={cancel}>停止</button>
          : <button type="submit">发送</button>}
      </form>
    </main>
  );
}
```

## 5. AIGC：图像 / 视频生成的全栈链路

### 5.1 为什么必须异步

| 特征 | LLM 对话 | AIGC 图像/视频 |
|---|---|---|
| 耗时 | 秒级（流式） | 图像数秒–数十秒；视频数分钟–数十分钟 |
| 资源 | 一次占用 1 个推理副本 | 可能长时间独占整卡 |
| 失败代价 | 重试成本低 | 重试成本高，且可能产生部分产物 |
| 交互 | 逐 token 流式 | 进度百分比 / 阶段事件 |
| 产物 | 文本 | 图片/视频文件（大） |

**结论**：AIGC 必须用 **异步任务 + 进度事件 + 对象存储**，不能用同步 HTTP 等结果。

### 5.2 API 设计

```http
POST /api/aigc/jobs            → 202 {job_id, status:"queued", events:"/api/aigc/jobs/{id}/events"}
GET  /api/aigc/jobs/{id}       → {status, progress, result_url?, error?}
GET  /api/aigc/jobs/{id}/events→ SSE：queued → running(progress) → succeeded/failed
POST /api/aigc/jobs/{id}/cancel→ 取消（尽力而为）
```

```python
from pydantic import BaseModel, Field

class AIGCJobRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2_000)
    width: int = Field(default=1024, ge=256, le=2048)
    height: int = Field(default=1024, ge=256, le=2048)
    steps: int = Field(default=25, ge=1, le=80)
    seed: int | None = None
    idempotency_key: str | None = None

@app.post("/api/aigc/jobs", status_code=202)
async def create_aigc_job(req: AIGCJobRequest, tenant: str = Depends(auth)):
    job_id = await job_service.submit(tenant=tenant, req=req)   # 入队，立即返回
    return {"job_id": job_id, "status": "queued", "events": f"/api/aigc/jobs/{job_id}/events"}
```

### 5.3 后端实现要点

```
FastAPI ──submit──> Redis Stream / MQ ──> GPU Worker
                                            │
                                            ├─ ComfyUI（工作流）/ Diffusers（代码）
                                            ├─ 进度回调 → Redis Pub/Sub
                                            └─ 产物 → S3/OSS → 预签名 URL
```

| 要点 | 说明 |
|---|---|
| **队列分区** | 图像、视频、不同模型分队列，避免长任务堵死短任务 |
| **幂等** | `idempotency_key` 去重，避免用户重复点击产生多份费用 |
| **进度** | ComfyUI 用 WebSocket 事件；Diffusers 用 callback，统一转成 `progress` 事件 |
| **取消** | 取消要能真正释放显存；不能只改数据库状态 |
| **产物落盘** | 直接写对象存储，API 只返回**预签名 URL**（不要用后端内存中转） |
| **失败分类** | 参数错误不重试；OOM 可降分辨率重试；节点故障换节点重试 |
| **配额** | 按租户限制并发任务数与每日生成量 |
| **内容安全** | 输入提示词审核 + 输出图片审核 + 水印/溯源 |

### 5.4 React 生成工作台

| 区域 | 组件要点 |
|---|---|
| 参数区 | Prompt、尺寸、步数、随机种子、模型/LoRA 选择；记住上次参数 |
| 提交区 | 显示预估耗时与预计扣费；提交后禁用按钮防重复 |
| 进度区 | SSE 订阅 `queued/running/succeeded`，显示百分比与阶段（排队/加载模型/采样/解码） |
| 结果区 | 图片网格 / 视频播放器，支持下载、复制种子、再次生成 |
| 历史区 | 分页加载，按时间/模型筛选；点击可复现（同参数同 seed） |
| 错误态 | 明确区分"排队超时 / 显存不足 / 内容审核未通过 / 任务被取消" |

### 5.5 AIGC 的成本与合规

- **成本**：按"分辨率 × 步数 × 模型大小 × 时长"估算；视频按秒计费；
- **配额**：免费额度 + 付费套餐 + 团队共享池；
- **合规**：生成内容标识（水印/元数据）、版权与肖像权提示、敏感内容拦截、日志留存；
- **可复现**：保存 `prompt + 负向提示 + seed + 模型版本 + LoRA 版本 + 采样器 + 步数`，否则同一需求无法复现。

## 6. 端到端联调清单

- [ ] FastAPI 的 SSE 在 Nginx/网关后仍然是逐字输出（`X-Accel-Buffering: no`）；
- [ ] 前端能正确处理"半包/粘包"，中文不乱码；
- [ ] 用户点"停止"后，后端确实取消了模型调用（看日志与 GPU 占用）；
- [ ] MCP 工具的 Schema 在 `tools/list` 中可见，非法参数被拒绝；
- [ ] 工具超时/异常返回统一错误，Agent 能降级而不是卡死；
- [ ] AIGC 任务提交后立即返回 202，前端通过 SSE 拿到进度；
- [ ] 任务取消后显存被释放，队列中没有残留；
- [ ] 产物通过预签名 URL 访问，链接有有效期；
- [ ] 全链路有 `request_id / job_id / trace_id`，可从一次失败追到具体节点；
- [ ] 限流、配额、幂等、审计四项在压测中验证通过。

## 7. 常见坑

| 坑 | 现象 | 修复 |
|---|---|---|
| 同步阻塞 async | 一个慢请求拖垮整个服务 | 换异步客户端 / 线程池隔离 |
| SSE 被代理缓冲 | 前端等到最后才显示 | 关闭 buffering，加心跳 |
| 没有取消 | 用户走了 GPU 还在跑 | AbortController + is_disconnected |
| 工具返回过大 | 上下文爆掉、成本飙升 | 分页/摘要/截断 |
| MCP 工具无权限控制 | Agent 能删库 | 工具侧强制鉴权 + 审批 |
| AIGC 同步等待 | 网关超时、连接堆积 | 改异步任务 + 进度事件 |
| 图片直接落本地盘 | 多副本访问不到、磁盘爆 | 对象存储 + 预签名 URL |
| 前端全量重渲染 | 流式时页面卡顿 | memo + 虚拟列表 + 局部更新 |

## 8. 参考链接（2026-10-20 实测可访问）

| 主题 | 链接 |
|---|---|
| MCP 官网 | <https://modelcontextprotocol.io/> |
| MCP 规范 | <https://modelcontextprotocol.io/specification> |
| MCP Python SDK | <https://github.com/modelcontextprotocol/python-sdk> |
| FastMCP（社区增强版） | <https://github.com/jlowin/fastmcp> |
| FastMCP 文档 | <https://gofastmcp.com/> |
| FastAPI | <https://fastapi.tiangolo.com/> |
| Pydantic 文档 | <https://docs.pydantic.dev/latest/> |
| Uvicorn（仓库） | <https://github.com/encode/uvicorn> |
| sse-starlette | <https://github.com/sysid/sse-starlette> |
| SSE 规范（WHATWG） | <https://html.spec.whatwg.org/multipage/server-sent-events.html> |
| React | <https://react.dev/> |
| Vite | <https://vite.dev/> |
| TanStack Query | <https://tanstack.com/query/latest> |
| react-markdown | <https://github.com/remarkjs/react-markdown> |
| ComfyUI | <https://github.com/comfyanonymous/ComfyUI> |
| Hugging Face Diffusers | <https://huggingface.co/docs/diffusers/index> |
| vLLM | <https://docs.vllm.ai/> |

> 说明：`uvicorn.org` 与 `docs.pydantic.dev` 根路径在部分网络下不稳定，故改用可稳定访问的 `latest` 文档与 GitHub 仓库地址。

## 9. 与既有章节的衔接

| 想补什么 | 看哪章 |
|---|---|
| Agent Harness 的职责与组件 | 第 02 章 AI Harness 企业落地教程 |
| Agent 权限、Guardrail 三态授权 | 第 18 章 AI Native 研发范式 |
| 薄 Loop + 厚 Control Plane、WAL 恢复 | 第 20 章 Harness 横向对比与最新实现范式 |
| Coze / Dify / LangChain 选型 | 第 23 章 |
| 统一 AI Gateway、Agent Runtime 架构 | 第 22 章 AI 平台架构师岗位与面试 |
| 推理服务、vLLM、K8s 部署 | 第 04 章 AI Infra 企业平台教程 |
| GPU 集群与故障处理 | 第 07 / 08 章 |