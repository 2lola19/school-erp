'use client';

import { useEntitlements } from './EntitlementProvider';
import type { FeatureCodeValue } from '@/types/subscriptions';

export function QuotaGate({ feature, requestedAmount = 1, children, fallback }: { feature: FeatureCodeValue; requestedAmount?: number; children: React.ReactNode; fallback?: React.ReactNode }) {
  const { getLimit, usage } = useEntitlements();
  const limit = getLimit(feature);
  const current = usage.find((item) => item.feature_code === feature)?.current_usage ?? 0;
  if (limit !== null && current + requestedAmount > limit) {
    return fallback ?? <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-800">Quota reached ({current.toLocaleString()} of {limit.toLocaleString()}). Archive records or upgrade before creating more.</div>;
  }
  return children;
}
