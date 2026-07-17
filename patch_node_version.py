import os

frontend_dockerfile_path = "frontend/Dockerfile"

if os.path.exists(frontend_dockerfile_path):
    with open(frontend_dockerfile_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Replace Node 18 with Node 20
    patched_content = content.replace("FROM node:18-alpine", "FROM node:20-alpine")
    
    with open(frontend_dockerfile_path, "w", encoding="utf-8") as f:
        f.write(patched_content)
    print("[+] Frontend Dockerfile upgraded to Node 20 Alpine.")
else:
    print("[-] Critical error: Could not locate frontend/Dockerfile.")