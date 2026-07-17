import os

def find_and_patch_router():
    for root, _, files in os.walk("app"):
        for filename in files:
            if filename.endswith(".py"):
                filepath = os.path.join(root, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Look for the file that wires the tenant routes
                if "tenant.router" in content and "include_router" in content:
                    print(f"[*] Found router configuration in: {filepath}")
                    
                    if "students.router" in content:
                        print("[*] Students router is already registered.")
                        return

                    # 1. Update the imports
                    if "from app.api.v1.endpoints import" in content:
                        content = content.replace(
                            "from app.api.v1.endpoints import auth, tenant", 
                            "from app.api.v1.endpoints import auth, tenant, students"
                        )
                        content = content.replace(
                            "from app.api.v1.endpoints import tenant", 
                            "from app.api.v1.endpoints import tenant, students"
                        )
                    else:
                        content = "from app.api.v1.endpoints import students\n" + content

                    # 2. Clone the tenant route registration and adapt it for students
                    lines = content.split('\n')
                    new_lines = []
                    for line in lines:
                        new_lines.append(line)
                        if "tenant.router" in line and "include_router" in line:
                            student_line = line.replace("tenant.router", "students.router") \
                                               .replace("tenants", "students") \
                                               .replace("Tenants", "Students")
                            new_lines.append(student_line)
                    
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write('\n'.join(new_lines))
                    
                    print("[+] Students router dynamically wired into the application.")
                    return
                    
    print("[-] Critical: Could not locate the router registration file.")

find_and_patch_router()