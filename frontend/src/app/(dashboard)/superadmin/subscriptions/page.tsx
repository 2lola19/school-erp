'use client';

import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { apiClient } from '@/lib/api-client';

interface Plan { id: string; code: string; name: string; is_public: boolean; is_active: boolean; currency: string; base_price: string }
interface TenantSubscription { tenant_id: string; tenant_name: string; subscription_id: string; plan_code: string; status: string; entitlement_version: number }
interface Feature { id: string; code: string; name: string; value_type: string; is_metered: boolean; is_active: boolean }

export default function PlatformSubscriptionsPage() {
  const router = useRouter();
  const [planCode, setPlanCode] = useState('');
  const [planName, setPlanName] = useState('');
  const [notice, setNotice] = useState('');
  const plans = useQuery({ queryKey: ['platform-plans'], queryFn: async () => (await apiClient.get<Plan[]>('/platform/plans')).data });
  const subscriptions = useQuery({ queryKey: ['platform-subscriptions'], queryFn: async () => (await apiClient.get<TenantSubscription[]>('/platform/subscriptions')).data });
  const features = useQuery({ queryKey: ['platform-features'], queryFn: async () => (await apiClient.get<Feature[]>('/platform/features')).data });

  const createPlan = async (event: React.FormEvent) => {
    event.preventDefault();
    await apiClient.post('/platform/plans', { code: planCode, name: planName, is_public: false, is_custom: true });
    setPlanCode(''); setPlanName(''); setNotice('Custom plan created. Add entitlements before assignment.');
    await plans.refetch();
  };

  const updateTenant = async (item: TenantSubscription, planId: string, status = item.status) => {
    await apiClient.patch(`/platform/tenants/${item.tenant_id}/subscription`, { plan_id: planId, status, reason: 'Platform subscription administration' });
    setNotice(`${item.tenant_name} subscription updated.`);
    await subscriptions.refetch();
  };

  const toggleFeature = async (feature: Feature) => {
    await apiClient.patch(`/platform/features/${feature.id}`, { is_active: !feature.is_active });
    setNotice(`${feature.name} ${feature.is_active ? 'disabled platform-wide' : 'enabled'}.`);
    await features.refetch();
  };

  return <main className="min-h-screen bg-slate-50 p-6"><div className="mx-auto max-w-6xl space-y-6">
    <header className="flex items-center justify-between"><div><p className="text-sm text-slate-500">Platform administration</p><h1 className="text-3xl font-bold">Plans and subscriptions</h1></div><Button variant="outline" onClick={() => router.push('/superadmin')}>Back to tenants</Button></header>
    {notice && <div role="status" className="rounded-md border border-blue-200 bg-blue-50 p-4 text-blue-900">{notice}</div>}
    <Card><CardHeader><CardTitle>Create custom plan</CardTitle><CardDescription>New plans remain private until their feature matrix and prices are reviewed.</CardDescription></CardHeader><CardContent><form onSubmit={createPlan} className="grid gap-3 md:grid-cols-[1fr_2fr_auto]"><input required pattern="[A-Z][A-Z0-9_]+" placeholder="PLAN_CODE" value={planCode} onChange={(event) => setPlanCode(event.target.value.toUpperCase())} className="h-10 rounded-md border px-3" /><input required placeholder="Plan name" value={planName} onChange={(event) => setPlanName(event.target.value)} className="h-10 rounded-md border px-3" /><Button type="submit">Create plan</Button></form></CardContent></Card>
    <Card><CardHeader><CardTitle>Plan catalog</CardTitle><CardDescription>Prices and entitlements are database-configured; plan codes remain stable.</CardDescription></CardHeader><CardContent className="grid gap-3 md:grid-cols-2">{plans.data?.map((plan) => <div key={plan.id} className="rounded-md border bg-white p-4"><div className="flex justify-between"><div><p className="font-semibold">{plan.name}</p><p className="text-xs text-slate-500">{plan.code}</p></div><span>{plan.currency} {Number(plan.base_price).toLocaleString()}</span></div><p className="mt-2 text-sm">{plan.is_active ? 'Active' : 'Inactive'} · {plan.is_public ? 'Public' : 'Private'}</p></div>)}</CardContent></Card>
    <Card><CardHeader><CardTitle>Platform feature registry</CardTitle><CardDescription>Disabling a feature is the highest-precedence security restriction and invalidates all tenant caches.</CardDescription></CardHeader><CardContent className="grid gap-2 md:grid-cols-2">{features.data?.map((feature) => <div key={feature.id} className="flex items-center justify-between rounded-md border p-3"><div><p className="font-medium">{feature.name}</p><p className="text-xs text-slate-500">{feature.code} · {feature.value_type}{feature.is_metered ? ' · metered' : ''}</p></div><Button variant="outline" onClick={() => toggleFeature(feature)}>{feature.is_active ? 'Disable' : 'Enable'}</Button></div>)}</CardContent></Card>
    <Card><CardHeader><CardTitle>Tenant subscriptions</CardTitle><CardDescription>Cross-tenant access is permission-controlled and every tenant row remains protected by forced RLS.</CardDescription></CardHeader><CardContent className="divide-y rounded-md border bg-white">{subscriptions.data?.map((item) => { const currentPlan = plans.data?.find((plan) => plan.code === item.plan_code); return <div key={item.subscription_id} className="grid gap-2 p-4 md:grid-cols-[2fr_1fr_1fr_auto]"><span className="font-medium">{item.tenant_name}<span className="ml-2 text-xs text-slate-500">v{item.entitlement_version}</span></span><select value={currentPlan?.id ?? ''} onChange={(event) => updateTenant(item, event.target.value)} className="h-9 rounded-md border px-2">{plans.data?.map((plan) => <option key={plan.id} value={plan.id}>{plan.name}</option>)}</select><select value={item.status} onChange={(event) => updateTenant(item, currentPlan?.id ?? '', event.target.value)} className="h-9 rounded-md border px-2">{['TRIALING', 'ACTIVE', 'PAST_DUE', 'GRACE_PERIOD', 'SUSPENDED', 'CANCELLED', 'EXPIRED', 'PENDING'].map((status) => <option key={status}>{status}</option>)}</select><span className="text-sm text-slate-500">{item.plan_code}</span></div>; })}{!subscriptions.data?.length && <p className="p-6 text-slate-500">No subscriptions found.</p>}</CardContent></Card>
  </div></main>;
}
