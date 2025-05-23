# AI Video Automation Pipeline

An end-to-end multi-agent workflow for turning video ideas into finished AI-generated videos ready for upload to platforms like YouTube, powered by the OpenAI Assistants API.

## Overview

This project implements a modular, traceable workflow using specialized agents built with the OpenAI Assistants API to automate the video creation process. The system breaks down video production into specialized tasks handled by purpose-built agents working in both sequential and parallel patterns, with comprehensive quality control, compliance checks, and publishing capabilities.

## Features

- **Ideation & Scripting**: Convert topic ideas into fully-formed video scripts with research-backed content
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
│   ├── script_generator.py     # Creates structured scripts from templates
│   ├── research.py             # Performs web research for accurate content
│   ├── voiceover.py            # Synthesizes narration using ElevenLabs
│   ├── music_supervisor.py     # Selects and processes background music
│   ├── visual_composer.py      # Generates visuals based on video scripts
│   ├── video_editor.py         # Assembles final videos with all assets
│   ├── publish_manager.py      # Handles YouTube uploads and metadata
│   └── reporter.py             # Generates reports and sends notifications
├── prompts/                    # YAML prompt templates for agents
│   ├── video_orchestrator.yaml
│   ├── script_generator.yaml
│   ├── templates/              # Script templates for different formats
│   │   ├── narration.yaml      # Template for single-voice narration
│   │   ├── interview.yaml      # Template for host-guest format
│   │   └── news_report.yaml    # Template for journalistic scripts
│   └── ...
├── tools/                      # Shared utilities
│   ├── token_manager.py        # API key validation and rotation
│   ├── observability.py        # Logging and metrics
│   ├── script_validator.py     # Validates script formatting and structure
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
2. **Research**: The ResearchAgent gathers accurate information on the topic from reliable sources
3. **Script Creation**: The ScriptGeneratorAgent creates a structured script using research and templates
4. **Script Validation**: The system validates script formatting, structure, and content quality
5. **Fact Checking**: The ResearchAgent verifies factual accuracy and generates citations
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

# Run with script format and research depth options
python launch.py --topic "Renewable Energy" --script-format narration --research-depth deep

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
│   ├── research/              # Research materials
│   │   ├── research.md        # Topic research findings
│   │   ├── fact_check.md      # Fact checking results
│   │   └── citations.md       # Source citations
│   ├── script/                # Generated scripts
│   │   ├── narration_script.md # Final approved script
│   │   └── script_history/    # Version history of script revisions
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

## Script Validation System

The pipeline includes a comprehensive script validation system that ensures all generated scripts meet quality standards:

### Validation Features

- **Structure Validation**: Ensures scripts contain all required sections (introduction, main content, conclusion)
- **Section Length Checks**: Verifies that sections aren't too short or too long
- **Metadata Validation**: Confirms presence of target audience, tone, and duration information
- **Formatting Validation**: Checks line lengths and proper markdown formatting

### Automatic Issue Fixing

The system can automatically fix common formatting issues:

- Corrects heading levels for consistency
- Adds missing metadata sections
- Breaks long lines for better readability
- Ensures proper markdown formatting

### Integration

Validation is integrated into all script-related methods:

```python
# Example validation usage in script generation
from tools.script_validator import ScriptValidator

validator = ScriptValidator()
is_valid, issues = validator.validate_script(script_content, "narration")

if not is_valid:
    # Attempt to fix formatting issues
    fixed_script = validator.fix_script_formatting(script_content)
    # Re-validate
    is_valid, remaining_issues = validator.validate_script(fixed_script, "narration")
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
