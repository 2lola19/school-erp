'use client';

import { useQuery } from '@tanstack/react-query';
import { createContext, useContext } from 'react';

import { apiClient } from '@/lib/api-client';
import { useAuthStore } from '@/store/authStore';
import type { EffectiveEntitlements, FeatureCodeValue, UsageItem } from '@/types/subscriptions';

interface EntitlementContextValue {
  entitlements: EffectiveEntitlements | null;
  usage: UsageItem[];
  subscriptionStatus: string;
  isLoading: boolean;
  hasFeature: (code: FeatureCodeValue) => boolean;
  getLimit: (code: FeatureCodeValue) => number | null;
  refresh: () => Promise<unknown>;
}

const EntitlementContext = createContext<EntitlementContextValue | null>(null);

export function EntitlementProvider({ children }: { children: React.ReactNode }) {
  const profile = useAuthStore((state) => state.profile);
  const canRead = profile?.permissions.includes('subscriptions.read') ?? false;
  const entitlementQuery = useQuery({
    queryKey: ['entitlements', profile?.tenant_id],
    queryFn: async () => (await apiClient.get<EffectiveEntitlements>('/tenant/subscription/entitlements')).data,
    enabled: Boolean(profile && canRead),
    staleTime: 60_000,
  });
  const usageQuery = useQuery({
    queryKey: ['subscription-usage', profile?.tenant_id],
    queryFn: async () => (await apiClient.get<UsageItem[]>('/tenant/subscription/usage')).data,
    enabled: Boolean(profile && canRead),
    staleTime: 30_000,
  });
  const value: EntitlementContextValue = {
    entitlements: entitlementQuery.data ?? null,
    usage: usageQuery.data ?? [],
    subscriptionStatus: entitlementQuery.data?.status ?? 'UNKNOWN',
    isLoading: entitlementQuery.isLoading || usageQuery.isLoading,
    hasFeature: (code) => entitlementQuery.data?.values[code] === true,
    getLimit: (code) => {
      const raw = entitlementQuery.data?.values[code];
      return typeof raw === 'number' ? raw : null;
    },
    refresh: async () => Promise.all([entitlementQuery.refetch(), usageQuery.refetch()]),
  };
  return <EntitlementContext.Provider value={value}>{children}</EntitlementContext.Provider>;
}

export function useEntitlements(): EntitlementContextValue {
  const context = useContext(EntitlementContext);
  if (!context) throw new Error('useEntitlements must be used inside EntitlementProvider');
  return context;
}
