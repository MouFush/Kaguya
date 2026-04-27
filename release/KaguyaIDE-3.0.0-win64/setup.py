#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name="kaguya-ide",
    version="3.0.0",
    packages=find_packages(include=["kaguya_core*", "kaguya_*"]),
    py_modules=[
        "qwen3_web",
        "ollama_adapter",
        "start_server",
        "kaguya_bootstrap",
        "kaguya_acp",
        "kaguya_agents",
        "kaguya_skills",
        "kaguya_accounts",
        "kaguya_frontend",
        "kaguya_permissions",
        "kaguya_hooks",
        "kaguya_feature_flags",
        "kaguya_memory",
        "kaguya_thinking",
        "kaguya_tool_system",
        "kaguya_file_history",
        "kaguya_compaction",
        "kaguya_terminal",
    ],
    include_package_data=True,
    package_data={
        "": ["*.html", "*.css", "*.js", "*.json", "*.db"],
        "static": ["*"],
        "data": ["*"],
    },
    entry_points={
        "console_scripts": [
            "kaguya-ide=start_server:main",
        ],
    },
    install_requires=[
        "flask>=2.3.0",
        "numpy>=1.24.0",
        "scikit-learn>=1.3.0",
    ],
)
