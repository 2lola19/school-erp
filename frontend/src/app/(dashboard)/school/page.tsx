'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { WorkspaceSwitcher } from '@/components/WorkspaceSwitcher';
import { apiClient } from '@/lib/api-client';
import { useAuthStore } from '@/store/authStore';

type DirectoryItem = { id: string; first_name?: string; last_name?: string; name?: string; admission_number?: string };

export default function SchoolDashboard() {
  const router = useRouter();
  const { activeWorkspaceId, initialized, logout, profile } = useAuthStore();
  const [students, setStudents] = useState<DirectoryItem[]>([]);
  const [teachers, setTeachers] = useState<DirectoryItem[]>([]);
  const [classrooms, setClassrooms] = useState<DirectoryItem[]>([]);
  const [error, setError] = useState('');

  const activeWorkspace = useMemo(
    () => profile?.workspaces.find((workspace) => workspace.assignment_id === activeWorkspaceId),
    [activeWorkspaceId, profile],
  );
  const can = (permission: string) => profile?.permissions.includes(permission) ?? false;

  useEffect(() => {
    if (initialized && !profile) router.replace('/login');
  }, [initialized, profile, router]);

  useEffect(() => {
    if (!profile) return;
    const permissions = new Set(profile.permissions);
    async function loadDirectory() {
      try {
        const [studentData, teacherData, classroomData] = await Promise.all([
          permissions.has('students.read') ? apiClient.get('/students/') : Promise.resolve({ data: [] }),
          permissions.has('staff.read') ? apiClient.get('/academic/teachers') : Promise.resolve({ data: [] }),
          permissions.has('classes.read') ? apiClient.get('/academic/classrooms') : Promise.resolve({ data: [] }),
        ]);
        setStudents(studentData.data);
        setTeachers(teacherData.data);
        setClassrooms(classroomData.data);
      } catch {
        setError('Some directory data could not be loaded for this workspace.');
      }
    }
    loadDirectory();
  }, [profile]);

  const handleLogout = async () => {
    try { await apiClient.post('/auth/logout'); } finally {
      logout();
      router.replace('/login');
    }
  };

  if (!initialized || !profile) return <main className="p-8">Loading secure workspace…</main>;

  return (
    <main className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm text-slate-500">{profile.email}</p>
            <h1 className="text-3xl font-bold text-slate-900">School operations</h1>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <WorkspaceSwitcher />
            <Button variant="outline" onClick={handleLogout}>Sign out</Button>
          </div>
        </header>

        {activeWorkspace && (
          <Card>
            <CardHeader>
              <CardTitle>{activeWorkspace.name}</CardTitle>
              <CardDescription>{activeWorkspace.assignment_type === 'PRIMARY' ? 'Primary responsibility' : 'Additional responsibility'} · {activeWorkspace.category}</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-slate-600">Operational scope: {Object.keys(activeWorkspace.scope).length ? JSON.stringify(activeWorkspace.scope) : 'School-wide'}</p>
              <p className="mt-2 text-xs text-slate-500">Workspace switching changes navigation only. Every action remains authorized by the API.</p>
            </CardContent>
          </Card>
        )}

        {error && <p role="alert" className="rounded-md border border-amber-200 bg-amber-50 p-3 text-amber-800">{error}</p>}

        <section className="grid gap-4 md:grid-cols-3">
          {can('students.read') && <Metric title="Students" value={students.length} />}
          {can('staff.read') && <Metric title="Teachers" value={teachers.length} />}
          {can('classes.read') && <Metric title="Classrooms" value={classrooms.length} />}
        </section>

        <Card>
          <CardHeader><CardTitle>Available modules</CardTitle><CardDescription>Modules are derived from effective permissions, including secondary roles and explicit restrictions.</CardDescription></CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {profile.permissions.map((permission) => <span key={permission} className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700">{permission}</span>)}
          </CardContent>
        </Card>
      </div>
    </main>
  );
}

function Metric({ title, value }: { title: string; value: number }) {
  return <Card><CardHeader><CardDescription>{title}</CardDescription><CardTitle className="text-3xl">{value}</CardTitle></CardHeader></Card>;
}
