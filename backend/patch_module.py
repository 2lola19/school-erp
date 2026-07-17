import os

routers_dir = os.path.join("app", "api", "v1", "routers")

# 1. Guarantee directory exists
os.makedirs(routers_dir, exist_ok=True)

# 2. Guarantee __init__.py exists to mark it as a Python module
init_file = os.path.join(routers_dir, "__init__.py")
if not os.path.exists(init_file):
    with open(init_file, "w", encoding="utf-8") as f:
        f.write("# Router package initialization\n")
    print("[+] Instantiated __init__.py in routers directory.")
else:
    print("[*] routers/__init__.py already exists.")

# 3. Check if enrollment.py is in the right place
enrollment_file = os.path.join(routers_dir, "enrollment.py")
if not os.path.exists(enrollment_file):
    print("[-] WARNING: enrollment.py is missing from the routers directory.")
    print("[-] Ensure you saved enrollment.py inside backend/app/api/v1/routers/")
else:
    print("[+] enrollment.py verified in correct location.")