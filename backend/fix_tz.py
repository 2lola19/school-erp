import os

files = [
    "app/db/base_class.py",
    "app/models/core.py"
]

for path in files:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Strip timezone metadata from the datetime generation
    content = content.replace("datetime.now(timezone.utc)", "datetime.now(timezone.utc).replace(tzinfo=None)")
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

print("Timezone mismatch resolved.")
