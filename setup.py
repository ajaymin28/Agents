"""
Setup script for the Ollama Agent Framework.

This script handles the installation of the Ollama Agent Framework and its dependencies.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ollama-agent-framework",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A flexible agent framework for working with Ollama models",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/ollama-agent-project",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "fastapi>=0.95.0",
        "uvicorn>=0.21.0",
        "pydantic>=1.10.7",
        "aiohttp>=3.8.4",
        "python-multipart>=0.0.6",
        "psutil>=5.9.5",
        "Pillow>=9.5.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
        ],
    },
)
