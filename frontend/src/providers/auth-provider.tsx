"use client";

import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import {
  AUTH_CHANGED_EVENT,
  claimGuestAnalyses,
  clearAuthToken,
  clearGuestToken,
  getAuthToken,
  getGuestToken,
  getMe,
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
  setAuthToken,
} from "@/lib/api-client";
import { ClaimGuestResponse, User } from "@/types/api";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  error: string | null;
  hasGuestSession: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => Promise<void>;
  claimGuest: () => Promise<ClaimGuestResponse | null>;
  dismissGuestClaim: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasGuestSession, setHasGuestSession] = useState(false);
  const revision = useRef(0);

  const checkGuest = useCallback(() => {
    const token = getGuestToken();
    setHasGuestSession(Boolean(token));
  }, []);

  const refreshUser = useCallback(async () => {
    const current = ++revision.current;
    const token = getAuthToken();
    setError(null);
    if (!token) {
      setUser(null);
      setLoading(false);
      checkGuest();
      return;
    }
    setLoading(true);
    try {
      const me = await getMe();
      if (current === revision.current && token === getAuthToken()) setUser(me);
    } catch (err: unknown) {
      if (current === revision.current && token === getAuthToken()) {
        setError(err instanceof Error ? err.message : "Không thể kết nối. Vui lòng thử lại.");
      }
    } finally {
      if (current === revision.current) {
        setLoading(false);
        checkGuest();
      }
    }
  }, [checkGuest]);

  useEffect(() => {
    let active = true;
    const authChanged = () => {
      revision.current += 1;
      setUser(null);
      setError(null);
      setLoading(false);
      checkGuest();
    };
    window.addEventListener(AUTH_CHANGED_EVENT, authChanged);
    void Promise.resolve().then(() => { if (active) return refreshUser(); });
    return () => {
      active = false;
      revision.current += 1;
      window.removeEventListener(AUTH_CHANGED_EVENT, authChanged);
    };
  }, [refreshUser, checkGuest]);

  const login = async (email: string, password: string) => {
    const current = ++revision.current;
    const res = await apiLogin(email, password);
    if (current !== revision.current) return;
    setAuthToken(res.access_token);
    setUser(res.user);
    checkGuest();
  };

  const register = async (email: string, password: string, fullName: string) => {
    const current = ++revision.current;
    const res = await apiRegister(email, password, fullName);
    if (current !== revision.current) return;
    setAuthToken(res.access_token);
    setUser(res.user);
    checkGuest();
  };

  const logout = async () => {
    const pending = apiLogout();
    clearAuthToken();
    await pending;
  };

  const claimGuest = async (): Promise<ClaimGuestResponse | null> => {
    const guestToken = getGuestToken();
    if (!guestToken) return null;
    const res = await claimGuestAnalyses(guestToken);
    setHasGuestSession(false);
    return res;
  };

  const dismissGuestClaim = () => {
    clearGuestToken();
    setHasGuestSession(false);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        error,
        hasGuestSession,
        login,
        register,
        logout,
        claimGuest,
        dismissGuestClaim,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuthContext must be used within an AuthProvider");
  }
  return context;
}
