import os

env_local = """NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1"""

api_types = """
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface TokenPayload {
  sub: string;
  tenant_id: string;
  role: string;
  exp: number;
}
"""

api_client = """
import axios from 'axios';
import { useAuthStore } from '@/store/authStore';

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
"""

auth_store = """
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { jwtDecode } from 'jwt-decode';
import { TokenPayload } from '@/types/api';

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: TokenPayload | null;
  setTokens: (access: string, refresh: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      setTokens: (access, refresh) => {
        const decoded = jwtDecode<TokenPayload>(access);
        set({ accessToken: access, refreshToken: refresh, user: decoded });
      },
      logout: () => set({ accessToken: null, refreshToken: null, user: null }),
    }),
    {
      name: 'auth-storage',
    }
  )
);
"""

login_form = """
'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export function LoginForm() {
  const [domain, setDomain] = useState('system.local');
  const [email, setEmail] = useState('admin@system.local');
  const [password, setPassword] = useState('SuperSecurePassword123!');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const setTokens = useAuthStore((state) => state.setTokens);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await apiClient.post('/auth/login', { domain, email, password });
      setTokens(res.data.access_token, res.data.refresh_token);
      router.push('/superadmin');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader>
        <CardTitle>System Login</CardTitle>
        <CardDescription>Enter credentials to access the ERP</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleLogin} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="domain">Tenant Domain</Label>
            <Input id="domain" value={domain} onChange={(e) => setDomain(e.target.value)} required />
          </div>
          <div className="space-y-2">
            <Label htmlFor="email">Email Address</Label>
            <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          {error && <p className="text-red-500 text-sm font-medium">{error}</p>}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? 'Authenticating...' : 'Sign In'}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
"""

login_page = """
import { LoginForm } from '@/components/forms/LoginForm';

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
      <LoginForm />
    </div>
  );
}
"""

superadmin_page = """
'use client';
import { useAuthStore } from '@/store/authStore';
import { Button } from '@/components/ui/button';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function SuperAdminDashboard() {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  return (
    <div className="p-8 min-h-screen bg-slate-50">
      <Card className="max-w-2xl mx-auto">
        <CardHeader>
          <CardTitle>Super Admin Interface</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-slate-100 p-4 rounded-md">
            <p className="text-sm font-mono break-all"><strong>Subject ID:</strong> {user?.sub}</p>
            <p className="text-sm font-mono break-all"><strong>Tenant ID:</strong> {user?.tenant_id}</p>
            <p className="text-sm font-mono break-all"><strong>Role ID:</strong> {user?.role}</p>
          </div>
          <Button onClick={handleLogout} variant="destructive">Disconnect Session</Button>
        </CardContent>
      </Card>
    </div>
  );
}
"""

root_page = """
import { redirect } from 'next/navigation';

export default function Home() {
  redirect('/login');
}
"""

providers = """
'use client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';

export default function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
"""

layout_page = """
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Providers from "./providers";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "School ERP",
  description: "Multi-tenant School Management System",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

files_to_write = {
    ".env.local": env_local,
    "src/types/api.d.ts": api_types,
    "src/lib/api-client.ts": api_client,
    "src/store/authStore.ts": auth_store,
    "src/components/forms/LoginForm.tsx": login_form,
    "src/app/(auth)/login/page.tsx": login_page,
    "src/app/(dashboard)/superadmin/page.tsx": superadmin_page,
    "src/app/page.tsx": root_page,
    "src/app/providers.tsx": providers,
    "src/app/layout.tsx": layout_page
}

for path, content in files_to_write.items():
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")

print("[+] Frontend logic populated and wired.")
"""
