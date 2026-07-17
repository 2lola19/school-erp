import os

# 1. Generate the Service Worker
os.makedirs("public", exist_ok=True)
sw_code = """
const CACHE_NAME = 'offline-read-cache-v1';
const API_PREFIX = '/api/v1/';

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(clients.claim());
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Only intercept API GET requests. Mutations bypass the SW and go to our IndexedDB queue.
  if (url.pathname.includes(API_PREFIX) && event.request.method === 'GET') {
    event.respondWith(
      fetch(event.request)
        .then((networkResponse) => {
          // Network is up. Clone and cache the successful response.
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
          return networkResponse;
        })
        .catch(async () => {
          // Network is down. Serve from cache.
          const cachedResponse = await caches.match(event.request);
          if (cachedResponse) {
            console.log('[*] Serving data from offline cache:', event.request.url);
            return cachedResponse;
          }
          // Fallback if no cache exists yet
          return new Response(JSON.stringify([]), {
            status: 200, // Return empty array to prevent UI crash
            headers: { 'Content-Type': 'application/json' }
          });
        })
    );
  }
});
"""

with open("public/sw.js", "w", encoding="utf-8") as f:
    f.write(sw_code.strip() + "\n")
print("[+] Service Worker logic generated in public directory.")

# 2. Generate the Registry Component
os.makedirs("src/components", exist_ok=True)
registry_code = """'use client';
import { useEffect } from 'react';

export function ServiceWorkerRegistry() {
  useEffect(() => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js')
        .then(reg => console.log('[+] Service Worker registered with scope:', reg.scope))
        .catch(err => console.error('[-] Service Worker registration failed:', err));
    }
  }, []);
  return null;
}
"""

with open("src/components/ServiceWorkerRegistry.tsx", "w", encoding="utf-8") as f:
    f.write(registry_code.strip() + "\n")
print("[+] Service Worker Registry component generated.")

# 3. Inject into the Dashboard
dashboard_file = "src/app/(dashboard)/school/page.tsx"
if os.path.exists(dashboard_file):
    with open(dashboard_file, "r", encoding="utf-8") as f:
        content = f.read()
        
    if "ServiceWorkerRegistry" not in content:
        # Add import
        content = content.replace(
            "import { Card", 
            "import { ServiceWorkerRegistry } from '@/components/ServiceWorkerRegistry';\nimport { Card"
        )
        # Add component to render tree
        content = content.replace(
            '<div className="p-8 min-h-screen',
            '<div className="p-8 min-h-screen">\n      <ServiceWorkerRegistry />'
        )
        
        with open(dashboard_file, "w", encoding="utf-8") as f:
            f.write(content)
        print("[+] Service Worker structurally bound to the Local Operations Plane.")
    else:
        print("[*] Service Worker already bound.")
else:
    print("[-] Critical: Could not locate school dashboard page.")