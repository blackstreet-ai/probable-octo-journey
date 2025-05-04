from setuptools import setup, find_packages

setup(
    name="ai_video_automation",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "openai>=1.3.0",  # OpenAI API client for Assistants API
        "python-dotenv>=1.0.0",  # Environment variable management
        "pydantic>=2.0.0",  # Data validation
        "PyYAML>=6.0",  # YAML parsing for prompt templates
        "ffmpeg-python>=0.2.0",  # FFmpeg Python bindings
        "structlog>=23.1.0",  # Structured logging
        "rich>=13.3.5",  # Rich terminal output
    ],
    extras_require={
        "dev": [
            "pytest>=7.3.1",  # Testing framework
            "ruff>=0.0.270",  # Fast linter
            "black>=23.3.0",  # Code formatter
            "mypy>=1.3.0",  # Static type checking
        ],
    },
    python_requires=">=3.9",
    description="An end-to-end multi-agent workflow for AI video generation using OpenAI Assistants API",
    author="AI Video Automation Project",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
    ],
)
