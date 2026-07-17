import os

files_to_fix = [
    "app/core/config.py",
    "app/db/base_class.py",
    "app/models/core.py",
    "alembic/env.py",
    ".env",
    "docker-compose.yml"
]

for file_path in files_to_fix:
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Strip literal \n string from the end
        if content.endswith("\\n"):
            content = content[:-2]
            
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

print("Syntax corruption removed from all files.")
