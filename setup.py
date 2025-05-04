from setuptools import setup, find_packages

setup(
    name="ai_video_pipeline",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "openai-agents-python",
        "python-dotenv",
        "pytest",
        "ruff",
    ],
    python_requires=">=3.9",
    description="An end-to-end multi-agent workflow for AI video generation",
    author="AI Video Automation Project",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
    ],
)
