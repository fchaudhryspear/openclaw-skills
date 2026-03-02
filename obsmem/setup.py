from setuptools import setup, find_packages

setup(
    name="obsmem",
    version="0.1.0",
    description="Security-focused Observational Memory system for AI agents",
    author="Faisal",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "cryptography>=42.0.0",
    ],
    extras_require={
        "test": [
            "pytest>=7.0.0",
        ],
    },
)
