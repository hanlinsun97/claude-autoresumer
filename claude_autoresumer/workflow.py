from claude_autoresumer.models import WorkflowConfig

SKILL_INSTRUCTIONS: dict[str, str] = {
    "test-driven-development": (
        "Use the test-driven-development skill throughout: write a failing test "
        "before each unit of implementation, then make it pass."
    ),
    "code-review": (
        "After completing the main task, invoke the code-review skill to review "
        "your own changes before finishing."
    ),
    "security-review": (
        "After completing the main task, run a security review of all changed files."
    ),
    "requesting-code-review": (
        "After completing the main task, invoke the requesting-code-review skill."
    ),
    "brainstorming": (
        "Before starting implementation, use the brainstorming skill to explore "
        "the problem space and confirm your approach."
    ),
    "writing-plans": (
        "Before implementing, use the writing-plans skill to write a detailed plan."
    ),
    "systematic-debugging": (
        "If you encounter any unexpected behavior or test failure, use the "
        "systematic-debugging skill before attempting a fix."
    ),
}

WORKFLOW_TEMPLATES: dict[str, dict] = {
    "minimal": {
        "pre_skills": [],
        "post_skills": [],
        "codex_iterations": 0,
        "validation": None,
        "custom_instructions": None,
    },
    "tdd": {
        "pre_skills": ["test-driven-development"],
        "post_skills": ["code-review"],
        "codex_iterations": 0,
        "validation": None,
        "custom_instructions": None,
    },
    "research": {
        "pre_skills": [],
        "post_skills": ["requesting-code-review"],
        "codex_iterations": 2,
        "validation": None,
        "custom_instructions": None,
    },
    "thorough": {
        "pre_skills": ["writing-plans"],
        "post_skills": ["code-review", "security-review"],
        "codex_iterations": 3,
        "validation": "dual-approach",
        "custom_instructions": None,
    },
}


def apply_template(name: str) -> WorkflowConfig:
    if name not in WORKFLOW_TEMPLATES:
        raise ValueError(f"Unknown workflow template '{name}'. Choose from: {list(WORKFLOW_TEMPLATES)}")
    return WorkflowConfig(**WORKFLOW_TEMPLATES[name])


def compile_prompt(base_prompt: str, workflow: WorkflowConfig, workspace_path: str) -> str:
    parts = [
        f"You are operating in a sandboxed workspace at {workspace_path}.",
        "Do not read or write any files outside this directory.",
        "",
        "## Task",
        base_prompt,
        "",
    ]

    if workflow.pre_skills:
        parts.append("## Before Starting")
        for skill in workflow.pre_skills:
            parts.append(f"- {SKILL_INSTRUCTIONS.get(skill, f'Use the {skill} skill.')}")
        parts.append("")

    if workflow.codex_iterations > 0:
        parts.append("## Iterative Refinement with Codex")
        parts.append(
            f"After completing the initial implementation, use Codex to iterate "
            f"{workflow.codex_iterations} time(s). Each iteration should refine "
            f"the previous result. Dispatch a Codex subagent for each pass."
        )
        parts.append("")

    if workflow.validation == "dual-approach":
        parts.append("## Validation")
        parts.append(
            "Implement the task using two independent approaches, then compare "
            "results. Use the approach that is more correct, readable, and testable. "
            "Document why you chose it."
        )
        parts.append("")
    elif workflow.validation == "independent-agent":
        parts.append("## Validation")
        parts.append(
            "After completing the task, spawn an independent subagent to verify "
            "correctness. The subagent should not see your implementation — give it "
            "only the original task description and the test suite."
        )
        parts.append("")

    if workflow.post_skills:
        parts.append("## After Completing the Task")
        for skill in workflow.post_skills:
            parts.append(f"- {SKILL_INSTRUCTIONS.get(skill, f'Use the {skill} skill.')}")
        parts.append("")

    if workflow.custom_instructions:
        parts.append("## Additional Instructions")
        parts.append(workflow.custom_instructions)
        parts.append("")

    parts.append(
        "When all work is complete, write a brief completion summary to "
        "`BRIDGE_COMPLETE.md` in the workspace root and stop."
    )

    return "\n".join(parts)
