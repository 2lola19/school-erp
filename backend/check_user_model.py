import os

model_path = "app/models/core.py"

if os.path.exists(model_path):
    with open(model_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    print("--- User Model Content ---")
    for line in content.splitlines():
        if "class User" in line:
            print(line)
        elif "password" in line.lower():
            print(line)
else:
    print("[-] Could not find app/models/core.py")