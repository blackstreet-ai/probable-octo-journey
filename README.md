# AI Video Automation Pipeline

An end-to-end multi-agent workflow for turning video ideas into finished AI-generated videos ready for upload.

## Overview

This project implements a modular, traceable workflow using the OpenAI Agents SDK to automate the video creation process. The system breaks down video production into specialized tasks handled by purpose-built agents working in both sequential and parallel patterns.

## Project Structure

- `/agents` - Individual agent modules
- `/assets` - Generated audio, images, video
- `/tests` - Pytest suites
- `.env.example` - Sample API keys file

## Workflow Phases

1. **Ideation & Script**: Turn a topic prompt into an approved shooting script
2. **Asset Creation**: Generate visuals, voice, music, and metadata
3. **Assembly & Edit**: Build an FCPXML timeline, ready for rendering
4. **QA & Publish**: Final compliance, thumbnail, upload, status report

## Getting Started

### Prerequisites

- Python 3.9+
- OpenAI API key
- fal.ai API key (for image/video generation)
- ElevenLabs API key (for voice synthesis)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-video-pipeline.git
cd ai-video-pipeline

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Running the Pipeline

```bash
python -m ai_video_pipeline --topic "Your video topic here"
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
