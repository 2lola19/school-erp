import os

req_file = "backend/requirements.txt"

if os.path.exists(req_file):
    with open(req_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    if "bcrypt==3.2.2" not in content:
        with open(req_file, "a", encoding="utf-8") as f:
            f.write("\nbcrypt==3.2.2\n")
        print("[+] Cryptographic dependency strictly pinned to 3.2.2.")
    else:
        print("[*] Dependency already pinned.")
else:
    print("[-] Critical error: Could not locate backend/requirements.txt.")