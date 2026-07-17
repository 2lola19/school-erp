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