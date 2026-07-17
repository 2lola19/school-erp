import os

ui_code = """'use client';
import { useEffect, useState } from 'react';
import { useAuthStore } from '@/store/authStore';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface Tenant {
  id: string;
  name: string;
  domain: string;
  created_at: string;
}

export default function SuperAdminDashboard() {
  const { logout } = useAuthStore();
  const router = useRouter();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchTenants = async () => {
      try {
        const res = await apiClient.get('/tenants/');
        setTenants(res.data);
      } catch (err: any) {
        if (err.response?.status === 403) {
          setError('403 Forbidden: Permissions missing from JWT. Please click Disconnect and log in again.');
        } else {
          setError(err.response?.data?.detail || 'Failed to fetch tenants');
        }
      }
    };
    fetchTenants();
  }, []);

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  return (
    <div className="p-8 min-h-screen bg-slate-50 space-y-6">
      <div className="flex justify-between items-center max-w-5xl mx-auto">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">System Dashboard</h1>
        <Button onClick={handleLogout} variant="destructive">Disconnect</Button>
      </div>

      <Card className="max-w-5xl mx-auto">
        <CardHeader>
          <CardTitle>Provisioned Tenants</CardTitle>
        </CardHeader>
        <CardContent>
          {error && <p className="text-red-500 mb-4 font-medium p-3 bg-red-50 rounded-md border border-red-200">{error}</p>}
          <div className="rounded-md border overflow-hidden">
            <table className="w-full text-sm text-left">
              <thead className="bg-slate-100 text-slate-700 border-b">
                <tr>
                  <th className="p-4 font-medium">Tenant Name</th>
                  <th className="p-4 font-medium">Domain</th>
                  <th className="p-4 font-medium">Created</th>
                  <th className="p-4 font-medium">Tenant ID</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {tenants.map((t) => (
                  <tr key={t.id} className="bg-white hover:bg-slate-50 transition-colors">
                    <td className="p-4 font-medium text-slate-900">{t.name}</td>
                    <td className="p-4 text-slate-600">{t.domain}</td>
                    <td className="p-4 text-slate-600">{new Date(t.created_at).toLocaleDateString()}</td>
                    <td className="p-4 text-slate-500 font-mono text-xs">{t.id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
"""

with open("src/app/(dashboard)/superadmin/page.tsx", "w", encoding="utf-8") as f:
    f.write(ui_code)
    
print("[+] Frontend Dashboard connected to Tenant API.")