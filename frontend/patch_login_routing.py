import os
import glob
import re

# 1. Locate the login file
login_files = glob.glob("src/app/**/login/page.tsx", recursive=True)
if not login_files:
    print("[-] Critical: Could not locate login page.tsx.")
    exit(1)

login_file = login_files[0]

with open(login_file, "r", encoding="utf-8") as f:
    content = f.read()

# 2. Patch the hardcoded route with payload introspection
push_pattern = r"router\.push\(['\"]/superadmin['\"]\);?"

routing_logic = """
          // Decode JWT payload
          const tokenStr = res.data.access_token || res.data.token;
          const base64Url = tokenStr.split('.')[1];
          const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
          const payload = JSON.parse(window.atob(base64));

          if (payload.permissions && payload.permissions.includes('view_all_tenants')) {
            router.push('/superadmin');
          } else {
            router.push('/school');
          }
"""

if re.search(push_pattern, content):
    content = re.sub(push_pattern, routing_logic.strip(), content)
    with open(login_file, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] Login routing dynamically bifurcated.")
else:
    print("[-] Target route not found. File may already be patched.")

# 3. Scaffold the isolated school dashboard
os.makedirs("src/app/(dashboard)/school", exist_ok=True)
school_code = """'use client';
import { useAuthStore } from '@/store/authStore';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function SchoolDashboard() {
  const { logout } = useAuthStore();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  return (
    <div className="p-8 min-h-screen bg-slate-50 space-y-6">
      <div className="flex justify-between items-center max-w-5xl mx-auto">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Local School Administration</h1>
        <Button onClick={handleLogout} variant="destructive">Disconnect</Button>
      </div>
      <Card className="max-w-5xl mx-auto">
        <CardHeader>
          <CardTitle>Operations Control</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-slate-600 font-medium">
            Authorization Confirmed. You are securely bound to your local institution. Central system access is locked.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
"""

with open("src/app/(dashboard)/school/page.tsx", "w", encoding="utf-8") as f:
    f.write(school_code)
    
print("[+] Local School dashboard scaffolded.")