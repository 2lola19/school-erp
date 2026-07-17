'use client';
import { useEffect, useState } from 'react';
import { useAuthStore } from '@/store/authStore';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

// 1. Import the Telemetry Component
import DashboardStats from '@/components/DashboardStats';

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
  
  // Tenant Form State
  const [name, setName] = useState('');
  const [domain, setDomain] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Admin Form State
  const [activeTenant, setActiveTenant] = useState<Tenant | null>(null);
  const [adminForm, setAdminForm] = useState({ first_name: '', last_name: '', email: '', password: '' });
  const [adminStatus, setAdminStatus] = useState({ error: '', success: '', submitting: false });

  const fetchTenants = async () => {
    try {
      const res = await apiClient.get('/tenants/');
      setTenants(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch tenants');
    }
  };

  useEffect(() => {
    fetchTenants();
  }, []);

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  const handleCreateTenant = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError('');
    try {
      await apiClient.post('/tenants/', { name, domain });
      setName('');
      setDomain('');
      fetchTenants();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to provision tenant');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateAdmin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeTenant) return;
    
    setAdminStatus({ error: '', success: '', submitting: true });
    try {
      await apiClient.post(`/tenants/${activeTenant.id}/admin`, adminForm);
      setAdminStatus({ error: '', success: 'School Admin provisioned successfully.', submitting: false });
      setAdminForm({ first_name: '', last_name: '', email: '', password: '' });
      setTimeout(() => {
        setActiveTenant(null);
        setAdminStatus(prev => ({ ...prev, success: '' }));
      }, 2000);
    } catch (err: any) {
      setAdminStatus({ error: err.response?.data?.detail || 'Failed to create admin', success: '', submitting: false });
    }
  };

  return (
    <div className="p-8 min-h-screen bg-slate-50 space-y-6 relative">
      <div className="flex justify-between items-center max-w-5xl mx-auto">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">System Dashboard</h1>
        <Button onClick={handleLogout} variant="destructive">Disconnect</Button>
      </div>

      {/* 2. Mount the Telemetry Component directly below the header */}
      <div className="max-w-5xl mx-auto">
        <DashboardStats />
      </div>

      <Card className="max-w-5xl mx-auto mb-6">
        <CardHeader>
          <CardTitle>Provision New Institution</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreateTenant} className="flex gap-4 items-end">
            <div className="flex-1">
              <label className="block text-sm font-medium mb-1">Institution Name</label>
              <input required value={name} onChange={e => setName(e.target.value)} className="w-full p-2 border rounded-md" placeholder="University of Ilorin" />
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium mb-1">Domain</label>
              <input required value={domain} onChange={e => setDomain(e.target.value)} className="w-full p-2 border rounded-md" placeholder="unilorin.edu.ng" />
            </div>
            <Button type="submit" disabled={isSubmitting}>Provision</Button>
          </form>
        </CardContent>
      </Card>

      <Card className="max-w-5xl mx-auto">
        <CardHeader>
          <CardTitle>Active Tenants</CardTitle>
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
                  <th className="p-4 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {tenants.map((t) => (
                  <tr key={t.id} className="bg-white hover:bg-slate-50 transition-colors">
                    <td className="p-4 font-medium text-slate-900">{t.name}</td>
                    <td className="p-4 text-slate-600">{t.domain}</td>
                    <td className="p-4 text-slate-600">{new Date(t.created_at).toLocaleDateString()}</td>
                    <td className="p-4 text-right">
                      <Button variant="outline" size="sm" onClick={() => setActiveTenant(t)}>Add Admin</Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Admin Provisioning Modal */}
      {activeTenant && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md shadow-xl">
            <CardHeader>
              <CardTitle>Provision Admin for {activeTenant.name}</CardTitle>
            </CardHeader>
            <CardContent>
              {adminStatus.error && <p className="text-red-500 mb-4 text-sm font-medium p-2 bg-red-50 rounded">{adminStatus.error}</p>}
              {adminStatus.success && <p className="text-green-600 mb-4 text-sm font-medium p-2 bg-green-50 rounded">{adminStatus.success}</p>}
              
              <form onSubmit={handleCreateAdmin} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">First Name</label>
                    <input required value={adminForm.first_name} onChange={e => setAdminForm({...adminForm, first_name: e.target.value})} className="w-full p-2 border rounded-md" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Last Name</label>
                    <input required value={adminForm.last_name} onChange={e => setAdminForm({...adminForm, last_name: e.target.value})} className="w-full p-2 border rounded-md" />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Admin Email</label>
                  <input required type="email" value={adminForm.email} onChange={e => setAdminForm({...adminForm, email: e.target.value})} className="w-full p-2 border rounded-md" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Temporary Password</label>
                  <input required type="password" value={adminForm.password} onChange={e => setAdminForm({...adminForm, password: e.target.value})} className="w-full p-2 border rounded-md" />
                </div>
                <div className="flex justify-end gap-2 mt-6">
                  <Button type="button" variant="outline" onClick={() => setActiveTenant(null)}>Cancel</Button>
                  <Button type="submit" disabled={adminStatus.submitting}>Create Admin</Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}