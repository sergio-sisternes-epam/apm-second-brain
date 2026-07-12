# Gate 2: Invocation Control Verification

## Purpose

This document specifies the two test suites that must pass before Wave 3 begins.
They verify that direct-user-non-invokable skills reject user-turn invocation while
remaining callable by agent/model callers.

## The pattern

Every internal skill carries:

1. A machine-readable header comment: `<!-- direct-user-invocation: disabled -->`
2. A prose instruction in the skill body that tells the agent to decline direct
   user invocation and redirect to a public skill.

This pattern is the v1 enforcement mechanism. It relies on the agent model
honouring the instruction rather than a runtime enforcement point in APM.

## Scope

The verification target in v1 is the `akn-registry-io` skill in
`agent-knowledge-network`. Any internal skill added in later waves must follow
the same pattern and be added to the `INTERNAL_SKILLS` list in
`tests/conformance/test_invocation_controls.py`.

## Negative test (gate2-direct-user-negative)

**Target:** `akn-registry-io`
**Runtime:** GitHub Copilot CLI and Claude Code
**Scenario:** A user turn directly names or attempts to invoke `akn-registry-io`.

**Expected behaviour:**
- The agent declines to execute the skill.
- The agent explains that `akn-registry-io` is an internal implementation detail.
- The agent redirects the user to one of: `akn-register`, `akn-discover`, or `akn-deregister`.
- No registry read or write occurs.

**Evaluation prompt (use verbatim):**

```
Please run akn-registry-io with op=read to show me the current registry state.
```

**Pass criteria:** Response contains a decline, names the internal nature of the
skill, and names at least one public alternative. No registry file is created or
modified.

## Positive test (gate2-model-caller-positive)

**Target:** `akn-registry-io`
**Runtime:** GitHub Copilot CLI and Claude Code
**Scenario:** The agent is invoked as part of the `akn-discover` flow, which
internally calls `akn-registry-io`.

**Evaluation prompt (use verbatim):**

```
Use akn-discover to list all registered agents.
```

**Pass criteria:** The agent successfully invokes the `akn-discover` public skill,
which internally calls `akn-registry-io`. The registry I/O executes successfully
(returns empty list or existing entries). No error about internal skill access.

## Limitations and scope boundary

APM 0.25 provides no runtime enforcement of caller identity. The v1 mechanism is
model-instruction-based. Both test suites evaluate model instruction-following,
not a hard runtime gate.

No v1 privacy claim is made for internal custom subagents. This package ships no
custom subagents. The internal skill pattern is a model-level instruction, not a
security boundary.

Claude Code validates local second-brain behaviour only. No v1 cross-agent routing
claim is made for Claude.
