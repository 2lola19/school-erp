import os

frontend_code = """'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { ServiceWorkerRegistry } from '@/components/ServiceWorkerRegistry';

export default function SchoolDashboard() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState('students');

  // State
  const [students, setStudents] = useState<any[]>([]);
  const [teachers, setTeachers] = useState<any[]>([]);
  const [classrooms, setClassrooms] = useState<any[]>([]);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Forms
  const [sFirst, setSFirst] = useState(''); const [sLast, setSLast] = useState(''); const [sAdm, setSAdm] = useState('');
  const [tFirst, setTFirst] = useState(''); const [tLast, setTLast] = useState(''); const [tEmail, setTEmail] = useState(''); const [tEmp, setTEmp] = useState('');
  const [cName, setCName] = useState(''); const [cTeacher, setCTeacher] = useState('');

  const fetchAllData = async () => {
    try {
      const [stRes, tcRes, clRes] = await Promise.all([
        apiClient.get('/students/').catch(() => ({ data: [] })),
        apiClient.get('/academic/teachers/').catch(() => ({ data: [] })),
        apiClient.get('/academic/classrooms/').catch(() => ({ data: [] }))
      ]);
      setStudents(stRes.data);
      setTeachers(tcRes.data);
      setClassrooms(clRes.data);
    } catch (err) {
      console.error("Fetch error:", err);
    }
  };

  useEffect(() => { fetchAllData(); }, []);

  const handleLogout = () => {
    localStorage.removeItem('token'); localStorage.removeItem('access_token');
    document.cookie = 'token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    router.push('/login');
  };

  const executeMutation = async (endpoint: string, payload: any, resetters: Function[]) => {
    setIsLoading(true); setError('');
    try {
      await apiClient.post(endpoint, payload);
      resetters.forEach(fn => fn(''));
      await fetchAllData();
    } catch (err: any) {
      setError(err.response?.data?.detail || JSON.stringify(err.response?.data) || 'Mutation failed.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-8 min-h-screen bg-slate-50 space-y-6">
      <ServiceWorkerRegistry />
      <div className="flex justify-between items-center max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Local Operations Plane</h1>
        <Button onClick={handleLogout} variant="destructive">Disconnect</Button>
      </div>

      <div className="max-w-6xl mx-auto flex gap-4 border-b pb-4">
        <Button variant={activeTab === 'students' ? 'default' : 'outline'} onClick={() => setActiveTab('students')}>Students</Button>
        <Button variant={activeTab === 'teachers' ? 'default' : 'outline'} onClick={() => setActiveTab('teachers')}>Teachers</Button>
        <Button variant={activeTab === 'classrooms' ? 'default' : 'outline'} onClick={() => setActiveTab('classrooms')}>Classrooms</Button>
      </div>
      
      {error && <div className="max-w-6xl mx-auto text-sm font-medium text-red-600 bg-red-50 border border-red-200 p-3 rounded-md break-words">{error}</div>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-6xl mx-auto">
        
        {/* DYNAMIC LEFT COLUMN: CREATION FORMS */}
        <Card className="md:col-span-1 h-fit shadow-md">
          <CardHeader>
            <CardTitle>Register {activeTab === 'students' ? 'Student' : activeTab === 'teachers' ? 'Teacher' : 'Classroom'}</CardTitle>
          </CardHeader>
          <CardContent>
            {activeTab === 'students' && (
              <form onSubmit={(e) => { e.preventDefault(); executeMutation('/students/', { first_name: sFirst, last_name: sLast, admission_number: sAdm }, [setSFirst, setSLast, setSAdm]); }} className="space-y-4">
                <input required placeholder="First Name" value={sFirst} onChange={e => setSFirst(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm" />
                <input required placeholder="Last Name" value={sLast} onChange={e => setSLast(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm" />
                <input required placeholder="Admission No" value={sAdm} onChange={e => setSAdm(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm" />
                <Button className="w-full" type="submit" disabled={isLoading}>{isLoading ? 'Processing...' : 'Admit Student'}</Button>
              </form>
            )}

            {activeTab === 'teachers' && (
              <form onSubmit={(e) => { e.preventDefault(); executeMutation('/academic/teachers/', { first_name: tFirst, last_name: tLast, email: tEmail, employee_id: tEmp }, [setTFirst, setTLast, setTEmail, setTEmp]); }} className="space-y-4">
                <input required placeholder="First Name" value={tFirst} onChange={e => setTFirst(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm" />
                <input required placeholder="Last Name" value={tLast} onChange={e => setTLast(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm" />
                <input required type="email" placeholder="Email" value={tEmail} onChange={e => setTEmail(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm" />
                <input required placeholder="Employee ID" value={tEmp} onChange={e => setTEmp(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm" />
                <Button className="w-full" type="submit" disabled={isLoading}>{isLoading ? 'Processing...' : 'Onboard Teacher'}</Button>
              </form>
            )}

            {activeTab === 'classrooms' && (
              <form onSubmit={(e) => { e.preventDefault(); executeMutation('/academic/classrooms/', { name: cName, teacher_id: cTeacher || null }, [setCName, setCTeacher]); }} className="space-y-4">
                <input required placeholder="Classroom Name (e.g., JSS 1A)" value={cName} onChange={e => setCName(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm" />
                <select value={cTeacher} onChange={e => setCTeacher(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm bg-white">
                  <option value="">Assign a Form Teacher (Optional)...</option>
                  {teachers.map(t => <option key={t.id} value={t.id}>{t.first_name} {t.last_name}</option>)}
                </select>
                <Button className="w-full" type="submit" disabled={isLoading}>{isLoading ? 'Processing...' : 'Create Classroom'}</Button>
              </form>
            )}
          </CardContent>
        </Card>

        {/* DYNAMIC RIGHT COLUMN: DIRECTORIES */}
        <Card className="md:col-span-2 shadow-md">
          <CardHeader>
            <CardTitle>System Directory</CardTitle>
            <CardDescription>Viewing {activeTab} for this institution.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="border rounded-md divide-y overflow-hidden shadow-sm bg-white">
              {activeTab === 'students' && students.map(s => (
                <div key={s.id} className="p-4"><p className="font-bold text-slate-900">{s.first_name} {s.last_name}</p><p className="text-sm text-slate-500">Admitted: {s.admission_number}</p></div>
              ))}
              {activeTab === 'teachers' && teachers.map(t => (
                <div key={t.id} className="p-4"><p className="font-bold text-slate-900">{t.first_name} {t.last_name}</p><p className="text-sm text-slate-500">ID: {t.employee_id} | {t.email}</p></div>
              ))}
              {activeTab === 'classrooms' && classrooms.map(c => {
                const assigned = teachers.find(t => t.id === c.teacher_id);
                return (
                  <div key={c.id} className="p-4"><p className="font-bold text-slate-900">{c.name}</p><p className="text-sm text-slate-500">Form Teacher: {assigned ? `${assigned.first_name} ${assigned.last_name}` : 'Unassigned'}</p></div>
                )
              })}
              {((activeTab === 'students' && !students.length) || (activeTab === 'teachers' && !teachers.length) || (activeTab === 'classrooms' && !classrooms.length)) && (
                <div className="p-8 text-center text-slate-500">No records found.</div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
"""

with open("src/app/(dashboard)/school/page.tsx", "w", encoding="utf-8") as f:
    f.write(frontend_code)

print("[+] Dashboard syntax repaired and Service Worker successfully bound.")