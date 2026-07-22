'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

import { apiClient } from '@/lib/api-client';
import { useAuthStore } from '@/store/authStore';
import type { TokenResponse, UserContext } from '@/types/api';
import { EntitlementProvider } from '@/components/entitlements/EntitlementProvider';

function AuthBootstrap() {
  const { setAccessToken, setInitialized, setProfile } = useAuthStore();

  useEffect(() => {
    let active = true;
    async function restoreSession() {
      try {
        const token = await apiClient.post<TokenResponse>('/auth/refresh');
        if (!active) return;
        setAccessToken(token.data.access_token);
        const context = await apiClient.get<UserContext>('/auth/me');
        if (active) setProfile(context.data);
      } catch {
        // No refresh cookie is a normal anonymous state.
      } finally {
        if (active) setInitialized();
      }
    }
    restoreSession();
    return () => { active = false; };
  }, [setAccessToken, setInitialized, setProfile]);

  return null;
}

export default function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());
  return (
    <QueryClientProvider client={queryClient}>
      <AuthBootstrap />
      <EntitlementProvider>{children}</EntitlementProvider>
    </QueryClientProvider>
  );
}
