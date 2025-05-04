# AI Video Automation Pipeline

An end-to-end multi-agent workflow for turning video ideas into finished AI-generated videos ready for upload to platforms like YouTube.

## Overview

This project implements a modular, traceable workflow using specialized agents to automate the video creation process. The system breaks down video production into specialized tasks handled by purpose-built agents working in both sequential and parallel patterns, with comprehensive quality control, compliance checks, and publishing capabilities.

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
ai_video_pipeline/
├── agents/                 # Individual agent modules
│   ├── executive.py        # Main orchestration agent
│   ├── ideation.py         # Topic research and ideation
│   ├── scriptwriter.py     # Script generation
│   ├── asset_creator.py    # Image and audio generation
│   ├── video_editor.py     # Timeline and editing
│   ├── motion_qc.py        # Motion quality control
│   ├── compliance_qa.py    # Content compliance checks
│   ├── thumbnail_creator.py # Thumbnail generation
│   ├── publish_manager.py  # YouTube publishing
│   └── reporter.py         # Slack reporting
├── tools/                  # Shared utilities
│   ├── observability.py    # Logging and metrics
│   └── ...
├── utils/                  # Helper utilities
│   ├── retry.py            # API retry mechanisms
│   ├── versioning.py       # Artifact versioning
│   └── ...
├── assets/                 # Generated media files
│   ├── images/
│   ├── audio/
│   ├── video/
│   └── metadata/
└── tests/                  # Pytest test suites
```

## Workflow Phases

1. **Ideation & Script**: Turn a topic prompt into an approved shooting script
2. **Asset Creation**: Generate visuals, voice, music, and metadata
3. **Assembly & Edit**: Build a video timeline, ready for rendering
4. **Quality Control**: Check motion quality and compliance issues
5. **Publish & Report**: Upload to YouTube and send status reports

## Quick Start Guide

### Prerequisites

- Python 3.9+
- OpenAI API key (for LLM-based agents)
- fal.ai API key (for image/video generation)
- ElevenLabs API key (for voice synthesis)
- YouTube API credentials (for publishing)
- Slack webhook URL (for reporting)

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

# Install pre-commit hooks (for development)
pip install pre-commit
pre-commit install

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Environment Variables

Create a `.env` file with the following variables:

```
# OpenAI
OPENAI_API_KEY=your_openai_api_key

# fal.ai
FAL_AI_KEY=your_fal_ai_key
FAL_AI_SECRET=your_fal_ai_secret

# ElevenLabs
ELEVENLABS_API_KEY=your_elevenlabs_api_key

# YouTube
YOUTUBE_CLIENT_SECRETS_FILE=path/to/client_secrets.json
YOUTUBE_CREDENTIALS_FILE=path/to/youtube_credentials.json

# Slack
SLACK_WEBHOOK_URL=your_slack_webhook_url
SLACK_CHANNEL=#your-channel-name

# Pipeline Configuration
ASSETS_DIR=./assets
OBSERVABILITY_ENABLED=true
EVENT_LOG_FILE=./events.jsonl
```

### Running the Pipeline

```bash
# Run the pipeline with a topic
python -m ai_video_pipeline --topic "The future of artificial intelligence"

# Run with additional options
python -m ai_video_pipeline \
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
│   ├── script.md              # Generated script
│   ├── manifest.json          # Asset manifest
│   ├── images/                # Generated images
│   │   ├── scene_01.png
│   │   └── ...
│   ├── audio/                 # Generated audio
│   │   ├── voiceover.mp3
│   │   └── background.mp3
│   ├── video/                 # Final video
│   │   ├── final_video.mp4
│   │   └── thumbnail.jpg
│   └── metadata/              # Process metadata
│       ├── youtube_upload.json
│       └── metrics.json
└── events.jsonl               # Event log
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
