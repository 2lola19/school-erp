import os

core_file = os.path.join("app", "models", "core.py")

with open(core_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

has_func = any("func" in line and "sqlalchemy" in line for line in lines)

if not has_func:
    for i, line in enumerate(lines):
        if line.startswith("from sqlalchemy") or line.startswith("import sqlalchemy"):
            lines.insert(i, "from sqlalchemy.sql import func\n")
            break
    else:
        lines.insert(0, "from sqlalchemy.sql import func\n")

    with open(core_file, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("[+] 'func' dependency mathematically injected.")
else:
    print("[*] 'func' dependency already exists.")