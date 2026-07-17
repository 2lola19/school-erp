import os

target_file = "docker-compose.yml"

if os.path.exists(target_file):
    with open(target_file, "r", encoding="utf-8") as f:
        content = f.read()
        
    patched_content = content.replace('- "5432:5432"', '- "5433:5432"')
    
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(patched_content)
    print("[+] Port collision bypassed. Database host mapping shifted to 5433.")
else:
    print("[-] Critical error: Could not locate docker-compose.yml.")