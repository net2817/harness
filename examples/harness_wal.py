#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
harness_wal.py — 「薄 Agent Loop + 厚 Control Plane」最小可运行参考实现。

对应 2026 年 Harness 工程共识（见学习手册第 20 章《Harness 横向对比与最新实现范式》）：

  1. 薄 Loop        : 循环只做 读上下文 -> 规划 -> 调工具 -> 写日志，边界清晰，约 200 行量级
  2. 厚 Control Plane: 权限 / 沙箱 / 持久化 / 恢复 / 审计 全部在 Loop 之外
  3. WAL            : 状态可以丢，日志不能丢；崩溃后按 Operation Log 找「安全恢复点」
  4. Fail Fast      : 同类错误达到阈值立即停止，绝不靠 Retry 把小故障放大成雪崩
  5. 受控自进化      : 任何自我改动必须经 隔离评测 -> 灰度 -> 保留回滚 的闭环

无第三方依赖。运行：  python harness_wal.py
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

# ----------------------------------------------------------------------------
# 0. 基础设施
# ----------------------------------------------------------------------------


class Corruption(Exception):
    """WAL 完整性校验失败 —— 必须显式暴露，绝不能静默继续。"""


def _digest(rec: Dict[str, Any]) -> str:
    """对记录内容做稳定摘要，形成哈希链（防篡改 / 防截断）。"""
    blob = json.dumps(rec, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


# ----------------------------------------------------------------------------
# 1. WAL：追加写 + fsync + 哈希链，可回放重建全部状态
# ----------------------------------------------------------------------------


class OpLog:
    """Write-Ahead Log。

    设计要点（对照数据库）：
      * 先写日志再改状态 —— 日志是唯一真相来源；
      * 每条记录带 prev 指针 + digest，形成链，能发现损坏与截断；
      * append 后立即 flush + fsync，保证进程崩溃时记录已落盘。
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self._fh = None
        self._seq = 0
        self._prev = "genesis"

    # -- 生命周期 ---------------------------------------------------------
    def open(self) -> "OpLog":
        records = self.replay(self.path)
        if records:
            self._seq = records[-1]["seq"]
            self._prev = records[-1]["digest"]
        self._fh = open(self.path, "a", encoding="utf-8")
        return self

    def close(self) -> None:
        if self._fh:
            self._fh.close()
            self._fh = None

    # -- 写入 -------------------------------------------------------------
    def append(self, kind: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        assert self._fh is not None, "OpLog 未 open()"
        self._seq += 1
        rec: Dict[str, Any] = {
            "seq": self._seq,
            "ts": round(time.time(), 3),
            "kind": kind,
            "payload": payload,
            "prev": self._prev,
        }
        rec["digest"] = _digest(rec)
        self._fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._fh.flush()
        os.fsync(self._fh.fileno())  # 关键：崩溃也不丢日志
        self._prev = rec["digest"]
        return rec

    # -- 读取 -------------------------------------------------------------
    @staticmethod
    def replay(path: str) -> List[Dict[str, Any]]:
        """回放日志；校验哈希链，任何不一致都抛 Corruption。"""
        if not os.path.exists(path):
            return []
        records: List[Dict[str, Any]] = []
        prev = "genesis"
        with open(path, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
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


# ----------------------------------------------------------------------------
# 2. Workspace：由 WAL 回放重建的持久状态（可快照 / 可回滚）
# ----------------------------------------------------------------------------


class Workspace:
    """持久工作区。状态本身可以丢，因为随时能从日志重建。"""

    def __init__(self) -> None:
        self.files: Dict[str, str] = {}
        self.notes: List[str] = []

    def apply(self, kind: str, payload: Dict[str, Any]) -> None:
        if kind == "file.write":
            self.files[payload["path"]] = payload["content"]
        elif kind == "file.delete":
            self.files.pop(payload["path"], None)
        elif kind == "note":
            self.notes.append(payload["text"])

    def snapshot(self) -> Dict[str, Any]:
        return {"files": dict(self.files), "notes": list(self.notes)}

    def restore(self, snap: Dict[str, Any]) -> None:
        self.files = dict(snap["files"])
        self.notes = list(snap["notes"])

    @classmethod
    def rebuild(cls, records: List[Dict[str, Any]]) -> "Workspace":
        ws = cls()
        for rec in records:
            if rec["kind"] in ("file.write", "file.delete", "note"):
                ws.apply(rec["kind"], rec["payload"])
            elif rec["kind"] == "rollback":
                ws.restore(rec["payload"]["snapshot"])
        return ws


# ----------------------------------------------------------------------------
# 3. Policy：厚 Control Plane —— 权限收口 + 路径沙箱
# ----------------------------------------------------------------------------


class Policy:
    """权限与沙箱。Loop 无权绕过，所有动作统一在这里收口。"""

    def __init__(self, sandbox_root: str, allow_tools: Tuple[str, ...], deny_paths: Tuple[str, ...] = ()) -> None:
        self.sandbox_root = os.path.abspath(sandbox_root)
        self.allow_tools = set(allow_tools)
        self.deny_paths = tuple(deny_paths)

    def check_tool(self, name: str) -> Tuple[bool, str]:
        if name not in self.allow_tools:
            return False, f"工具 {name} 不在白名单"
        return True, "ok"

    def check_path(self, path: str) -> Tuple[bool, str]:
        full = os.path.abspath(os.path.join(self.sandbox_root, path))
        if not (full == self.sandbox_root or full.startswith(self.sandbox_root + os.sep)):
            return False, f"路径越出沙箱：{path}"
        for pat in self.deny_paths:
            if pat in full:
                return False, f"路径命中禁写规则：{pat}"
        return True, "ok"


# ----------------------------------------------------------------------------
# 4. Guardrail：三态判定 PASS / BLOCKED / UNKNOWN + 证据
# ----------------------------------------------------------------------------


@dataclass
class Verdict:
    state: str                      # PASS | BLOCKED | UNKNOWN
    evidence: Dict[str, Any] = field(default_factory=dict)


class Guardrail:
    """确定性验证。Agent 说「我修好了」不算数，必须由外部不变量证明。

    UNKNOWN 是刻意保留的三态：当无法判定时既不放行也不拦截，
    而是升级为人工/异步复核 —— 避免「默认放行」带来的隐性风险。
    """

    MAX_BYTES = 200_000

    def check(self, tool: str, args: Dict[str, Any], result: Any) -> Verdict:
        if tool == "write_file":
            content = args.get("content", "")
            if len(content.encode("utf-8")) > self.MAX_BYTES:
                return Verdict("BLOCKED", {"reason": "写入超过大小上限", "bytes": len(content)})
            if not content.strip():
                return Verdict("UNKNOWN", {"reason": "内容为空，需人工确认是否为预期结果"})
            return Verdict("PASS", {"bytes": len(content.encode('utf-8'))})
        if tool == "run_tests":
            passed = result.get("passed", False)
            if passed:
                return Verdict("PASS", {"tests": result.get("count", 0)})
            return Verdict("BLOCKED", {"reason": "测试未通过", "failed": result.get("failed", [])})
        return Verdict("UNKNOWN", {"reason": f"工具 {tool} 没有定义验证器"})


# ----------------------------------------------------------------------------
# 5. Harness：薄 Loop + 安全恢复点
# ----------------------------------------------------------------------------


@dataclass
class Tool:
    name: str
    fn: Callable[..., Any]
    description: str = ""


class Harness:
    """薄 Agent Loop。

    循环体只有四步：读上下文 -> 规划 -> 调工具 -> 写日志。
    其余一切（权限、沙箱、验证、持久化、恢复）都在 Control Plane 里。
    """

    def __init__(
        self,
        log_path: str,
        policy: Policy,
        guardrail: Guardrail,
        tools: Dict[str, Tool],
        planner: Callable[[Dict[str, Any]], Optional[Dict[str, Any]]],
        checkpoint_every: int = 3,
        fail_fast_after: int = 2,
        max_steps: int = 40,
    ) -> None:
        self.log = OpLog(log_path)
        self.policy = policy
        self.guardrail = guardrail
        self.tools = tools
        self.planner = planner
        self.checkpoint_every = checkpoint_every
        self.fail_fast_after = fail_fast_after
        self.max_steps = max_steps
        self.workspace = Workspace()
        self.consecutive_errors = 0

    # -- 运行 -------------------------------------------------------------
    def run(self, goal: str, resume: bool = False) -> str:
        self.log.open()
        records = OpLog.replay(self.log.path)
        self.workspace = Workspace.rebuild(records)

        start_step = 0
        if resume and records:
            start_step, pending = self.recovery_point(records)
            if pending:
                # 崩溃点：该操作没有结果，视为「未知结果」，先回滚到最近 checkpoint
                self.log.append("rollback", {
                    "reason": "resume: 未完成操作，回滚到最近可信状态",
                    "pending_op": pending,
                    "snapshot": self._last_checkpoint(records) or Workspace().snapshot(),
                })
                self.workspace = Workspace.rebuild(OpLog.replay(self.log.path))
            self.log.append("loop.resume", {"from_step": start_step})

        if not records:
            self.log.append("loop.start", {"goal": goal})

        status = "finished"
        history: List[Dict[str, Any]] = [
            {"role": "goal", "text": goal},
            {"role": "obs", "text": f"已执行 {start_step} 步，工作区 {len(self.workspace.files)} 个文件"},
        ]

        for step in range(start_step, self.max_steps):
            plan = self.planner({"goal": goal, "history": history, "workspace": self.workspace.snapshot()})
            if plan is None:
                self.log.append("loop.finish", {"reason": "planner 返回 None"})
                break

            tool_name = plan.get("tool")
            args = plan.get("args", {})

            # --- Control Plane 前置：权限 + 沙箱 ---
            ok, why = self.policy.check_tool(tool_name)
            if ok and "path" in args:
                ok, why = self.policy.check_path(args["path"])
            if not ok:
                self.log.append("policy.deny", {"tool": tool_name, "reason": why, "step": step})
                status = self._count_error(step, f"policy denied: {why}")
                if status == "fail_fast":
                    break
                continue

            # --- 执行工具（副作用点，前后都有日志） ---
            call_id = uuid.uuid4().hex[:8]
            self.log.append("tool.call", {"call_id": call_id, "tool": tool_name, "args": args, "step": step})
            try:
                result = self.tools[tool_name].fn(**args)
            except Exception as exc:  # 工具失败 = 快速暴露，不重试
                self.log.append("tool.error", {"call_id": call_id, "error": repr(exc)})
                status = self._count_error(step, f"tool error: {exc!r}")
                if status == "fail_fast":
                    break
                continue

            # --- Control Plane 后置：确定性验证 ---
            verdict = self.guardrail.check(tool_name, args, result)
            self.log.append("guard.verdict", {
                "call_id": call_id, "tool": tool_name,
                "state": verdict.state, "evidence": verdict.evidence,
            })

            if verdict.state == "BLOCKED":
                self.log.append("tool.result", {"call_id": call_id, "accepted": False})
                status = self._count_error(step, f"blocked: {verdict.evidence}")
                if status == "fail_fast":
                    break
                continue

            # PASS / UNKNOWN 均落盘（UNKNOWN 记录为待复核，不阻塞主流程）
            self.log.append("tool.result", {"call_id": call_id, "accepted": True, "result": result})
            self.workspace.apply(self._as_state_kind(tool_name), {**args, **(result or {})})
            self.consecutive_errors = 0
            history.append({"role": "act", "text": f"{tool_name}({args}) -> {result}"})

            if step and step % self.checkpoint_every == 0:
                self.checkpoint()

        self.log.close()
        return status

    # -- 恢复点 -----------------------------------------------------------
    @staticmethod
    def recovery_point(records: List[Dict[str, Any]]) -> Tuple[int, Optional[Dict[str, Any]]]:
        """返回 (最后完成的步号, 未完成操作)。

        规则：最后一个 tool.call 若没有配对的 tool.result，就是崩溃点。
        """
        results = {r["payload"]["call_id"] for r in records if r["kind"] == "tool.result"}
        last_step = 0
        pending = None
        for r in records:
            if r["kind"] in ("tool.result", "tool.error", "guard.verdict", "loop.finish"):
                last_step = max(last_step, r["payload"].get("step", 0) + 1)
            if r["kind"] == "tool.call" and r["payload"]["call_id"] not in results:
                pending = r["payload"]
        return last_step, pending

    def _last_checkpoint(self, records: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        for rec in reversed(records):
            if rec["kind"] == "checkpoint":
                return rec["payload"]["snapshot"]
        return None

    # -- 辅助 -------------------------------------------------------------
    def checkpoint(self) -> None:
        self.log.append("checkpoint", {"snapshot": self.workspace.snapshot()})
        print(f"  [checkpoint] 已落盘：{len(self.workspace.files)} 个文件")

    def _count_error(self, step: int, reason: str) -> str:
        self.consecutive_errors += 1
        if self.consecutive_errors >= self.fail_fast_after:
            self.log.append("loop.fail_fast", {
                "step": step, "reason": reason, "consecutive_errors": self.consecutive_errors,
            })
            print(f"  [FAIL FAST] 连续 {self.consecutive_errors} 次错误，立即停止：{reason}")
            return "fail_fast"
        print(f"  [error] {reason}（第 {self.consecutive_errors} 次）")
        return "retry_allowed"

    @staticmethod
    def _as_state_kind(tool: str) -> str:
        return {"write_file": "file.write", "delete_file": "file.delete", "note": "note"}.get(tool, "obs")


# ----------------------------------------------------------------------------
# 6. 受控自进化（示例策略）
# ----------------------------------------------------------------------------


class SelfEvolutionGate:
    """自进化必须走受控闭环：隔离评测 -> 质量/成本/时延/安全门槛 -> 灰度 -> 保留回滚。

    这里的实现是「策略声明 + 判定」，真实系统里替换为你的 CI/CD 与评测平台。
    """

    THRESHOLDS = {"quality": 0.95, "cost_ratio": 1.10, "latency_ratio": 1.20}

    def admit(self, candidate: Dict[str, float], baseline: Dict[str, float]) -> Tuple[bool, str]:
        if candidate["quality"] < self.THRESHOLDS["quality"]:
            return False, "质量未达标"
        if candidate["cost"] > baseline["cost"] * self.THRESHOLDS["cost_ratio"]:
            return False, "成本上升超阈值"
        if candidate["latency"] > baseline["latency"] * self.THRESHOLDS["latency_ratio"]:
            return False, "时延劣化超阈值"
        return True, "进入灰度（保留一键回滚）"


# ----------------------------------------------------------------------------
# 7. 演示
# ----------------------------------------------------------------------------


def scripted_planner(script: List[Optional[Dict[str, Any]]]) -> Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """用一段脚本代替真实模型，方便离线跑通演示。"""
    idx = {"i": 0}

    def _plan(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        i = idx["i"]
        if i >= len(script):
            return None
        idx["i"] += 1
        return script[i]

    return _plan


def build_tools(root: str) -> Dict[str, Tool]:
    def write_file(path: str, content: str) -> Dict[str, Any]:
        full = os.path.join(root, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
        return {"ok": True, "path": path}

    def run_tests(suite: str = "unit") -> Dict[str, Any]:
        return {"passed": True, "count": 12, "failed": []}

    return {
        "write_file": Tool("write_file", write_file, "写入文件（沙箱内）"),
        "run_tests": Tool("run_tests", run_tests, "运行测试"),
    }


def demo() -> None:
    print("=" * 72)
    print("Demo 1：正常执行 —— 薄 Loop + WAL + Checkpoint")
    print("=" * 72)
    tmp = tempfile.mkdtemp(prefix="harness_")
    log_path = os.path.join(tmp, "oplog.jsonl")
    policy = Policy(tmp, allow_tools=("write_file", "run_tests"))
    harness = Harness(
        log_path, policy, Guardrail(), build_tools(tmp),
        scripted_planner([
            {"tool": "write_file", "args": {"path": "src/app.py", "content": "print('hello harness')"}},
            {"tool": "run_tests", "args": {"suite": "unit"}},
            {"tool": "write_file", "args": {"path": "docs/design.md", "content": "# 设计\n薄 Loop + 厚 Control Plane"}},
            {"tool": "write_file", "args": {"path": "src/util.py", "content": "def add(a, b):\n    return a + b"}},
        ]),
        checkpoint_every=3,
    )
    print("状态:", harness.run("搭建最小 harness"))
    print("文件:", sorted(harness.workspace.files))
    records = OpLog.replay(log_path)
    print(f"WAL 记录数: {len(records)}；最后一条: {records[-1]['kind']}")

    print()
    print("=" * 72)
    print("Demo 2：崩溃后按 Operation Log 恢复（WAL 安全恢复点）")
    print("=" * 72)
    log2 = os.path.join(tmp, "oplog2.jsonl")
    log = OpLog(log2).open()
    log.append("loop.start", {"goal": "做一个会被中断的任务"})
    log.append("tool.call", {"call_id": "abc123", "tool": "write_file",
                             "args": {"path": "will-not-commit.txt", "content": "半成品"}, "step": 0})
    log.append("checkpoint", {"snapshot": {"files": {"committed.txt": "已完成"}, "notes": []}})
    log.append("tool.call", {"call_id": "def456", "tool": "write_file",
                             "args": {"path": "half-written.txt", "content": "正在写..."}, "step": 1})
    log.close()  # 模拟进程在这里崩溃：def456 已发起但没有结果
    print(">> 模拟崩溃：def456 已发起但未记录结果")

    h2 = Harness(log2, policy, Guardrail(), build_tools(tmp), scripted_planner([]))
    h2.run("做一个会被中断的任务", resume=True)
    ws = Workspace.rebuild(OpLog.replay(log2))
    print("恢复后工作区文件:", sorted(ws.files))
    print("→ def456 被判定为「未知结果」，回滚到最近 checkpoint；committed.txt 保留")

    print()
    print("=" * 72)
    print("Demo 3：权限拒绝 + Fail Fast（绝不靠 Retry 放大故障）")
    print("=" * 72)
    log3 = os.path.join(tmp, "oplog3.jsonl")
    h3 = Harness(
        log3, Policy(tmp, allow_tools=("write_file",)), Guardrail(), build_tools(tmp),
        scripted_planner([
            {"tool": "write_file", "args": {"path": "../../etc/passwd", "content": "x"}},
            {"tool": "write_file", "args": {"path": "../escape.txt", "content": "x"}},
            {"tool": "write_file", "args": {"path": "never.txt", "content": "x"}},  # 不应被执行
        ]),
        fail_fast_after=2,
    )
    print("状态:", h3.run("尝试越权"))
    print("工作区文件:", sorted(h3.workspace.files), "（never.txt 未产生 → Loop 已停止）")
    for r in OpLog.replay(log3):
        if r["kind"] in ("policy.deny", "loop.fail_fast"):
            print(f"  WAL[{r['seq']}] {r['kind']}: {json.dumps(r['payload'], ensure_ascii=False)[:90]}")

    print()
    print("=" * 72)
    print("Demo 4：Guardrail 三态判定（PASS / BLOCKED / UNKNOWN）")
    print("=" * 72)
    g = Guardrail()
    cases = [
        ("write_file", {"path": "a.py", "content": "print(1)"}, {"ok": True}),
        ("write_file", {"path": "b.py", "content": "   "}, {"ok": True}),
        ("write_file", {"path": "c.py", "content": "x" * 300_000}, {"ok": True}),
        ("run_tests", {"suite": "unit"}, {"passed": False, "failed": ["test_add"]}),
    ]
    for tool, args, res in cases:
        v = g.check(tool, args, res)
        print(f"  {tool:11s} -> {v.state:8s} {json.dumps(v.evidence, ensure_ascii=False)[:70]}")

    print()
    print("=" * 72)
    print("Demo 5：受控自进化门禁（隔离评测 → 门槛 → 灰度 → 保留回滚）")
    print("=" * 72)
    gate = SelfEvolutionGate()
    base = {"quality": 0.93, "cost": 1.00, "latency": 1.00}
    for cand in (
        {"quality": 0.96, "cost": 1.05, "latency": 1.10},
        {"quality": 0.91, "cost": 1.05, "latency": 1.10},
        {"quality": 0.97, "cost": 1.30, "latency": 1.10},
    ):
        ok, why = gate.admit(cand, base)
        print(f"  候选 {cand} -> {'准入' if ok else '拒绝'}：{why}")

    shutil.rmtree(tmp, ignore_errors=True)
    print()
    print("演示完成。WAL 本身即审计证据：可回放、可校验、可回滚。")


if __name__ == "__main__":
    demo()