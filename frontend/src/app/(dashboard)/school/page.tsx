'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { ServiceWorkerRegistry } from '@/components/ServiceWorkerRegistry';
import { safeMutate } from '@/lib/sync/syncEngine';

export default function SchoolDashboard() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState('students');

  // Core State
  const [students, setStudents] = useState<any[]>([]);
  const [teachers, setTeachers] = useState<any[]>([]);
  const [classrooms, setClassrooms] = useState<any[]>([]);
  const [subjects, setSubjects] = useState<any[]>([]);
  
  // UI State
  const [error, setError] = useState('');
  const [syncStatus, setSyncStatus] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Form State: Core
  const [sFirst, setSFirst] = useState(''); const [sLast, setSLast] = useState(''); const [sAdm, setSAdm] = useState('');
  const [tFirst, setTFirst] = useState(''); const [tLast, setTLast] = useState(''); const [tEmail, setTEmail] = useState(''); const [tEmp, setTEmp] = useState('');
  const [cName, setCName] = useState(''); const [cTeacher, setCTeacher] = useState('');
  
  // Form State: Academic
  const [subName, setSubName] = useState(''); const [subCode, setSubCode] = useState('');
  const [gStudent, setGStudent] = useState(''); const [gSubject, setGSubject] = useState(''); 
  const [gTerm, setGTerm] = useState('First Term'); const [gYear, setGYear] = useState('2025/2026'); const [gScore, setGScore] = useState('');

  // Form State: Attendance & Enrollment
  const [aStudent, setAStudent] = useState('');
  const [aClassroom, setAClassroom] = useState('');
  const [aDate, setADate] = useState(new Date().toISOString().split('T')[0]);
  const [aStatus, setAStatus] = useState('Present');
  const [eStudent, setEStudent] = useState('');
  const [eClassroom, setEClassroom] = useState('');
  const [eYear, setEYear] = useState('2025/2026');

  // Transcript State
  const [tSelectedStudent, setTSelectedStudent] = useState('');
  const [transcriptData, setTranscriptData] = useState<any[]>([]);

  const fetchAllData = async () => {
    try {
      const [stRes, tcRes, clRes, subRes] = await Promise.all([
        apiClient.get('/students/').catch(() => ({ data: [] })),
        apiClient.get('/academic/teachers/').catch(() => ({ data: [] })),
        apiClient.get('/academic/classrooms/').catch(() => ({ data: [] })),
        apiClient.get('/academic/performance/subjects').catch(() => ({ data: [] }))
      ]);
      setStudents(stRes.data);
      setTeachers(tcRes.data);
      setClassrooms(clRes.data);
      setSubjects(subRes.data);
    } catch (err) {
      console.error("Fetch error:", err);
    }
  };

  useEffect(() => { 
    fetchAllData(); 
    const handleSyncComplete = () => {
      setSyncStatus('Background sync complete. Data is now live.');
      fetchAllData();
      setTimeout(() => setSyncStatus(''), 4000);
    };
    window.addEventListener('offline-sync-complete', handleSyncComplete);
    return () => window.removeEventListener('offline-sync-complete', handleSyncComplete);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token'); 
    localStorage.removeItem('access_token');
    document.cookie = 'token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    router.push('/login');
  };

  const executeMutation = async (endpoint: string, payload: any, resetters: Function[]) => {
    setIsLoading(true); setError(''); setSyncStatus('');
    try {
      const result = await safeMutate('POST', endpoint, payload);
      resetters.forEach(fn => fn(''));
      
      if (result.offline) {
        setSyncStatus('Network unstable. Data saved locally and queued for background sync.');
      } else {
        await fetchAllData();
        if (endpoint.includes('grades')) {
          setSyncStatus('Grade successfully recorded to student transcript.');
        } else if (endpoint.includes('attendance')) {
          setSyncStatus('Roll call registered successfully.');
        } else if (endpoint.includes('enrollments')) {
          setSyncStatus('Student bound to classroom matrix.');
        }
        setTimeout(() => setSyncStatus(''), 4000);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || JSON.stringify(err.response?.data) || 'Mutation failed.');
    } finally {
      setIsLoading(false);
    }
  };

  const loadTranscript = async (studentId: string) => {
    setTSelectedStudent(studentId);
    if (!studentId) {
      setTranscriptData([]);
      return;
    }
    try {
      const res = await apiClient.get(`/academic/performance/transcripts/${studentId}`);
      setTranscriptData(res.data);
    } catch (err) {
      console.error("Failed to load transcript");
    }
  };

  const cumulativeAverage = transcriptData.length > 0 
    ? (transcriptData.reduce((acc, curr) => acc + curr.score, 0) / transcriptData.length).toFixed(1) 
    : 0;

  return (
    <div className="p-8 min-h-screen bg-slate-50 space-y-6 print:p-0 print:bg-white">
      <ServiceWorkerRegistry />
      
      <div className="flex justify-between items-center max-w-6xl mx-auto print:hidden">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Local Operations Plane</h1>
        <Button onClick={handleLogout} variant="destructive">Disconnect</Button>
      </div>

      <div className="max-w-6xl mx-auto flex gap-4 border-b pb-4 overflow-x-auto print:hidden">
        <Button variant={activeTab === 'students' ? 'default' : 'outline'} onClick={() => setActiveTab('students')}>Students</Button>
        <Button variant={activeTab === 'teachers' ? 'default' : 'outline'} onClick={() => setActiveTab('teachers')}>Teachers</Button>
        <Button variant={activeTab === 'classrooms' ? 'default' : 'outline'} onClick={() => setActiveTab('classrooms')}>Classrooms</Button>
        <Button variant={activeTab === 'enrollments' ? 'default' : 'outline'} onClick={() => setActiveTab('enrollments')}>Enrollment</Button>
        <Button variant={activeTab === 'subjects' ? 'default' : 'outline'} onClick={() => setActiveTab('subjects')}>Subjects</Button>
        <Button variant={activeTab === 'attendance' ? 'default' : 'outline'} onClick={() => setActiveTab('attendance')}>Roll Call</Button>
        <Button variant={activeTab === 'grades' ? 'default' : 'outline'} onClick={() => setActiveTab('grades')}>Grades</Button>
        <Button variant={activeTab === 'transcripts' ? 'default' : 'outline'} onClick={() => setActiveTab('transcripts')}>Transcripts</Button>
      </div>
      
      {error && <div className="max-w-6xl mx-auto text-sm font-medium text-red-600 bg-red-50 border border-red-200 p-3 rounded-md print:hidden">{error}</div>}
      {syncStatus && <div className="max-w-6xl mx-auto text-sm font-medium text-amber-700 bg-amber-50 border border-amber-200 p-3 rounded-md print:hidden">{syncStatus}</div>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-6xl mx-auto print:block">
        
        <Card className="md:col-span-1 h-fit shadow-md print:hidden">
          <CardHeader>
            <CardTitle>
              {activeTab === 'students' && 'Admit Student'}
              {activeTab === 'teachers' && 'Onboard Teacher'}
              {activeTab === 'classrooms' && 'Create Classroom'}
              {activeTab === 'enrollments' && 'Assign to Class'}
              {activeTab === 'subjects' && 'Register Subject'}
              {activeTab === 'attendance' && 'Mark Attendance'}
              {activeTab === 'grades' && 'Enter Assessment'}
              {activeTab === 'transcripts' && 'Pull Report Card'}
            </CardTitle>
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

            {activeTab === 'enrollments' && (
              <form onSubmit={(e) => { e.preventDefault(); executeMutation('/academic/performance/enrollments', { student_id: eStudent, classroom_id: eClassroom, academic_year: eYear }, [setEStudent]); }} className="space-y-4">
                <select required value={eStudent} onChange={e => setEStudent(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm bg-white">
                  <option value="">Select Student...</option>
                  {students.map(s => <option key={s.id} value={s.id}>{s.first_name} {s.last_name} ({s.admission_number})</option>)}
                </select>
                <select required value={eClassroom} onChange={e => setEClassroom(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm bg-white">
                  <option value="">Select Classroom...</option>
                  {classrooms.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
                <input required placeholder="Year (e.g., 2025/2026)" value={eYear} onChange={e => setEYear(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm" />
                <Button className="w-full" type="submit" disabled={isLoading}>{isLoading ? 'Processing...' : 'Enroll Student'}</Button>
              </form>
            )}

            {activeTab === 'subjects' && (
              <form onSubmit={(e) => { e.preventDefault(); executeMutation('/academic/performance/subjects', { name: subName, code: subCode }, [setSubName, setSubCode]); }} className="space-y-4">
                <input required placeholder="Subject Name (e.g., Mathematics)" value={subName} onChange={e => setSubName(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm" />
                <input required placeholder="Subject Code (e.g., MTH101)" value={subCode} onChange={e => setSubCode(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm" />
                <Button className="w-full" type="submit" disabled={isLoading}>{isLoading ? 'Processing...' : 'Register Subject'}</Button>
              </form>
            )}

            {activeTab === 'attendance' && (
              <form onSubmit={(e) => { e.preventDefault(); executeMutation('/academic/performance/attendance', { student_id: aStudent, classroom_id: aClassroom, date: aDate, status: aStatus }, [setAStudent]); }} className="space-y-4">
                <select required value={aClassroom} onChange={e => setAClassroom(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm bg-white">
                  <option value="">Select Classroom...</option>
                  {classrooms.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
                <select required value={aStudent} onChange={e => setAStudent(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm bg-white">
                  <option value="">Select Student...</option>
                  {students.map(s => <option key={s.id} value={s.id}>{s.first_name} {s.last_name} ({s.admission_number})</option>)}
                </select>
                <div className="flex gap-2">
                  <input required type="date" value={aDate} onChange={e => setADate(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm" />
                  <select required value={aStatus} onChange={e => setAStatus(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm bg-white">
                    <option value="Present">Present</option>
                    <option value="Absent">Absent</option>
                    <option value="Late">Late</option>
                  </select>
                </div>
                <Button className="w-full" type="submit" disabled={isLoading}>{isLoading ? 'Processing...' : 'Submit Roll Call'}</Button>
              </form>
            )}

            {activeTab === 'grades' && (
              <form onSubmit={(e) => { e.preventDefault(); executeMutation('/academic/performance/grades', { student_id: gStudent, subject_id: gSubject, term: gTerm, academic_year: gYear, score: parseFloat(gScore) }, [setGScore]); }} className="space-y-4">
                <select required value={gStudent} onChange={e => setGStudent(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm bg-white">
                  <option value="">Select Student...</option>
                  {students.map(s => <option key={s.id} value={s.id}>{s.first_name} {s.last_name} ({s.admission_number})</option>)}
                </select>
                <select required value={gSubject} onChange={e => setGSubject(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm bg-white">
                  <option value="">Select Subject...</option>
                  {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
                <div className="flex gap-2">
                  <select required value={gTerm} onChange={e => setGTerm(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm bg-white">
                    <option value="First Term">First Term</option>
                    <option value="Second Term">Second Term</option>
                    <option value="Third Term">Third Term</option>
                  </select>
                  <input required placeholder="Year (e.g., 2025/2026)" value={gYear} onChange={e => setGYear(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm" />
                </div>
                <input required type="number" step="0.1" min="0" max="100" placeholder="Score (0-100)" value={gScore} onChange={e => setGScore(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm" />
                <Button className="w-full" type="submit" disabled={isLoading}>{isLoading ? 'Processing...' : 'Record Grade'}</Button>
              </form>
            )}

            {activeTab === 'transcripts' && (
              <div className="space-y-4">
                <select required value={tSelectedStudent} onChange={e => loadTranscript(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm bg-white">
                  <option value="">Select Student...</option>
                  {students.map(s => <option key={s.id} value={s.id}>{s.first_name} {s.last_name} ({s.admission_number})</option>)}
                </select>
                <Button className="w-full" variant="outline" onClick={() => window.print()} disabled={!tSelectedStudent}>Print Transcript</Button>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="md:col-span-2 shadow-md print:shadow-none print:border-none">
          <CardHeader className="print:hidden">
            <CardTitle>System Directory</CardTitle>
            <CardDescription>
              {activeTab === 'grades' ? 'Select parameters on the left to record assessments.' : 
               activeTab === 'attendance' ? 'Offline-capable daily presence matrix active.' :
               activeTab === 'enrollments' ? 'Bind existing students to their assigned physical classrooms.' :
               activeTab === 'transcripts' ? 'Official Academic Report generated from the ledger.' :
               `Viewing ${activeTab} for this institution.`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {activeTab === 'transcripts' ? (
              tSelectedStudent ? (
                <div className="space-y-6">
                  <div className="text-center border-b pb-4">
                    <h2 className="text-2xl font-bold uppercase tracking-widest text-slate-900">Official Transcript</h2>
                    <p className="text-slate-500">
                      {students.find(s => s.id === tSelectedStudent)?.first_name} {students.find(s => s.id === tSelectedStudent)?.last_name} 
                      {' '} | Admission: {students.find(s => s.id === tSelectedStudent)?.admission_number}
                    </p>
                  </div>
                  
                  <table className="w-full text-sm text-left border rounded-md overflow-hidden">
                    <thead className="bg-slate-100 text-slate-700">
                      <tr>
                        <th className="p-3">Subject</th>
                        <th className="p-3">Code</th>
                        <th className="p-3">Term</th>
                        <th className="p-3">Year</th>
                        <th className="p-3 text-right">Score (%)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y bg-white">
                      {transcriptData.map(t => (
                        <tr key={t.id}>
                          <td className="p-3 font-medium text-slate-900">{t.subject_name}</td>
                          <td className="p-3 text-slate-600">{t.subject_code}</td>
                          <td className="p-3 text-slate-600">{t.term}</td>
                          <td className="p-3 text-slate-600">{t.academic_year}</td>
                          <td className="p-3 text-right font-bold text-slate-900">{t.score}</td>
                        </tr>
                      ))}
                      {transcriptData.length === 0 && (
                        <tr><td colSpan={5} className="p-8 text-center text-slate-500">No grades recorded for this student.</td></tr>
                      )}
                    </tbody>
                  </table>

                  {transcriptData.length > 0 && (
                    <div className="flex justify-end pt-4">
                      <div className="bg-slate-100 px-6 py-3 rounded-md border text-right">
                        <p className="text-sm text-slate-500 font-medium uppercase">Cumulative Average</p>
                        <p className="text-3xl font-bold text-slate-900">{cumulativeAverage}%</p>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-8 text-center text-slate-500 bg-slate-50 rounded border border-dashed print:hidden">
                  Awaiting student selection for transcript generation.
                </div>
              )
            ) : activeTab === 'grades' ? (
              <div className="p-8 text-center text-slate-500 bg-slate-50 rounded border border-dashed">
                Transcript generation matrix is active. Use the form to mathematically bind grades to students.
              </div>
            ) : activeTab === 'attendance' ? (
              <div className="p-8 text-center text-slate-500 bg-slate-50 rounded border border-dashed">
                Roll call matrix is active. Select classroom, student, date, and status. Network volatility is handled automatically.
              </div>
            ) : activeTab === 'enrollments' ? (
              <div className="p-8 text-center text-slate-500 bg-slate-50 rounded border border-dashed">
                Enrollment matrix is active. Bind students to physical classrooms to expose them to teacher-level operations.
              </div>
            ) : (
              <div className="border rounded-md divide-y overflow-hidden shadow-sm bg-white">
                {activeTab === 'students' && students.map(s => (
                  <div key={s.id} className="p-4 flex justify-between"><p className="font-bold text-slate-900">{s.first_name} {s.last_name}</p><p className="text-sm text-slate-500">Admitted: {s.admission_number}</p></div>
                ))}
                {activeTab === 'teachers' && teachers.map(t => (
                  <div key={t.id} className="p-4 flex justify-between"><p className="font-bold text-slate-900">{t.first_name} {t.last_name}</p><p className="text-sm text-slate-500">ID: {t.employee_id}</p></div>
                ))}
                {activeTab === 'classrooms' && classrooms.map(c => {
                  const assigned = teachers.find(t => t.id === c.teacher_id);
                  return (
                    <div key={c.id} className="p-4 flex justify-between"><p className="font-bold text-slate-900">{c.name}</p><p className="text-sm text-slate-500">Teacher: {assigned ? `${assigned.first_name} ${assigned.last_name}` : 'Unassigned'}</p></div>
                  )
                })}
                {activeTab === 'subjects' && subjects.map(s => (
                  <div key={s.id} className="p-4 flex justify-between"><p className="font-bold text-slate-900">{s.name}</p><p className="text-sm text-slate-500">Code: {s.code}</p></div>
                ))}
                
                {((activeTab === 'students' && !students.length) || 
                  (activeTab === 'teachers' && !teachers.length) || 
                  (activeTab === 'classrooms' && !classrooms.length) ||
                  (activeTab === 'subjects' && !subjects.length)) && (
                  <div className="p-8 text-center text-slate-500">No records found.</div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}