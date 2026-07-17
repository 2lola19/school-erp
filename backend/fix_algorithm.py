import os

sec_path = "app/core/security.py"

if os.path.exists(sec_path):
    with open(sec_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace the failed config lookup with the hardcoded standard string
    content = content.replace("settings.ALGORITHM", '"HS256"')

    with open(sec_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print("[+] Encryption algorithm hardcoded to HS256.")
else:
    print("[-] Could not find app/core/security.py")