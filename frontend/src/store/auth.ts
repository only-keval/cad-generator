import { create } from 'zustand';

interface User {
  user_id: number;
  name: string;
  email: string | null;
  is_guest: boolean;
}

interface AuthState {
  token: string | null;
  user: User | null;
  setAuth: (token: string, user: User) => void;
  clearAuth: () => void;
}

function loadAuth(): { token: string | null; user: User | null } {
  try {
    const token = localStorage.getItem('jwt');
    const user = JSON.parse(localStorage.getItem('jwt_user') || 'null');
    return { token, user };
  } catch {
    return { token: null, user: null };
  }
}

export const useAuth = create<AuthState>((set) => {
  const { token, user } = loadAuth();
  return {
    token,
    user,
    setAuth: (token: string, user: User) => {
      localStorage.setItem('jwt', token);
      localStorage.setItem('jwt_user', JSON.stringify(user));
      set({ token, user });
    },
    clearAuth: () => {
      localStorage.removeItem('jwt');
      localStorage.removeItem('jwt_user');
      set({ token: null, user: null });
    },
  };
});
