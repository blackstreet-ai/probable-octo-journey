# AI Video Automation Pipeline

An end-to-end multi-agent workflow for turning video ideas into finished AI-generated videos ready for upload to platforms like YouTube, powered by the OpenAI Assistants API.

## Overview

This project implements a modular, traceable workflow using specialized agents built with the OpenAI Assistants API to automate the video creation process. The system breaks down video production into specialized tasks handled by purpose-built agents working in both sequential and parallel patterns, with comprehensive quality control, compliance checks, and publishing capabilities.

## Features

- **Ideation & Scripting**: Convert topic ideas into fully-formed video scripts
- **Asset Generation**: Create AI-generated visuals, voiceovers, and music
- **Video Assembly**: Automatically build and edit video timelines
- **Quality Control**: Check for motion quality issues and compliance violations
- **Publishing**: Upload to YouTube with proper metadata
- **Reporting**: Send status reports and notifications via Slack
- **Observability**: Track events and metrics throughout the pipeline

## Project Structure

```
/
├── agents/                     # Individual agent modules using OpenAI Assistants API
│   ├── video_orchestrator.py   # Main controller for coordinating sub-agents
│   ├── script_rewriter.py      # Enhances raw transcripts into polished scripts
│   ├── voiceover.py            # Synthesizes narration using ElevenLabs
│   ├── music_supervisor.py     # Selects and processes background music
│   ├── visual_composer.py      # Generates visuals based on video scripts
│   ├── video_editor.py         # Assembles final videos with all assets
│   ├── publish_manager.py      # Handles YouTube uploads and metadata
│   └── reporter.py             # Generates reports and sends notifications
├── prompts/                    # YAML prompt templates for agents
│   ├── video_orchestrator.yaml
│   ├── script_rewriter.yaml
│   └── ...
├── tools/                      # Shared utilities
│   ├── token_manager.py        # API key validation and rotation
│   ├── observability.py        # Logging and metrics
│   └── ...
├── tests/                      # Pytest test suites
│   ├── test_video_orchestrator.py
│   ├── test_script_rewriter.py
│   ├── mocks/                  # Mock implementations for testing
│   │   ├── elevenlabs_mock.py
│   │   └── dalle_mock.py
│   └── conftest.py             # Pytest configuration
├── config.py                   # Configuration management
├── pipeline.py                 # Main pipeline orchestration
└── launch.py                   # CLI entrypoint
```

## Workflow Phases

1. **Orchestration & Initialization**: The VideoOrchestratorAgent initializes the job and creates a manifest to track progress
2. **Script Creation**: The ScriptRewriterAgent transforms a topic into a structured video script with scene breakdowns
3. **Script Review**: The VideoOrchestratorAgent reviews the script for quality and structure
4. **Asset Generation**: Multiple agents work in parallel:
   - VoiceoverAgent extracts and synthesizes narration from the script
   - MusicSupervisorAgent selects and processes background music
   - VisualComposerAgent generates visuals based on script descriptions
5. **Video Assembly**: The VideoEditorAgent creates an edit plan and assembles the final video
6. **Quality Control**: The VideoOrchestratorAgent reviews the final video for quality
7. **Publishing**: The PublishManagerAgent prepares metadata and uploads to YouTube
8. **Reporting**: The ReporterAgent generates reports and sends notifications

## Quick Start Guide

### Prerequisites

- Python 3.9+
- OpenAI API key (with access to the Assistants API)
- ElevenLabs API key (for voice synthesis)
- YouTube API credentials (for publishing, optional)
- Slack webhook URL (for reporting, optional)

### Installation

```bash
# Clone the repository
git clone https://github.com/blackstreet-ai/probable-octo-journey.git
cd probable-octo-journey

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# For development and testing
pip install -e ".[dev]"

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Environment Variables

Create a `.env` file with the following variables:

```
# OpenAI
OPENAI_API_KEY=your_openai_api_key

# ElevenLabs
ELEVENLABS_API_KEY=your_elevenlabs_api_key

# YouTube (optional)
YOUTUBE_CLIENT_SECRETS_FILE=path/to/client_secrets.json
YOUTUBE_CREDENTIALS_FILE=path/to/youtube_credentials.json

# Slack (optional)
SLACK_WEBHOOK_URL=your_slack_webhook_url
SLACK_CHANNEL=#your-channel-name

# Pipeline Configuration
OUTPUT_DIR=./output
LOG_LEVEL=INFO
```

### Running the Pipeline

```bash
# Run the pipeline with a topic
python launch.py --topic "The future of artificial intelligence"

# Run with additional options
python launch.py \
  --topic "The future of artificial intelligence" \
  --output-dir ./my_videos \
  --publish \
  --notify
```

### Expected Output

When the pipeline completes successfully, you'll find the following in your output directory:

```
output/
├── job_123456/                # Unique job ID folder
│   ├── manifest.json          # Job manifest with status tracking
│   ├── scripts/               # Generated scripts
│   │   └── script.md          # Final approved script
│   ├── audio/                 # Audio files
│   │   └── voiceover.mp3      # Synthesized narration
│   ├── music/                 # Music files
│   │   ├── original.mp3       # Selected background music
│   │   └── processed.mp3      # Processed music (volume adjusted, etc.)
│   ├── visuals/               # Generated images
│   │   ├── image_1.png        # Visual for scene 1
│   │   ├── image_2.png        # Visual for scene 2
│   │   └── ...
│   ├── videos/                # Generated videos
│   │   ├── edit_plan.md       # Video editing plan
│   │   └── final_video.mp4    # Final assembled video
│   └── reports/               # Generated reports
       └── final_report.json  # Pipeline execution report
```

## Development

### Code Quality Tools

This project uses the following tools for code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **Ruff**: Fast Python linter
- **mypy**: Static type checking

These tools are configured in `pyproject.toml` and run automatically via pre-commit hooks.

### Running Tests

```bash
# Run all tests
python -m pytest

# Run tests with coverage
python -m pytest --cov=ai_video_pipeline

# Run specific test modules
python -m pytest tests/test_executive.py
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
