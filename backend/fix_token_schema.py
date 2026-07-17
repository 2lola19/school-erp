import os

schema_path = "app/schemas/auth.py"
if os.path.exists(schema_path):
    with open(schema_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Align the schema key with the JWT encoder
    content = content.replace("role_id: str", "role: str")

    with open(schema_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] Token payload schema aligned.")
else:
    print("[-] Schema file not found.")