'use client';

import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { useEntitlements } from '@/components/entitlements/EntitlementProvider';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { apiClient } from '@/lib/api-client';

interface Subscription { plan_name: string; plan_code: string; status: string; current_period_end: string | null; cancel_at_period_end: boolean }
interface Plan { id: string; code: string; name: string; description: string | null; currency: string; base_price: string; display_order: number }
interface AddOn { id: string; name: string; description: string | null }
interface BillingItem { id: string; transaction_type: string; amount: string; currency: string; status: string; created_at: string }
interface DowngradePreview { target_plan_id: string; effective_at: string; features_lost: string[]; quotas_decreased: Array<{ feature_code: string; new_limit: number; current_usage: number; over_limit: boolean }>; over_limit: boolean }

export default function BillingPage() {
  const router = useRouter();
  const { entitlements, usage, subscriptionStatus } = useEntitlements();
  const [notice, setNotice] = useState('');
  const [preview, setPreview] = useState<DowngradePreview | null>(null);
  const subscription = useQuery({ queryKey: ['subscription'], queryFn: async () => (await apiClient.get<Subscription>('/tenant/subscription')).data });
  const plans = useQuery({ queryKey: ['plans'], queryFn: async () => (await apiClient.get<Plan[]>('/subscription-plans')).data });
  const addOns = useQuery({ queryKey: ['add-ons'], queryFn: async () => (await apiClient.get<AddOn[]>('/add-ons')).data });
  const billing = useQuery({ queryKey: ['billing-history'], queryFn: async () => (await apiClient.get<BillingItem[]>('/tenant/subscription/billing')).data });

  const requestPlan = async (plan: Plan) => {
    setNotice('');
    const current = plans.data?.find((item) => item.code === subscription.data?.plan_code);
    try {
      if (!current || plan.display_order > current.display_order) {
        const response = await apiClient.post<{ message: string }>('/tenant/subscription/upgrade', { plan_id: plan.id, reason: `Upgrade requested to ${plan.name}` });
        setNotice(response.data.message);
        await billing.refetch();
      } else {
        const response = await apiClient.post<DowngradePreview>('/tenant/subscription/downgrade', { plan_id: plan.id, reason: `Downgrade requested to ${plan.name}`, confirm: false });
        setPreview(response.data);
      }
    } catch { setNotice('The plan request could not be completed.'); }
  };

  const confirmDowngrade = async () => {
    if (!preview) return;
    await apiClient.post('/tenant/subscription/downgrade', { plan_id: preview.target_plan_id, reason: 'Downgrade confirmed after impact review', confirm: true });
    setNotice('Downgrade scheduled. No data will be deleted.');
    setPreview(null);
    await subscription.refetch();
  };

  const requestAddOn = async (addOn: AddOn) => {
    await apiClient.post('/tenant/subscription/add-ons', { add_on_id: addOn.id, quantity: 1 });
    setNotice(`${addOn.name} requested; access awaits verified payment or platform approval.`);
  };

  const changeCancellation = async () => {
    if (subscription.data?.cancel_at_period_end) {
      await apiClient.post('/tenant/subscription/reactivate');
      setNotice('Subscription reactivated.');
    } else {
      await apiClient.post('/tenant/subscription/cancel', { reason: 'Cancellation requested in school billing portal', at_period_end: true });
      setNotice('Cancellation scheduled for the end of the paid period.');
    }
    await subscription.refetch();
  };

  return <main className="min-h-screen bg-slate-50 p-6"><div className="mx-auto max-w-6xl space-y-6">
    <header className="flex items-center justify-between"><div><p className="text-sm text-slate-500">School administration</p><h1 className="text-3xl font-bold">Subscription and billing</h1></div><Button variant="outline" onClick={() => router.push('/school')}>Back to school</Button></header>
    {['PAST_DUE', 'GRACE_PERIOD', 'SUSPENDED', 'EXPIRED'].includes(subscriptionStatus) && <div className="rounded-md border border-amber-300 bg-amber-50 p-4 text-amber-900">Your subscription is {subscriptionStatus.toLowerCase().replace('_', ' ')}. Existing data is preserved, but operational writes may be restricted.</div>}
    {notice && <div role="status" className="rounded-md border border-blue-200 bg-blue-50 p-4 text-blue-900">{notice}</div>}
    {preview && <Card><CardHeader><CardTitle>Review downgrade impact</CardTitle><CardDescription>Effective {new Date(preview.effective_at).toLocaleDateString()}. Existing records remain preserved.</CardDescription></CardHeader><CardContent className="space-y-3"><p>{preview.features_lost.length} capabilities become read-only: {preview.features_lost.join(', ') || 'none'}.</p>{preview.quotas_decreased.map((quota) => <p key={quota.feature_code} className={quota.over_limit ? 'text-red-700' : ''}>{quota.feature_code}: {quota.current_usage} used against the new {quota.new_limit} limit.</p>)}<div className="flex gap-2"><Button onClick={confirmDowngrade}>Confirm scheduled downgrade</Button><Button variant="outline" onClick={() => setPreview(null)}>Keep current plan</Button></div></CardContent></Card>}
    <section className="grid gap-4 md:grid-cols-3">
      <Card><CardHeader><CardDescription>Current plan</CardDescription><CardTitle>{subscription.data?.plan_name ?? entitlements?.plan_code ?? 'Loading...'}</CardTitle></CardHeader><CardContent><p className="text-sm">Status: {subscription.data?.status ?? subscriptionStatus}</p>{subscription.data?.current_period_end && <p className="text-sm text-slate-500">Period ends {new Date(subscription.data.current_period_end).toLocaleDateString()}</p>}<Button className="mt-3" variant="outline" onClick={changeCancellation}>{subscription.data?.cancel_at_period_end ? 'Reactivate subscription' : 'Cancel at period end'}</Button></CardContent></Card>
      <Card><CardHeader><CardDescription>Enabled capabilities</CardDescription><CardTitle>{Object.values(entitlements?.values ?? {}).filter((value) => value === true).length}</CardTitle></CardHeader><CardContent className="text-sm text-slate-500">RBAC permissions are checked separately for every action.</CardContent></Card>
      <Card><CardHeader><CardDescription>Quota warnings</CardDescription><CardTitle>{usage.filter((item) => item.percent_used >= 80).length}</CardTitle></CardHeader><CardContent className="text-sm text-slate-500">Warnings begin at 80% usage.</CardContent></Card>
    </section>
    <Card><CardHeader><CardTitle>Usage</CardTitle><CardDescription>Authoritative active-record counts and current-period metered usage.</CardDescription></CardHeader><CardContent className="space-y-4">{usage.map((item) => <div key={item.feature_code}><div className="mb-1 flex justify-between text-sm"><span>{item.feature_code.replace('quota.', '').replaceAll('_', ' ')}</span><span>{item.current_usage.toLocaleString()} / {item.limit.toLocaleString()}</span></div><div className="h-2 rounded bg-slate-200"><div className={`h-2 rounded ${item.percent_used >= 100 ? 'bg-red-600' : item.percent_used >= 80 ? 'bg-amber-500' : 'bg-emerald-600'}`} style={{ width: `${Math.min(item.percent_used, 100)}%` }} /></div></div>)}{!usage.length && <p className="text-slate-500">No quota information is available.</p>}</CardContent></Card>
    <Card><CardHeader><CardTitle>Available plans</CardTitle><CardDescription>Requests do not unlock features until platform approval or verified payment.</CardDescription></CardHeader><CardContent className="grid gap-3 md:grid-cols-2">{plans.data?.map((plan) => <div key={plan.id} className="rounded-md border p-4"><div className="flex justify-between"><h3 className="font-semibold">{plan.name}</h3><span>{plan.currency} {Number(plan.base_price).toLocaleString()}</span></div><p className="mt-1 text-sm text-slate-500">{plan.description}</p><Button className="mt-3" variant="outline" onClick={() => requestPlan(plan)} disabled={plan.code === subscription.data?.plan_code}>Request this plan</Button></div>)}</CardContent></Card>
    <Card><CardHeader><CardTitle>Optional add-ons</CardTitle></CardHeader><CardContent className="grid gap-3 md:grid-cols-2">{addOns.data?.map((addOn) => <div key={addOn.id} className="flex items-center justify-between rounded-md border p-4"><div><p className="font-medium">{addOn.name}</p><p className="text-sm text-slate-500">{addOn.description}</p></div><Button variant="outline" onClick={() => requestAddOn(addOn)}>Request</Button></div>)}</CardContent></Card>
    <Card><CardHeader><CardTitle>Billing history</CardTitle></CardHeader><CardContent className="divide-y">{billing.data?.map((item) => <div key={item.id} className="flex flex-wrap justify-between gap-2 py-3 text-sm"><span>{item.transaction_type}</span><span>{item.currency} {Number(item.amount).toLocaleString()}</span><span className="font-medium">{item.status}</span><span className="text-slate-500">{new Date(item.created_at).toLocaleDateString()}</span></div>)}{!billing.data?.length && <p className="text-slate-500">No platform billing transactions yet.</p>}</CardContent></Card>
  </div></main>;
}
