# Multi-Agent Runbook

## Objective
Deliver AI-first features through a strict 4-agent workflow with explicit handoffs and quality gates.

## Agents
- Manager: scope, prioritize, gate decisions.
- Architect: design the simplest viable technical solution.
- Developer: implement exactly against approved design.
- Validation Tester: verify behavior, safety, and release readiness.

## Workflow
1. Manager -> create `artifacts/plan.md`.
2. Architect -> create `artifacts/architecture.md` from plan.
3. Developer -> implement and create `artifacts/implementation.md`.
4. Validation Tester -> create `tests/test-report.md`.

## Gates
1. Gate A (Plan Approved): manager confirms scope/KPIs are clear.
2. Gate B (Design Approved): architecture is simple, feasible, testable.
3. Gate C (Build Complete): implementation matches architecture.
4. Gate D (Release Decision): validation passes critical checks.

## Handoff Contract (all agents)
- Input: approved artifact(s) from previous step.
- Output: one artifact + short status (`PASS`/`BLOCKED`).
- Blocked rule: include blocker, impact, and owner.
- Simplicity rule: prefer smallest solution that works.

## Cadence
- Each phase ends with a 5-line summary: done, risks, open items, next owner, ETA.
- Each phase has to get the manager approval AND user approval. If not approved, should return responsibility to the correct agent.
- No phase starts before previous gate is `PASS`.

## Git Methodology
- Each agent works on its own dedicated branch (see agent files for branch names).
- Branch naming: `agent/<role>` (e.g. `agent/manager`, `agent/architect`, `agent/developer`, `agent/validation-tester`).
- Each agent branches from `main` only after the previous gate's PR is merged.
- When an agent completes its output artifact: `git add` → `git commit` → open a PR to `main`.
- PR title format: `[AgentName] Gate X — <short description>`.
- PRs require approval from Manager + Ayala before merging.
- If changes are requested: fix on the same branch, push, PR auto-updates.
- No agent starts its branch until the previous gate PR is merged into `main`.
