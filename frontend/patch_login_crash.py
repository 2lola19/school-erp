import os

frontend_code = """'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const { login } = useAuthStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    
    try {
      // Send both email and username formats to satisfy varying Pydantic schemas
      const res = await apiClient.post('/auth/login', { email: email, username: email, password: password });
      const tokenStr = res.data?.access_token || res.data?.token;
      
      if (!tokenStr) {
        throw new Error("Backend returned 200 OK but no token was found.");
      }

      const base64Url = tokenStr.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const payload = JSON.parse(window.atob(base64));

      await login(email, password);

      if (payload.permissions && payload.permissions.includes('view_all_tenants')) {
        router.push('/superadmin');
      } else {
        router.push('/school');
      }
      
    } catch (err: any) {
      console.error(err);
      if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        
        // CRITICAL FIX: Parse FastAPI 422 Array safely
        if (Array.isArray(detail)) {
          const parsedErrors = detail.map((d: any) => `${d.loc[d.loc.length - 1]}: ${d.msg}`).join(' | ');
          setError(`Validation Error -> ${parsedErrors}`);
        } else if (typeof detail === 'string') {
          setError(detail); // Standard 401/403 strings
        } else {
          setError(JSON.stringify(detail)); // Fallback
        }
      } else if (err.message) {
        setError(`Client Error: ${err.message}`);
      } else {
        setError('An unknown connection error occurred.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <Card className="w-full max-w-md shadow-lg">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold">System Login</CardTitle>
          <CardDescription>Enter your credentials to access your control plane</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Email Address</label>
              <input required type="text" value={email} onChange={(e) => setEmail(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Password</label>
              <input required type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500" />
            </div>
            
            {error && (
              <div className="text-sm font-medium text-red-600 bg-red-50 border border-red-200 p-3 rounded-md break-words">
                {error}
              </div>
            )}
            
            <Button className="w-full font-semibold" type="submit" disabled={isLoading}>
              {isLoading ? 'Authenticating...' : 'Sign In'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
"""

with open("src/app/(auth)/login/page.tsx", "w", encoding="utf-8") as f:
    f.write(frontend_code)

print("[+] Frontend React crash patched. Validation errors will now render safely.")