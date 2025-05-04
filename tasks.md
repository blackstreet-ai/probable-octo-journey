### 🛠️ **AI‑Generated Video Pipeline — Task List**

---

#### **Sprint 1 · SDK Skeleton & Repo Setup**
- [x] **Create project workspace** → initialize Git repo `ai‑video‑pipeline` with MIT LICENSE & README.
- [x] **Add dependencies** → Poetry/`requirements.txt` for `openai-agents-python`, `python-dotenv`, `pytest`, `ruff`.
- [x] **Scaffold Executive agent** → class `ExecutiveAgent` with run‑level metadata, DAG stubs, logging hooks.
- [x] **Stub Scriptwriter agent** → returns fixed markdown “Hello World” script.
- [x] **Stub Voice‑Synthesis agent** → mock ElevenLabs call; save `hello.wav` to `/assets/audio`.
- [x] **Run E2E test** → ensure Executive triggers Scriptwriter → Voice‑Synthesis; outputs asset manifest JSON.

#### **Sprint 2 · Visual Branch (fal.ai)**
- [ ] **Implement Prompt‑Designer agent** → converts script sections to fal.ai text‑to‑image prompts.
- [ ] **Add Image‑Gen agent wrapper** → call fal.ai image endpoint; save PNGs to `/assets/images`.
- [ ] **Add Video‑Gen agent wrapper** → basic text‑to‑video demo; save MP4s to `/assets/video`.
- [ ] **Create Asset‑Librarian** → catalog URIs + metadata in `asset_manifest.json`.
- [ ] **Unit tests** → mock fal.ai responses; assert correct file naming & manifest structure.

#### **Sprint 3 · Audio Branch**
- [ ] **Integrate real ElevenLabs API** → read key from `.env`; generate multi‑paragraph VO.
- [ ] **Implement Music‑Selector agent** → fetch royalty‑free track via placeholder API.
- [ ] **Build Audio‑Mixer agent** → ffmpeg ducking script; output loudness‑normalized WAV.
- [ ] **CI check** → ensure mixed WAV meets −14 LUFS using `ffmpeg‑loudnorm`.

#### **Sprint 4 · Timeline & FCPXML**
- [ ] **Design Timeline‑Builder agent** → map asset_manifest to Final Cut Pro FCPXML spec.
- [ ] **Validate FCPXML** → open in FCP (manual) or use `fcpxml‑validate` CLI; document any schema fixes.
- [ ] **Emit Mix Request JSON** → handoff settings to Audio‑Mixer.

#### **Sprint 5 · Quality Control & Compliance**
- [ ] **Motion‑QC agent** → heuristic checks on clip duration, aspect ratio, duplicate frames.
- [ ] **Compliance‑QA agent** → policy prompts for copyrighted imagery & TTS consent.
- [ ] **Thumbnail‑Creator agent** → auto‑compose thumbnail PNG using first hero image + headline text.

#### **Sprint 6 · Publish & Reporting**
- [ ] **Publish‑Manager agent** → YouTube Data API upload (unlisted), set title/description/tags.
- [ ] **Reporter agent** → Slack webhook summarizing run status, video link, key metrics.
- [ ] **Observability** → ship agent logs & events to console + JSONL file; plan Grafana later.

#### **Hardening & Dev Ex**
- [ ] Add **retry/back‑off policy** decorators for fal.ai & ElevenLabs calls.
- [ ] Implement **artifact hashing & versioning** for rollback.
- [ ] Configure **pre‑commit** hooks: ruff, isort, black.
- [ ] Write **README quick‑start** with env setup, example command, expected output tree.
- [ ] Draft **unit & integration tests** covering ≥ 80 % lines; set up GitHub Actions CI (optional).

---

**Legend**

- 📂 `/agents` – individual agent modules  
- 📂 `/assets` – generated audio, images, video  
- 📂 `/tests` – pytest suites  
- `.env.example` – sample API keys file  

> ✅ Check items off in Windsurf as they’re completed; adjust scope or split tasks as needed.