'use client';

import { useEntitlements } from './EntitlementProvider';
import type { FeatureCodeValue } from '@/types/subscriptions';

export function UpgradeRequired({ feature }: { feature: string }) {
  return <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"><p className="font-semibold">Upgrade required</p><p>{feature} is not included in this school&apos;s current plan.</p></div>;
}

export function FeatureGate({ feature, children, fallback, hide = false }: { feature: FeatureCodeValue; children: React.ReactNode; fallback?: React.ReactNode; hide?: boolean }) {
  const { hasFeature, isLoading } = useEntitlements();
  if (isLoading) return <div className="h-20 animate-pulse rounded-md bg-slate-100" />;
  if (!hasFeature(feature)) return hide ? null : (fallback ?? <UpgradeRequired feature={feature} />);
  return children;
}
