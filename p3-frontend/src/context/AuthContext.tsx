import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export interface AuthUser {
  name: string;
  email: string;
  badge: string;
  role: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);
const STORAGE_KEY = "ciphertrail:auth_user";

export const DEMO_CREDENTIALS = {
  email: "officer@cid.karnataka.gov.in",
  password: "CipherTrail@123",
};

const DEMO_USER: AuthUser = {
  name: "Investigating Officer",
  email: DEMO_CREDENTIALS.email,
  badge: "IO-4471",
  role: "CID Cyber Crime Unit",
};

function readStoredUser(): AuthUser | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as AuthUser) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => readStoredUser());

  useEffect(() => {
    if (user) window.localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
    else window.localStorage.removeItem(STORAGE_KEY);
  }, [user]);

  const login = async (email: string, password: string) => {
    // No backend required: this validates against a fixed demo account so the
    // login screen behaves like a real gate while the whole app stays usable offline.
    await new Promise((resolve) => setTimeout(resolve, 500));

    const normalizedEmail = email.trim().toLowerCase();
    if (
      normalizedEmail === DEMO_CREDENTIALS.email.toLowerCase() &&
      password === DEMO_CREDENTIALS.password
    ) {
      setUser(DEMO_USER);
      return;
    }
    throw new Error("Invalid email or password.");
  };

  const logout = () => setUser(null);

  const value = useMemo(
    () => ({ user, isAuthenticated: Boolean(user), login, logout }),
    [user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
