import os
import re

# 1. Introspect the dependencies file
dep_file = os.path.join("app", "api", "v1", "dependencies.py")
with open(dep_file, "r", encoding="utf-8") as f:
    deps_content = f.read()

# 2. Extract exact function names using resilient regex
db_match = re.search(r'(?:async\s+)?def\s+(get_db|get_session|get_async_session)\b', deps_content)
user_match = re.search(r'(?:async\s+)?def\s+(get_current[a-zA-Z_0-9]*user)\b', deps_content)

db_func = db_match.group(1) if db_match else "get_db"
user_func = user_match.group(1) if user_match else "get_current_user"

print(f"[*] Database injection mapped to: {db_func}")
print(f"[*] Authentication injection mapped to: {user_func}")

# 3. Patch the router
enrollment_file = os.path.join("app", "api", "v1", "routers", "enrollment.py")
with open(enrollment_file, "r", encoding="utf-8") as f:
    text = f.read()

target = "from app.api.deps import get_db, get_current_user"
replacement = f"from app.api.v1.dependencies import {db_func} as get_db, {user_func} as get_current_user"

if target in text:
    text = text.replace(target, replacement)
else:
    # Force replacement if partially modified
    text = re.sub(r'from .* import get_db, get_current_user', replacement, text)

with open(enrollment_file, "w", encoding="utf-8") as f:
    f.write(text)

print("[+] Router imports mathematically realigned via aliasing.")