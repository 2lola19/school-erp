import { create } from 'zustand';

import type { UserContext } from '@/types/api';

interface AuthState {
  accessToken: string | null;
  profile: UserContext | null;
  activeWorkspaceId: string | null;
  initialized: boolean;
  setAccessToken: (accessToken: string) => void;
  setProfile: (profile: UserContext) => void;
  setActiveWorkspace: (assignmentId: string) => void;
  setInitialized: () => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  profile: null,
  activeWorkspaceId: null,
  initialized: false,
  setAccessToken: (accessToken) => set({ accessToken }),
  setProfile: (profile) => {
    const primary = profile.workspaces.find((workspace) => workspace.assignment_type === 'PRIMARY');
    set({ profile, activeWorkspaceId: primary?.assignment_id ?? null });
  },
  setActiveWorkspace: (activeWorkspaceId) => set({ activeWorkspaceId }),
  setInitialized: () => set({ initialized: true }),
  logout: () => set({ accessToken: null, profile: null, activeWorkspaceId: null, initialized: true }),
}));
