import os

target_file = "src/lib/api-client.ts"

if os.path.exists(target_file):
    with open(target_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # We append a robust interceptor that guarantees the token is pulled from storage
    # right before the request leaves the browser.
    override = """
// [HOTFIX] Force inject token directly from browser storage to bypass Zustand desync
apiClient.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const rawToken = localStorage.getItem('access_token') || localStorage.getItem('token');
    if (rawToken) {
      config.headers.Authorization = `Bearer ${rawToken}`;
    }
  }
  return config;
});
"""
    if "HOTFIX" not in content:
        with open(target_file, "a", encoding="utf-8") as f:
            f.write("\n" + override)
        print("[+] API Client patched. Axios will now extract tokens directly from local storage.")
    else:
        print("[*] API Client already patched.")
else:
    print(f"[-] Critical: Could not locate {target_file}")