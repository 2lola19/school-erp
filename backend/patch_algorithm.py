import os

target_file = "app/api/v1/endpoints/auth.py"

if os.path.exists(target_file):
    with open(target_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Replace the failed settings call with a hardcoded string
    if "settings.ALGORITHM" in content:
        patched_content = content.replace("settings.ALGORITHM", '"HS256"')
        
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(patched_content)
        print("[+] Token generator patched. HS256 algorithm hardcoded.")
    else:
        print("[*] Target string not found. File may already be patched.")
else:
    print("[-] Critical: Could not locate auth.py")