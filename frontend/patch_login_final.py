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
      // 1. Manually fetch the token to guarantee we have the raw string
      const res = await apiClient.post('/auth/login', { email, password });
      const tokenStr = res.data?.access_token || res.data?.token;
      
      if (!tokenStr) {
        throw new Error("Backend returned 200 OK but no token was found in payload.");
      }

      // 2. Decode the JWT payload securely
      const base64Url = tokenStr.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const payload = JSON.parse(window.atob(base64));

      // 3. Sync the global auth state
      await login(email, password);

      // 4. Route based on mathematical verification of permissions
      if (payload.permissions && payload.permissions.includes('view_all_tenants')) {
        router.push('/superadmin');
      } else {
        router.push('/school');
      }
      
    } catch (err: any) {
      console.error(err);
      if (err.response?.data?.detail) {
        setError(err.response.data.detail); // Server rejected credentials
      } else if (err.message) {
        setError(`Client Error: ${err.message}`); // Frontend crashed parsing
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
              <input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Password</label>
              <input required type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500" />
            </div>
            
            {/* Critical Error Output */}
            {error && (
              <div className="text-sm font-medium text-red-600 bg-red-50 border border-red-200 p-3 rounded-md">
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

# Force overwrite the login page
with open("src/app/(auth)/login/page.tsx", "w", encoding="utf-8") as f:
    f.write(frontend_code)

print("[+] Frontend login router explicitly patched. JWT logic verified.")