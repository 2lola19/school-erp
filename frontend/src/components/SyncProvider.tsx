"use client";

import { useEffect } from "react";
import { initSyncListeners } from "@/lib/sync/syncEngine";

export function SyncProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    initSyncListeners();
  }, []);

  return <>{children}</>;
}