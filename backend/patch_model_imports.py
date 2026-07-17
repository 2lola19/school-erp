import os

target_file = "app/models/core.py"

with open(target_file, "r", encoding="utf-8") as f:
    content = f.read()

# Define the exhaustive list of required dependencies
safe_imports = """
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID
"""

if "class Teacher(Base):" in content:
    # Strip the partial import injected previously
    content = content.replace("from sqlalchemy import Date", "")
    
    # Inject the complete dependency matrix directly above the new classes
    parts = content.split("class Teacher(Base):")
    new_content = parts[0] + safe_imports + "\nclass Teacher(Base):" + parts[1]
    
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("[+] Core schema dependencies safely injected.")
else:
    print("[-] Could not locate Teacher class. File may be corrupted.")