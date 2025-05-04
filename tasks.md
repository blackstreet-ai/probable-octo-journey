# ✅ AI Video Automation Task List

This is a derived task list based on the system architecture outlined in `blueprint.md`.

---

## 📁 Agent Development

- [ ] Implement `VideoOrchestratorAgent` to coordinate all sub-agents
- [ ] Create `ScriptRewriterAgent` with prompt templates and rewrite logic
- [ ] Integrate `VoiceoverAgent` using ElevenLabs or equivalent TTS
- [ ] Build `MusicSupervisorAgent` with tempo-matching and sidechaining support
- [ ] Develop `VisualComposerAgent` using fal.ai or other external image APIs
- [ ] Code `VideoEditorAgent` to compile visuals, voiceover, and music using ffmpeg

---

## ⚙️ Workflow Execution

- [ ] Design hybrid sequential + parallel agent workflow
- [ ] Use `run_steps_sequentially()` for core pipeline flow
- [ ] Use `run_steps_in_parallel()` for concurrent voice + visual generation
- [ ] Add fallback and error recovery logic in orchestration

---

## 🧱 Project Structure Enhancements

- [ ] Create folders: `agents/`, `tools/`, `configs/`, `logs/`
- [ ] Refactor `run.py` into `launch.py`, `pipeline.py`, and `config.py`
- [ ] Add environment config loader using `python-dotenv`

---

## 📝 Prompt Engineering

- [ ] Create YAML prompt templates in `prompts/` directory
- [ ] Define tone/style options in prompts (e.g. Case in Point, Prime Example)
- [ ] Version control prompts for iterative improvement

---

## 📊 Logging & Observability

- [ ] Add execution logging per agent
- [ ] Track runtime duration of each agent
- [ ] Optional: visualize execution graph using LangGraph-style tracing

---

## 🔐 API Security

- [ ] Add `.env` file for API keys
- [ ] Implement `token_manager.py` for validation and rotation
- [ ] Add basic rate limiting logic for external API calls

---

## 🧪 Testing and QA

- [ ] Write unit tests for each agent
- [ ] Create end-to-end integration test: transcript → full video
- [ ] Mock ElevenLabs and image generator APIs for tests
- [ ] Setup GitHub Actions to run `pytest`, `black`, `ruff`

---

## 🚀 Future Roadmap

- [ ] Expose pipeline as REST API
- [ ] Add human-in-the-loop checkpoints (optional)
- [ ] Enable theme/mood toggles for visual generation
- [ ] Add usage analytics per generated video
