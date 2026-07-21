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

type AcademicSession = {
  id: string;
  name: string;
  starts_on: string;
  ends_on: string;
  status: 'PLANNED' | 'ACTIVE' | 'CLOSED';
};

type Applicant = {
  id: string;
  application_number: string;
  first_name: string;
  last_name: string;
  status: 'DRAFT' | 'SUBMITTED' | 'ADMITTED' | 'REJECTED';
};

type AttendanceRecord = {
  id: string;
  date: string;
  status: string;
  workflow_status: 'DRAFT' | 'SUBMITTED' | 'APPROVED';
};

type ExamCycle = { id: string; name: string; status: string };

function today() {
  return new Date().toISOString().slice(0, 10);
}

export default function AcademicWorkspace() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { initialized, profile } = useAuthStore();
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const permissions = useMemo(() => new Set(profile?.permissions ?? []), [profile]);
  const can = (permission: string) => permissions.has(permission);

  useEffect(() => {
    if (initialized && !profile) router.replace('/login');
  }, [initialized, profile, router]);

  const sessions = useQuery({
    queryKey: ['academic-sessions'],
    queryFn: async () => (await apiClient.get<AcademicSession[]>('/academic-admin/sessions')).data,
    enabled: can('academic.setup.read'),
  });
  const applicants = useQuery({
    queryKey: ['academic-applicants'],
    queryFn: async () => (await apiClient.get<Applicant[]>('/academic-admin/applicants')).data,
    enabled: can('admissions.read'),
  });
  const attendance = useQuery({
    queryKey: ['academic-attendance'],
    queryFn: async () => (await apiClient.get<AttendanceRecord[]>('/academic-admin/attendance')).data,
    enabled: can('attendance.read'),
  });
  const examCycles = useQuery({
    queryKey: ['academic-exam-cycles'],
    queryFn: async () => (await apiClient.get<ExamCycle[]>('/academic-admin/exam-cycles')).data,
    enabled: can('examinations.read'),
  });

  const reportFailure = (message: string) => {
    setNotice('');
    setError(message);
  };
  const reportSuccess = (message: string) => {
    setError('');
    setNotice(message);
  };

  const createSession = useMutation({
    mutationFn: (payload: { name: string; starts_on: string; ends_on: string }) =>
      apiClient.post('/academic-admin/sessions', payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['academic-sessions'] });
      reportSuccess('Academic session created as planned.');
    },
    onError: () => reportFailure('The academic session could not be created.'),
  });

  const createApplicant = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      apiClient.post('/academic-admin/applicants', payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['academic-applicants'] });
      reportSuccess('Application submitted for review.');
    },
    onError: () => reportFailure('The application could not be submitted.'),
  });

  const markAttendance = useMutation({
    mutationFn: (payload: Record<string, string>) =>
      apiClient.post('/academic-admin/attendance', payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['academic-attendance'] });
      reportSuccess('Attendance saved as a draft.');
    },
    onError: () => reportFailure('Attendance could not be saved. Check the student and classroom scope.'),
  });

  if (!initialized || !profile) {
    return <main className="p-8">Loading academic workspace…</main>;
  }

  const loading = sessions.isLoading || applicants.isLoading || attendance.isLoading || examCycles.isLoading;
  const queryError = sessions.isError || applicants.isError || attendance.isError || examCycles.isError;

  return (
    <main className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <Link href="/school" className="text-sm font-medium text-slate-600 hover:text-slate-900">← School operations</Link>
            <h1 className="mt-2 text-3xl font-bold text-slate-900">Academic administration</h1>
            <p className="mt-1 text-sm text-slate-600">Official academic workflows remain tenant-scoped and audited.</p>
          </div>
          <WorkspaceSwitcher />
        </header>

        {notice && <p role="status" className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-emerald-800">{notice}</p>}
        {(error || queryError) && <p role="alert" className="rounded-md border border-red-200 bg-red-50 p-3 text-red-800">{error || 'Some academic records could not be loaded.'}</p>}
        {loading && <p className="text-sm text-slate-500">Refreshing academic records…</p>}

        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Metric title="Academic sessions" value={sessions.data?.length ?? 0} />
          <Metric title="Open applications" value={applicants.data?.filter((item) => item.status === 'SUBMITTED').length ?? 0} />
          <Metric title="Attendance awaiting approval" value={attendance.data?.filter((item) => item.workflow_status === 'SUBMITTED').length ?? 0} />
          <Metric title="Examination cycles" value={examCycles.data?.length ?? 0} />
        </section>

        <section className="grid gap-6 lg:grid-cols-3">
          {can('academic.setup.manage') && <SessionForm pending={createSession.isPending} onSubmit={(payload) => createSession.mutate(payload)} />}
          {can('admissions.create') && <ApplicantForm pending={createApplicant.isPending} onSubmit={(payload) => createApplicant.mutate(payload)} />}
          {can('attendance.mark') && <AttendanceForm pending={markAttendance.isPending} onSubmit={(payload) => markAttendance.mutate(payload)} />}
        </section>

        <section className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Application queue</CardTitle>
              <CardDescription>Admission decisions require the dedicated approval permission.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {(applicants.data ?? []).slice(0, 8).map((applicant) => (
                <div key={applicant.id} className="flex items-center justify-between rounded-md border p-3">
                  <div><p className="font-medium">{applicant.first_name} {applicant.last_name}</p><p className="text-xs text-slate-500">{applicant.application_number}</p></div>
                  <Status value={applicant.status} />
                </div>
              ))}
              {!applicants.data?.length && <p className="text-sm text-slate-500">No applications available.</p>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Controlled workflows</CardTitle>
              <CardDescription>These operations are available through the API when your role grants them.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2">
              {['Timetables', 'Examination cycles', 'Assessment components', 'Report cards'].map((module) => (
                <div key={module} className="rounded-md border bg-white p-4"><p className="font-medium">{module}</p><p className="mt-1 text-xs text-slate-500">Scoped permissions and audit history enabled</p></div>
              ))}
            </CardContent>
          </Card>
        </section>
      </div>
    </main>
  );
}

function Metric({ title, value }: { title: string; value: number }) {
  return <Card><CardHeader><CardDescription>{title}</CardDescription><CardTitle className="text-3xl">{value}</CardTitle></CardHeader></Card>;
}

function Status({ value }: { value: string }) {
  return <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">{value.replaceAll('_', ' ')}</span>;
}

function SessionForm({ pending, onSubmit }: { pending: boolean; onSubmit: (payload: { name: string; starts_on: string; ends_on: string }) => void }) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    onSubmit({ name: String(values.get('name')), starts_on: String(values.get('starts_on')), ends_on: String(values.get('ends_on')) });
    event.currentTarget.reset();
  }
  return (
    <Card><CardHeader><CardTitle>New academic session</CardTitle><CardDescription>Create the school year before adding terms.</CardDescription></CardHeader><CardContent><form onSubmit={submit} className="space-y-3"><Field label="Session name" name="name" placeholder="2026/2027" /><Field label="Starts" name="starts_on" type="date" /><Field label="Ends" name="ends_on" type="date" /><Button disabled={pending} type="submit">{pending ? 'Creating…' : 'Create session'}</Button></form></CardContent></Card>
  );
}

function ApplicantForm({ pending, onSubmit }: { pending: boolean; onSubmit: (payload: Record<string, unknown>) => void }) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    onSubmit({
      application_number: String(values.get('application_number')),
      first_name: String(values.get('first_name')),
      last_name: String(values.get('last_name')),
      guardian: {
        first_name: String(values.get('guardian_first_name')),
        last_name: String(values.get('guardian_last_name')),
        email: String(values.get('guardian_email')),
        relationship: String(values.get('relationship')),
      },
    });
    event.currentTarget.reset();
  }
  return (
    <Card><CardHeader><CardTitle>Register applicant</CardTitle><CardDescription>Capture the applicant and primary guardian together.</CardDescription></CardHeader><CardContent><form onSubmit={submit} className="space-y-3"><Field label="Application number" name="application_number" /><div className="grid grid-cols-2 gap-2"><Field label="First name" name="first_name" /><Field label="Last name" name="last_name" /></div><div className="grid grid-cols-2 gap-2"><Field label="Guardian first name" name="guardian_first_name" /><Field label="Guardian last name" name="guardian_last_name" /></div><Field label="Guardian email" name="guardian_email" type="email" /><Field label="Relationship" name="relationship" placeholder="Parent" /><Button disabled={pending} type="submit">{pending ? 'Submitting…' : 'Submit application'}</Button></form></CardContent></Card>
  );
}

function AttendanceForm({ pending, onSubmit }: { pending: boolean; onSubmit: (payload: Record<string, string>) => void }) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    onSubmit({ student_id: String(values.get('student_id')), classroom_id: String(values.get('classroom_id')), date: String(values.get('date')), status: String(values.get('status')) });
  }
  return (
    <Card><CardHeader><CardTitle>Mark attendance</CardTitle><CardDescription>Your active role scope must cover the classroom.</CardDescription></CardHeader><CardContent><form onSubmit={submit} className="space-y-3"><Field label="Student ID" name="student_id" /><Field label="Classroom ID" name="classroom_id" /><Field label="Date" name="date" type="date" defaultValue={today()} /><div className="space-y-1.5"><Label htmlFor="attendance-status">Status</Label><select id="attendance-status" name="status" className="h-9 w-full rounded-md border bg-white px-3 text-sm"><option value="PRESENT">Present</option><option value="ABSENT">Absent</option><option value="LATE">Late</option><option value="EXCUSED">Excused</option></select></div><Button disabled={pending} type="submit">{pending ? 'Saving…' : 'Save attendance'}</Button></form></CardContent></Card>
  );
}

function Field({ label, name, type = 'text', placeholder, defaultValue }: { label: string; name: string; type?: string; placeholder?: string; defaultValue?: string }) {
  return <div className="space-y-1.5"><Label htmlFor={name}>{label}</Label><Input id={name} name={name} type={type} placeholder={placeholder} defaultValue={defaultValue} required /></div>;
}
