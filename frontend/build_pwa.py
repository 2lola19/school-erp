import os

# 1. Generate the Manifest
manifest_code = """{
  "name": "Local Operations Plane",
  "short_name": "OpsPlane",
  "start_url": "/school",
  "display": "standalone",
  "background_color": "#f8fafc",
  "theme_color": "#0f172a",
  "icons": [
    {
      "src": "https://www.google.com/s2/favicons?sz=192&domain=localhost",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "https://www.google.com/s2/favicons?sz=512&domain=localhost",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}"""

with open("public/manifest.json", "w", encoding="utf-8") as f:
    f.write(manifest_code)
print("[+] Manifest payload written to public directory.")

# 2. Inject Manifest into Next.js Metadata
layout_file = "src/app/layout.tsx"
if os.path.exists(layout_file):
    with open(layout_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    if "manifest:" not in content and "export const metadata" in content:
        patched_content = content.replace(
            "export const metadata: Metadata = {",
            "export const metadata: Metadata = {\n  manifest: '/manifest.json',"
        )
        with open(layout_file, "w", encoding="utf-8") as f:
            f.write(patched_content)
        print("[+] Manifest structurally bound to application layout.")
    else:
        print("[*] Manifest already bound or metadata structure unrecognized.")
else:
    print("[-] Critical: Could not locate src/app/layout.tsx")