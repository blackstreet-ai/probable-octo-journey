# 🧠 AI Video Automation System Enhancement Plan

This document outlines how to improve upon the initial Windsurf-generated repo by transitioning it into a modular, production-ready, agentic architecture using the OpenAI Agents SDK.

---

## 🔧 1. Agent-Oriented System Design

### Suggested Agent Hierarchy

| Agent                  | Role                                                                 |
|------------------------|----------------------------------------------------------------------|
| 🧠 `VideoOrchestratorAgent` | Main controller. Delegates tasks to all sub-agents and handles state |
| ✍️ `ScriptRewriterAgent`     | Enhances raw transcript, adds pacing, story beats, and CTAs         |
| 🗣️ `VoiceoverAgent`          | Synthesizes narration using ElevenLabs or similar                  |
| 🎵 `MusicSupervisorAgent`    | Selects background music, handles tone/tempo, sidechaining         |
| 🖼️ `VisualComposerAgent`     | Generates visuals (DALL·E, stock APIs) based on scenes              |
| 🎬 `VideoEditorAgent`        | Assembles final video with visuals, VO, and music                  |

### Agent Design Guidelines
- Clearly scoped input/output contracts
- Scoped tools per agent (e.g., ffmpeg, music selector)
- Structured logging per agent (e.g., with `rich` or `structlog`)

---

## 🧱 2. Workflow Pattern: Hybrid Sequential + Parallel

- **Sequential flow**: script → voiceover → visual prompt generation
- **Parallel flow**: voiceover and visual generation can run concurrently
- **Final merge** in `VideoEditorAgent`

Use SDK helpers like:
```python
run_steps_sequentially([...])
run_steps_in_parallel([...])
```

---

## 📦 3. Repository Enhancements

### Add These Directories:
```
agents/         # All agent definitions
tools/          # Shared utilities (ffmpeg, music selectors, etc.)
configs/        # Prompt templates, environment settings
logs/           # Trace + debug logs
```

### Refactor `run.py` into:
```
launch.py       # CLI entrypoint
pipeline.py     # Orchestrates agent execution
config.py       # Loads API keys, settings
```

---

## 🤖 4. Improved Prompt Engineering

- Use `prompts/agent_name.yaml` for each agent.
- YAML prompt templates = editable, version-controlled, customizable.
- Allow tone/style switching (e.g., "Case in Point" vs. "Prime Example").

---

## 📈 5. Tracing + Observability

- Log all agent executions and decisions
- Track time spent per agent (for performance profiling)
- Optionally render LangGraph-style decision trees

---

## 🔐 6. API & Security

- Store credentials in `.env` using `python-dotenv`
- Implement `token_manager.py` to validate/rotate API keys
- Add rate-limiting for external APIs to prevent abuse

---

## 🧪 7. Testing Improvements

### Add:
- End-to-end test pipeline (sample transcript → final video)
- Mock integrations for ElevenLabs, image generation
- GitHub Actions: run `pytest`, `black`, `ruff` on PR

---

## 🧭 8. Roadmap Suggestions

1. Convert core logic into agents via OpenAI Agents SDK
2. Expand visual generation to support themes or moods
3. Add human-in-the-loop checkpoints for creative review
4. Build REST API + CLI for public interaction
5. Add analytics to track script quality, user edits, etc.
