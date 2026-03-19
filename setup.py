from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="rtl-gen-aii",
    version="1.0.0",
    author="RTL-Gen AI Team",
    author_email="team@rtl-gen-ai.dev",
    description="An AI-powered system for converting natural language to verified SystemVerilog RTL code",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/rtl-gen-aii/rtl-gen-aii",
    packages=find_packages(exclude=["tests*", "scripts*", "docs*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=[
        "anthropic>=0.18.0",
        "python-dotenv>=1.0.0",
        "streamlit>=1.30.0",
        "psutil>=5.9.8",
        "tqdm>=4.66.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "rtl-gen=python.__main__:main",
        ],
    },
)
