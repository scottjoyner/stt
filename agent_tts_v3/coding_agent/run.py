from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from voicebus.schema.tasks import Task

try:
    import dspy  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    dspy = None


@dataclass
class CodingResult:
    changed_files: list[str] = field(default_factory=list)
    patch_diffs: list[str] = field(default_factory=list)
    tests_executed: list[str] = field(default_factory=list)
    test_results: list[str] = field(default_factory=list)
    evaluation_score: float = 0.0


class SafeWorkspaceTools:
    def __init__(self, workspace: Path, run_tests_enabled: bool = False) -> None:
        self.workspace = workspace
        self.run_tests_enabled = run_tests_enabled

    def read_file(self, rel: str) -> str:
        return (self.workspace / rel).read_text(encoding="utf-8")

    def write_file(self, rel: str, content: str) -> None:
        p = self.workspace / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def apply_patch(self, patch_text: str) -> None:
        proc = subprocess.run(["git", "apply", "-"], input=patch_text.encode("utf-8"), cwd=self.workspace, check=True)
        _ = proc

    def run_tests(self, cmd: str = "pytest -q") -> str:
        if not self.run_tests_enabled:
            return "tests disabled"
        proc = subprocess.run(cmd.split(), cwd=self.workspace, capture_output=True, text=True)
        return proc.stdout + proc.stderr


class IssueUnderstanding:
    def __call__(self, task: Task) -> str:
        return f"Task {task.task_id}: {task.title}\n{task.details}"


class PlanSynthesis:
    def __call__(self, issue_summary: str) -> str:
        return f"Plan: inspect files, patch minimally, run tests.\n{issue_summary}"


class PatchProposal:
    def __call__(self, plan: str) -> str:
        return f"No-op patch proposal for now.\n{plan}"


class PatchApplication:
    def __call__(self, tools: SafeWorkspaceTools, patch: str) -> str:
        return patch


class TestGeneration:
    def __call__(self, task: Task) -> list[str]:
        return ["pytest -q"]


class PatchEvaluation:
    def __call__(self, test_output: str) -> float:
        return 1.0 if "failed" not in test_output.lower() else 0.2


def run_coding_task(task: Task, workspace: Path) -> CodingResult:
    if dspy is None:
        raise RuntimeError("DSPy is not installed. Install optional dependency 'dspy' to run coding agent.")

    tools = SafeWorkspaceTools(workspace=workspace, run_tests_enabled=False)
    issue = IssueUnderstanding()(task)
    plan = PlanSynthesis()(issue)
    patch = PatchProposal()(plan)
    _ = PatchApplication()(tools, patch)

    tests = TestGeneration()(task)
    outputs = [tools.run_tests(t) for t in tests]
    score = PatchEvaluation()("\n".join(outputs))
    return CodingResult(tests_executed=tests, test_results=outputs, evaluation_score=score)
