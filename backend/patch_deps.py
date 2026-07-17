import os

def find_module(func_name):
    """Scans the AST/file text for the definition of a specific function."""
    for root, dirs, files in os.walk("app"):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if f"def {func_name}(" in content:
                        # Convert file path to python module format (e.g., app.api.dependencies)
                        return path.replace(os.sep, ".")[:-3]
    return None

print("[*] Scanning codebase for dependency definitions...")
db_mod = find_module("get_db")
user_mod = find_module("get_current_user")

if not db_mod or not user_mod:
    print(f"[-] Critical Error: Could not locate dependency definitions. get_db: {db_mod} | get_current_user: {user_mod}")
    exit(1)

enrollment_file = os.path.join("app", "api", "v1", "routers", "enrollment.py")

print("[*] Re-binding enrollment.py imports...")
with open(enrollment_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

with open(enrollment_file, "w", encoding="utf-8") as f:
    for line in lines:
        if "from app.api.deps import get_db, get_current_user" in line:
            if db_mod == user_mod:
                f.write(f"from {db_mod} import get_db, get_current_user\n")
            else:
                f.write(f"from {db_mod} import get_db\n")
                f.write(f"from {user_mod} import get_current_user\n")
        else:
            f.write(line)

print(f"[+] Router dependencies re-bound.")
print(f"[+] get_db -> {db_mod}")
print(f"[+] get_current_user -> {user_mod}")