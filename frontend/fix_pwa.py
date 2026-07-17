import os

# 1. Synthesize a mathematically perfect 512x512 SVG vector icon
svg_code = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <rect width="512" height="512" rx="100" fill="#0f172a"/>
  <text x="50%" y="50%" font-family="system-ui, sans-serif" font-weight="bold" font-size="200" fill="#ffffff" text-anchor="middle" dominant-baseline="central">OP</text>
</svg>"""

with open("public/icon.svg", "w", encoding="utf-8") as f:
    f.write(svg_code)
print("[+] Vector icon synthesized locally.")

# 2. Re-bind the Manifest to the local asset
manifest_code = """{
  "name": "Local Operations Plane",
  "short_name": "OpsPlane",
  "start_url": "/school",
  "display": "standalone",
  "background_color": "#f8fafc",
  "theme_color": "#0f172a",
  "icons": [
    {
      "src": "/icon.svg",
      "sizes": "192x192",
      "type": "image/svg+xml",
      "purpose": "any maskable"
    },
    {
      "src": "/icon.svg",
      "sizes": "512x512",
      "type": "image/svg+xml",
      "purpose": "any maskable"
    }
  ]
}"""

with open("public/manifest.json", "w", encoding="utf-8") as f:
    f.write(manifest_code)
print("[+] Manifest strictly bound to local geometry.")

# 3. Force DOM Injection
layout_file = "src/app/layout.tsx"
if os.path.exists(layout_file):
    with open(layout_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Bypass Next.js metadata caching by hardcoding the link into the body if not present
    if "<link rel=" not in content:
        content = content.replace(
            '<body className={inter.className}>',
            '<head><link rel="manifest" href="/manifest.json" /></head>\n      <body className={inter.className}>'
        )
        with open(layout_file, "w", encoding="utf-8") as f:
            f.write(content)
        print("[+] Manifest strictly injected into DOM.")