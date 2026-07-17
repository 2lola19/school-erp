import os

backend_ignore = """venv/
__pycache__/
*.pyc
.env
.pytest_cache/
"""

frontend_ignore = """node_modules/
.next/
out/
.env.local
.env
.DS_Store
"""

root_ignore = """.env
.vscode/
"""

with open("backend/.gitignore", "w") as f: f.write(backend_ignore)
with open("frontend/.gitignore", "w") as f: f.write(frontend_ignore)
with open(".gitignore", "w") as f: f.write(root_ignore)

# Next.js auto-creates a .git folder. We must remove it to prevent a detached submodule conflict.
os.system("rmdir /s /q frontend\\.git")
os.system("rmdir /s /q backend\\.git") 

print("[+] Repositories sterilized and gitignores generated.")