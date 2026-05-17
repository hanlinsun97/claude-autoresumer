from claude_bridge.models import WorkflowConfig
from claude_bridge.workflow import compile_prompt, apply_template, WORKFLOW_TEMPLATES


def test_compile_minimal_prompt():
    wf = WorkflowConfig()
    result = compile_prompt(
        base_prompt="Fix the auth bug",
        workflow=wf,
        workspace_path="/tmp/ws/job-1",
    )
    assert "Fix the auth bug" in result
    assert "/tmp/ws/job-1" in result
    assert "outside this directory" in result


def test_compile_adds_pre_skills():
    wf = WorkflowConfig(pre_skills=["test-driven-development"])
    result = compile_prompt("do work", wf, "/ws")
    assert "test-driven-development" in result.lower() or "tdd" in result.lower() or "failing test" in result.lower()


def test_compile_adds_post_skills():
    wf = WorkflowConfig(post_skills=["code-review"])
    result = compile_prompt("do work", wf, "/ws")
    assert "code-review" in result.lower() or "code review" in result.lower()


def test_compile_adds_codex_instructions():
    wf = WorkflowConfig(codex_iterations=2)
    result = compile_prompt("do work", wf, "/ws")
    assert "codex" in result.lower() or "iteration" in result.lower()


def test_compile_adds_custom_instructions():
    wf = WorkflowConfig(custom_instructions="Always use type hints.")
    result = compile_prompt("do work", wf, "/ws")
    assert "Always use type hints." in result


def test_compile_dual_approach_validation():
    wf = WorkflowConfig(validation="dual-approach")
    result = compile_prompt("do work", wf, "/ws")
    assert "two" in result.lower() or "dual" in result.lower() or "independent" in result.lower()


def test_apply_template_tdd():
    wf = apply_template("tdd")
    assert "test-driven-development" in wf.pre_skills
    assert "code-review" in wf.post_skills


def test_apply_template_thorough():
    wf = apply_template("thorough")
    assert wf.codex_iterations == 3
    assert wf.validation == "dual-approach"


def test_apply_template_unknown_raises():
    try:
        apply_template("nonexistent")
        assert False
    except ValueError:
        pass
