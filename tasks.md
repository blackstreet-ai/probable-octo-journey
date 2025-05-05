# ✅ AI Video Automation Task List

This is a derived task list based on the system architecture outlined in `blueprint.md`.

---

## 📁 Agent Development

- [x] Implement `VideoOrchestratorAgent` to coordinate all sub-agents
- [x] Create `ScriptRewriterAgent` with prompt templates and rewrite logic
- [x] Integrate `VoiceoverAgent` using ElevenLabs or equivalent TTS
- [x] Build `MusicSupervisorAgent` with tempo-matching and sidechaining support
- [x] Develop `VisualComposerAgent` using fal.ai or other external image APIs
- [x] Code `VideoEditorAgent` to compile visuals, voiceover, and music using ffmpeg

---

## ⚙️ Workflow Execution

- [x] Design hybrid sequential + parallel agent workflow
- [x] Use `run_steps_sequentially()` for core pipeline flow
- [x] Use `run_steps_in_parallel()` for concurrent voice + visual generation
- [x] Add fallback and error recovery logic in orchestration

---

## 🧱 Project Structure Enhancements

- [x] Create folders: `agents/`, `tools/`, `configs/`, `logs/`
- [x] Refactor `run.py` into `launch.py`, `pipeline.py`, and `config.py`
- [x] Add environment config loader using `python-dotenv`

---

## 📝 Prompt Engineering

- [x] Create YAML prompt templates in `prompts/` directory
- [x] Define tone/style options in prompts (e.g. Case in Point, Prime Example)
- [ ] Version control prompts for iterative improvement

---

## 📊 Logging & Observability

- [x] Add execution logging per agent
- [x] Track runtime duration of each agent
- [ ] Optional: visualize execution graph using LangGraph-style tracing

---

## 🔐 API Security

- [x] Add `.env` file for API keys
- [x] Implement `token_manager.py` for validation and rotation
- [x] Add basic rate limiting logic for external API calls

---

## 🧪 Testing and QA

- [x] Write unit tests for each agent
- [x] Create end-to-end integration test: transcript → full video
- [x] Mock ElevenLabs and image generator APIs for tests
- [x] Setup GitHub Actions to run `pytest`, `black`, `ruff`

---

## 🚀 Future Roadmap

- [ ] Expose pipeline as REST API
- [ ] Add human-in-the-loop checkpoints (optional)
- [ ] Enable theme/mood toggles for visual generation
- [ ] Add usage analytics per generated video

---

## 🔄 Discovered During Work (2025-05-04)

- [x] Implement `VoiceoverAgent` using OpenAI Agents SDK
- [x] Implement `MusicSupervisorAgent` using OpenAI Agents SDK
- [x] Implement `VisualComposerAgent` using OpenAI Agents SDK
- [x] Implement `VideoEditorAgent` using OpenAI Agents SDK
- [x] Implement `PublishManagerAgent` using OpenAI Agents SDK
- [x] Implement `ReporterAgent` using OpenAI Agents SDK
- [x] Create token_manager.py for API key validation and rotation
- [x] Write unit tests for VideoOrchestratorAgent
- [x] Write unit tests for ScriptRewriterAgent
- [x] Update requirements.txt with OpenAI SDK dependencies

## 📝 Script Development (2025-05-04)

- [ ] Create `ScriptGeneratorAgent` for automated script creation
- [ ] Implement script templates for different video formats (tutorial, explainer, product demo)
- [ ] Add script formatting and structure validation
- [ ] Develop script enhancement features (hooks, calls to action, transitions)
- [ ] Create unit tests for script generation components
- [ ] Integrate script generation into the main pipeline workflow
- [ ] Add script versioning and revision history tracking
