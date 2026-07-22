'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { WorkspaceSwitcher } from '@/components/WorkspaceSwitcher';
import { apiClient } from '@/lib/api-client';
import { useAuthStore } from '@/store/authStore';

interface Tenant { id: string; name: string; domain: string }

export default function SuperAdminDashboard() {
  const router = useRouter();
  const { initialized, logout, profile } = useAuthStore();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [name, setName] = useState('');
  const [domain, setDomain] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const loadTenants = async () => {
    try { setTenants((await apiClient.get<Tenant[]>('/tenants/')).data); }
    catch { setError('Tenant directory could not be loaded.'); }
  };

  useEffect(() => {
    if (initialized && !profile) {
      router.replace('/login');
      return;
    }
    if (!profile) return;
    let active = true;
    apiClient.get<Tenant[]>('/tenants/')
      .then((response) => { if (active) setTenants(response.data); })
      .catch(() => { if (active) setError('Tenant directory could not be loaded.'); });
    return () => { active = false; };
  }, [initialized, profile, router]);

  const createTenant = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      await apiClient.post('/tenants/', { name, domain });
      setName('');
      setDomain('');
      await loadTenants();
    } catch (caught: unknown) {
      const response = caught as { response?: { data?: { detail?: string } } };
      setError(response.response?.data?.detail ?? 'Tenant provisioning failed.');
    } finally { setSubmitting(false); }
  };

  const handleLogout = async () => {
    try { await apiClient.post('/auth/logout'); } finally {
      logout();
      router.replace('/login');
    }
  };

  if (!initialized || !profile) return <main className="p-8">Loading platform workspace…</main>;

  return (
    <main className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto max-w-5xl space-y-6">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div><p className="text-sm text-slate-500">Platform administration</p><h1 className="text-3xl font-bold">School ERP tenants</h1></div>
          <div className="flex items-center gap-3"><WorkspaceSwitcher /><Button variant="outline" onClick={handleLogout}>Sign out</Button></div>
        </header>
        {error && <p role="alert" className="rounded-md border border-red-200 bg-red-50 p-3 text-red-700">{error}</p>}
        {profile.permissions.includes('plans.read') && <Card><CardHeader><CardTitle>Subscription control</CardTitle></CardHeader><CardContent><Button onClick={() => router.push('/superadmin/subscriptions')}>Manage plans and tenant subscriptions</Button></CardContent></Card>}
        <Card>
          <CardHeader><CardTitle>Provision institution</CardTitle></CardHeader>
          <CardContent>
            <form onSubmit={createTenant} className="grid gap-4 md:grid-cols-[1fr_1fr_auto] md:items-end">
              <label className="text-sm font-medium">Institution name<input required value={name} onChange={(event) => setName(event.target.value)} className="mt-1 h-10 w-full rounded-md border px-3" /></label>
              <label className="text-sm font-medium">Domain<input required pattern="[a-z0-9.-]+" value={domain} onChange={(event) => setDomain(event.target.value.toLowerCase())} className="mt-1 h-10 w-full rounded-md border px-3" /></label>
              <Button type="submit" disabled={submitting}>{submitting ? 'Creating…' : 'Create tenant'}</Button>
            </form>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Active tenants</CardTitle></CardHeader>
          <CardContent>
            <div className="divide-y rounded-md border bg-white">
              {tenants.map((tenant) => <div key={tenant.id} className="flex justify-between p-4"><span className="font-medium">{tenant.name}</span><span className="text-slate-500">{tenant.domain}</span></div>)}
              {!tenants.length && <p className="p-6 text-center text-slate-500">No tenants have been provisioned.</p>}
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
