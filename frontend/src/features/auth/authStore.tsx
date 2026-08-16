import React, { createContext, useContext, useEffect, useState } from "react";
import { apiRequest } from "@/lib/apiClient";
import { clearStoredToken, getStoredToken, setStoredToken } from "@/lib/authToken";

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_staff: boolean;
  is_superuser?: boolean;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isStaff: boolean;
  login: (email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(getStoredToken());
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Initialize and verify session on load
  useEffect(() => {
    async function verifySession() {
      const stored = getStoredToken();
      if (!stored) {
        setIsLoading(false);
        return;
      }

      try {
        const data = await apiRequest<{ user: User }>("auth/me/");
        setUser(data.user);
        setToken(stored);
      } catch (err) {
        console.warn("Stored session invalid or expired", err);
        clearStoredToken();
        setToken(null);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    }

    verifySession();

    // Listen to global 401/403 events
    const handleUnauthorized = () => {
      clearStoredToken();
      setToken(null);
      setUser(null);
    };

    window.addEventListener("tersuite:auth:unauthorized", handleUnauthorized);
    return () => {
      window.removeEventListener("tersuite:auth:unauthorized", handleUnauthorized);
    };
  }, []);

  const login = async (email: string, password: string): Promise<User> => {
    const data = await apiRequest<{ token: string; user: User }>("auth/login/", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });

    setStoredToken(data.token);
    setToken(data.token);
    setUser(data.user);
    return data.user;
  };

  const logout = async (): Promise<void> => {
    try {
      if (token) {
        await apiRequest("auth/logout/", { method: "POST" });
      }
    } catch {
      // Best-effort logout
    } finally {
      clearStoredToken();
      setToken(null);
      setUser(null);
    }
  };

  const isAuthenticated = !!token && !!user;
  const isStaff = !!user && (user.is_staff || !!user.is_superuser);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthenticated,
        isStaff,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
