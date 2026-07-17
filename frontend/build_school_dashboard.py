import os

frontend_code = """'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

export default function SchoolDashboard() {
  const { logout } = useAuthStore();
  const router = useRouter();

  const [students, setStudents] = useState<any[]>([]);
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [admissionNum, setAdmissionNum] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const fetchStudents = async () => {
    try {
      const res = await apiClient.get('/students/');
      setStudents(res.data);
    } catch (err: any) {
      console.error("Failed to fetch students:", err);
    }
  };

  useEffect(() => {
    fetchStudents();
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('access_token');
    document.cookie = 'token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    try { logout(); } catch (e) {}
    router.push('/login');
  };

  const handleAddStudent = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      await apiClient.post('/students/', {
        first_name: firstName,
        last_name: lastName,
        admission_number: admissionNum
      });
      
      setFirstName('');
      setLastName('');
      setAdmissionNum('');
      fetchStudents();
      
    } catch (err: any) {
      if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        if (typeof detail === 'string') setError(detail);
        else setError(JSON.stringify(detail));
      } else {
        setError('Failed to register student.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-8 min-h-screen bg-slate-50 space-y-6">
      <div className="flex justify-between items-center max-w-5xl mx-auto">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Local School Dashboard</h1>
        <Button onClick={handleLogout} variant="destructive">Disconnect</Button>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
        
        {/* Registration Form */}
        <Card className="md:col-span-1 h-fit shadow-md">
          <CardHeader>
            <CardTitle>Register Student</CardTitle>
            <CardDescription>Admit a new student to your institution.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleAddStudent} className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">First Name</label>
                <input required value={firstName} onChange={(e) => setFirstName(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">Last Name</label>
                <input required value={lastName} onChange={(e) => setLastName(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">Admission Number</label>
                <input required value={admissionNum} onChange={(e) => setAdmissionNum(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500" />
              </div>
              
              {error && <div className="text-sm font-medium text-red-600 bg-red-50 border border-red-200 p-3 rounded-md break-words">{error}</div>}
              
              <Button className="w-full font-semibold" type="submit" disabled={isLoading}>
                {isLoading ? 'Registering...' : 'Admit Student'}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Student Directory */}
        <Card className="md:col-span-2 shadow-md">
          <CardHeader>
            <CardTitle>Student Directory</CardTitle>
            <CardDescription>All students currently enrolled in this institution.</CardDescription>
          </CardHeader>
          <CardContent>
            {students.length === 0 ? (
              <div className="text-center p-8 border-2 border-dashed rounded-md bg-slate-50">
                <p className="text-slate-500 font-medium">No students registered yet.</p>
              </div>
            ) : (
              <div className="border rounded-md divide-y overflow-hidden shadow-sm">
                {students.map((student) => (
                  <div key={student.id} className="p-4 flex justify-between items-center bg-white hover:bg-slate-50 transition-colors">
                    <div>
                      <p className="font-bold text-slate-900">{student.first_name} {student.last_name}</p>
                      <p className="text-sm text-slate-500 font-medium tracking-tight">Admission No: <span className="text-slate-900">{student.admission_number}</span></p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
"""

with open("src/app/(dashboard)/school/page.tsx", "w", encoding="utf-8") as f:
    f.write(frontend_code)

print("[+] Local School dashboard rebuilt with Student Registration UI.")