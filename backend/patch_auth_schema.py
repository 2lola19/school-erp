import os
import re

target_file = "app/schemas/auth.py"

if os.path.exists(target_file):
    with open(target_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Convert the strict requirement into an optional default string
    patched_content = re.sub(r"domain:\s*str\b", 'domain: str = ""', content)

    if content != patched_content:
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(patched_content)
        print("[+] Auth schema repaired. Ghost domain constraint neutralized.")
    else:
        print("[*] No strict domain constraint found. File may already be patched.")
else:
    print("[-] Critical: Could not locate app/schemas/auth.py")