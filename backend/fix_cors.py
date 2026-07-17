import os

main_path = "app/main.py"
if os.path.exists(main_path):
    with open(main_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Restrict allowed origins to explicitly permit the local frontend
    content = content.replace(
        'allow_origins=["*"]',
        'allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"]'
    )
    
    with open(main_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] CORS policy patched successfully.")
else:
    print("[-] Could not find app/main.py")