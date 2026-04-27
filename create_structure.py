#!/usr/bin/env python3
"""创建FastAPI项目结构"""

import os

base_dir = r"c:\Users\林智涵\.conda\kaguya_fastapi"

structure = [
    "app/__init__.py",
    "app/main.py",
    "app/core/__init__.py",
    "app/core/config.py",
    "app/core/security.py",
    "app/core/logging.py",
    "app/models/__init__.py",
    "app/models/schemas.py",
    "app/models/database.py",
    "app/api/__init__.py",
    "app/api/v1/__init__.py",
    "app/api/v1/chat.py",
    "app/api/v1/roles.py",
    "app/api/v1/knowledge.py",
    "app/api/v1/memory.py",
    "app/api/v1/deepseek.py",
    "app/services/__init__.py",
    "app/services/llm_service.py",
    "app/services/rag_service.py",
    "app/services/memory_service.py",
    "app/services/role_service.py",
    "app/utils/__init__.py",
    "app/utils/helpers.py",
    "tests/__init__.py",
    "tests/test_api.py",
    "docs/README.md",
    "requirements.txt",
    "Dockerfile",
    "docker-compose.yml",
]

for path in structure:
    full_path = os.path.join(base_dir, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    if not path.endswith('/'):
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write('')

print("✅ FastAPI项目结构创建完成")
print(f"📁 项目路径: {base_dir}")
