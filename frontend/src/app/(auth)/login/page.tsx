'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { apiClient } from '@/lib/api-client';
import { useAuthStore } from '@/store/authStore';
import type { TokenResponse, UserContext } from '@/types/api';

export default function LoginPage() {
  const [domain, setDomain] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const { setAccessToken, setProfile } = useAuthStore();

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsLoading(true);
    setError('');
    try {
      const login = await apiClient.post<TokenResponse>('/auth/login', { domain, email, password });
      setAccessToken(login.data.access_token);
      const context = await apiClient.get<UserContext>('/auth/me');
      setProfile(context.data);
      const primary = context.data.workspaces.find((workspace) => workspace.assignment_type === 'PRIMARY');
      router.replace(primary?.code === 'PLATFORM_ADMIN' ? '/superadmin' : '/school');
    } catch (caught: unknown) {
      const response = caught as { response?: { data?: { detail?: string } } };
      setError(response.response?.data?.detail ?? 'Unable to sign in. Check your school domain and credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <Card className="w-full max-w-md shadow-lg">
        <CardHeader>
          <CardTitle className="text-2xl">School ERP sign in</CardTitle>
          <CardDescription>Use your school domain and staff account.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <label className="block text-sm font-medium">
              School domain
              <input required value={domain} onChange={(event) => setDomain(event.target.value)} placeholder="school.example" className="mt-1 flex h-10 w-full rounded-md border px-3" />
            </label>
            <label className="block text-sm font-medium">
              Email address
              <input required type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} className="mt-1 flex h-10 w-full rounded-md border px-3" />
            </label>
            <label className="block text-sm font-medium">
              Password
              <input required type="password" minLength={8} autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} className="mt-1 flex h-10 w-full rounded-md border px-3" />
            </label>
            {error && <p role="alert" className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
            <Button className="w-full" type="submit" disabled={isLoading}>
              {isLoading ? 'Signing in…' : 'Sign in'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
