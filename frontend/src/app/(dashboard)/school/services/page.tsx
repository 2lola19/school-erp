'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FormEvent, useEffect, useMemo, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { WorkspaceSwitcher } from '@/components/WorkspaceSwitcher';
import { apiClient } from '@/lib/api-client';
import { useAuthStore } from '@/store/authStore';

type RecordItem = { id: string; status?: string };
type FieldSpec = {
  name: string;
  label: string;
  placeholder?: string;
  kind?: 'number' | 'list' | 'textarea' | 'text';
};

const MODULES = [
  { title: 'Finance', description: 'Fees, invoices, payments, receipts, and independently approved refunds.', prefix: 'finance.' },
  { title: 'Health', description: 'Isolated clinical records, medical consent, emergency flags, and break-glass review.', prefix: 'health.' },
  { title: 'Counselling', description: 'Assigned confidential cases and protected encounter notes.', prefix: 'counselling.' },
  { title: 'Library', description: 'Catalogue inventory, issue and return workflows, and availability.', prefix: 'library.' },
  { title: 'Transport', description: 'Routes, pickup points, capacity controls, and student assignments.', prefix: 'transport.' },
  { title: 'Hostel', description: 'Boarding facilities, room capacity, and student placement.', prefix: 'hostel.' },
  { title: 'Activities', description: 'Clubs, sports, enrolment, attendance, and verified achievements.', prefix: 'activities.' },
];

export default function SchoolServicesWorkspace() {
  const router = useRouter();
  const { initialized, profile } = useAuthStore();
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const permissions = useMemo(() => new Set(profile?.permissions ?? []), [profile]);
  const can = (permission: string) => permissions.has(permission);

  useEffect(() => {
    if (initialized && !profile) router.replace('/login');
  }, [initialized, profile, router]);

  const invoices = useQuery({
    queryKey: ['service-invoices'],
    queryFn: async () => (await apiClient.get<RecordItem[]>('/school-services/finance/invoices')).data,
    enabled: can('finance.read'),
  });
  const libraryItems = useQuery({
    queryKey: ['service-library-items'],
    queryFn: async () => (await apiClient.get<RecordItem[]>('/school-services/library/items')).data,
    enabled: can('library.read'),
  });
  const routes = useQuery({
    queryKey: ['service-routes'],
    queryFn: async () => (await apiClient.get<RecordItem[]>('/school-services/transport/routes')).data,
    enabled: can('transport.read'),
  });
  const hostels = useQuery({
    queryKey: ['service-hostels'],
    queryFn: async () => (await apiClient.get<RecordItem[]>('/school-services/hostels')).data,
    enabled: can('hostel.read'),
  });
  const activities = useQuery({
    queryKey: ['service-activities'],
    queryFn: async () => (await apiClient.get<RecordItem[]>('/school-services/activities')).data,
    enabled: can('activities.read'),
  });
  const counselling = useQuery({
    queryKey: ['service-counselling-cases'],
    queryFn: async () => (await apiClient.get<RecordItem[]>('/school-services/counselling/cases')).data,
    enabled: can('counselling.cases.read'),
  });

  if (!initialized || !profile) return <main className="p-8">Loading school services…</main>;

  const visibleModules = MODULES.filter((module) =>
    profile.permissions.some((permission) => permission.startsWith(module.prefix)),
  );
  const queryError = [invoices, libraryItems, routes, hostels, activities, counselling]
    .some((query) => query.isError);
  const reportSuccess = (message: string) => { setError(''); setNotice(message); };
  const reportFailure = (message: string) => { setNotice(''); setError(message); };

  return (
    <main className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <Link href="/school" className="text-sm font-medium text-slate-600 hover:text-slate-900">← School operations</Link>
            <h1 className="mt-2 text-3xl font-bold text-slate-900">School services</h1>
            <p className="mt-1 text-sm text-slate-600">Operational modules appear only when the active account has permission.</p>
          </div>
          <WorkspaceSwitcher />
        </header>

        {notice && <p role="status" className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-emerald-800">{notice}</p>}
        {(error || queryError) && <p role="alert" className="rounded-md border border-red-200 bg-red-50 p-3 text-red-800">{error || 'Some service records could not be loaded.'}</p>}

        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-6">
          {can('finance.read') && <Metric title="Invoices" value={invoices.data?.length ?? 0} />}
          {can('library.read') && <Metric title="Library items" value={libraryItems.data?.length ?? 0} />}
          {can('transport.read') && <Metric title="Routes" value={routes.data?.length ?? 0} />}
          {can('hostel.read') && <Metric title="Hostels" value={hostels.data?.length ?? 0} />}
          {can('activities.read') && <Metric title="Activities" value={activities.data?.length ?? 0} />}
          {can('counselling.cases.read') && <Metric title="Assigned cases" value={counselling.data?.length ?? 0} />}
        </section>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {visibleModules.map((module) => (
            <Card key={module.title}>
              <CardHeader><CardTitle>{module.title}</CardTitle><CardDescription>{module.description}</CardDescription></CardHeader>
            </Card>
          ))}
        </section>

        <section className="grid gap-6 lg:grid-cols-2 xl:grid-cols-3">
          {can('finance.fees.manage') && (
            <QuickCreate
              title="Create fee schedule"
              description="Create a reusable fee amount before issuing student invoices."
              url="/school-services/finance/fee-schedules"
              queryKey="service-invoices"
              fields={[{ name: 'name', label: 'Fee name' }, { name: 'amount', label: 'Amount', placeholder: '125000.00' }]}
              onSuccess={() => reportSuccess('Fee schedule created.')}
              onError={() => reportFailure('The fee schedule could not be created.')}
            />
          )}
          {can('health.records.write') && (
            <QuickCreate
              title="Add emergency health flag"
              description="Expose safety instructions without disclosing the full clinical record."
              url="/school-services/health/emergency-flags"
              fields={[
                { name: 'student_id', label: 'Student ID' },
                { name: 'label', label: 'Safety flag', placeholder: 'Severe asthma' },
                { name: 'instructions', label: 'Emergency instructions', kind: 'textarea' },
              ]}
              onSuccess={() => reportSuccess('Emergency health flag added.')}
              onError={() => reportFailure('The emergency flag could not be added.')}
            />
          )}
          {can('library.manage') && (
            <QuickCreate
              title="Catalogue library item"
              description="Add inventory with an immediately available copy count."
              url="/school-services/library/items"
              queryKey="service-library-items"
              fields={[
                { name: 'catalogue_code', label: 'Catalogue code' },
                { name: 'title', label: 'Title' },
                { name: 'author', label: 'Author' },
                { name: 'total_copies', label: 'Copies', kind: 'number' },
              ]}
              onSuccess={() => reportSuccess('Library item catalogued.')}
              onError={() => reportFailure('The library item could not be saved.')}
            />
          )}
          {can('transport.manage') && (
            <QuickCreate
              title="Create transport route"
              description="Capacity is enforced when students are assigned."
              url="/school-services/transport/routes"
              queryKey="service-routes"
              fields={[
                { name: 'name', label: 'Route name' },
                { name: 'pickup_points', label: 'Pickup points', placeholder: 'Gate A, Market Road', kind: 'list' },
                { name: 'capacity', label: 'Capacity', kind: 'number' },
              ]}
              onSuccess={() => reportSuccess('Transport route created.')}
              onError={() => reportFailure('The route could not be created.')}
            />
          )}
          {can('hostel.manage') && (
            <QuickCreate
              title="Create hostel"
              description="Room placement applies a second capacity check."
              url="/school-services/hostels"
              queryKey="service-hostels"
              fields={[
                { name: 'name', label: 'Hostel name' },
                { name: 'gender_policy', label: 'Gender policy', placeholder: 'Girls' },
                { name: 'capacity', label: 'Capacity', kind: 'number' },
              ]}
              onSuccess={() => reportSuccess('Hostel created.')}
              onError={() => reportFailure('The hostel could not be created.')}
            />
          )}
          {can('activities.manage') && (
            <QuickCreate
              title="Create activity"
              description="Patrons receive a scoped role before recording participation."
              url="/school-services/activities"
              queryKey="service-activities"
              fields={[{ name: 'name', label: 'Activity name' }, { name: 'category', label: 'Category', placeholder: 'Club' }]}
              onSuccess={() => reportSuccess('Activity created.')}
              onError={() => reportFailure('The activity could not be created.')}
            />
          )}
        </section>

        {visibleModules.length === 0 && (
          <Card><CardHeader><CardTitle>No service workspace assigned</CardTitle><CardDescription>Ask an authorised school administrator to assign a relevant role.</CardDescription></CardHeader></Card>
        )}
      </div>
    </main>
  );
}

function Metric({ title, value }: { title: string; value: number }) {
  return <Card><CardHeader><CardDescription>{title}</CardDescription><CardTitle className="text-3xl">{value}</CardTitle></CardHeader></Card>;
}

function QuickCreate({ title, description, url, queryKey, fields, onSuccess, onError }: {
  title: string;
  description: string;
  url: string;
  queryKey?: string;
  fields: FieldSpec[];
  onSuccess: () => void;
  onError: () => void;
}) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => apiClient.post(url, payload),
    onSuccess: async () => {
      if (queryKey) await queryClient.invalidateQueries({ queryKey: [queryKey] });
      onSuccess();
    },
    onError,
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    const payload = Object.fromEntries(fields.map((field) => {
      const value = String(values.get(field.name) ?? '').trim();
      if (field.kind === 'number') return [field.name, Number(value)];
      if (field.kind === 'list') return [field.name, value.split(',').map((item) => item.trim()).filter(Boolean)];
      return [field.name, value];
    }));
    mutation.mutate(payload, { onSuccess: () => form.reset() });
  }

  return (
    <Card>
      <CardHeader><CardTitle>{title}</CardTitle><CardDescription>{description}</CardDescription></CardHeader>
      <CardContent>
        <form onSubmit={submit} className="space-y-3">
          {fields.map((field) => (
            <div key={field.name} className="space-y-1.5">
              <Label htmlFor={field.name}>{field.label}</Label>
              {field.kind === 'textarea' ? (
                <textarea id={field.name} name={field.name} required placeholder={field.placeholder} className="min-h-24 w-full rounded-md border bg-white px-3 py-2 text-sm" />
              ) : (
                <Input id={field.name} name={field.name} required placeholder={field.placeholder} type={field.kind === 'number' ? 'number' : 'text'} min={field.kind === 'number' ? 1 : undefined} />
              )}
            </div>
          ))}
          <Button type="submit" disabled={mutation.isPending}>{mutation.isPending ? 'Saving…' : 'Save'}</Button>
        </form>
      </CardContent>
    </Card>
  );
}
