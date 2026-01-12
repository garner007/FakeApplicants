"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { useRouter, usePathname } from "next/navigation";

// User type
export interface User {
  id: string;
  email: string;
  name: string;
  role: "superadmin" | "admin" | "user" | "viewer";
  is_active: boolean;
  must_change_password: boolean;
  must_change_email: boolean;
  last_login_at: string | null;
}

// Auth context type
interface AuthContextType {
  user: User | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  initialSetup: (currentPassword: string, newEmail: string | null, newPassword: string) => Promise<void>;
  refreshUser: () => Promise<void>;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isSuperAdmin: boolean;
  mustChangePassword: boolean;
  mustChangeEmail: boolean;
  requiresSetup: boolean;
}

// Create context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// API base URL
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Auth provider component
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const pathname = usePathname();

  // Fetch current user
  const refreshUser = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/auth/me`, {
        credentials: "include",
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        setError(null);
      } else if (response.status === 401) {
        setUser(null);
      } else {
        setUser(null);
      }
    } catch (err) {
      console.error("Failed to fetch user:", err);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // Check auth on mount
  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  // Handle redirects based on auth state
  useEffect(() => {
    if (loading) return;

    const publicPaths = ["/login"];
    const setupPath = "/setup";
    const isPublicPath = publicPaths.includes(pathname);
    const requiresSetup = user?.must_change_password || user?.must_change_email;

    if (!user && !isPublicPath) {
      // Not authenticated, redirect to login
      router.push("/login");
    } else if (user && requiresSetup && pathname !== setupPath) {
      // Must complete initial setup, redirect to setup page
      router.push(setupPath);
    } else if (user && isPublicPath && !requiresSetup) {
      // Authenticated on login page, redirect to home
      router.push("/");
    }
  }, [user, loading, pathname, router]);

  // Login function
  const login = async (email: string, password: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({ email, password }),
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);

        if (userData.must_change_password || userData.must_change_email) {
          router.push("/setup");
        } else {
          router.push("/");
        }
      } else {
        const errorData = await response.json();
        setError(errorData.detail || "Login failed");
        throw new Error(errorData.detail || "Login failed");
      }
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
        throw err;
      }
      setError("Login failed");
      throw new Error("Login failed");
    } finally {
      setLoading(false);
    }
  };

  // Logout function
  const logout = async () => {
    try {
      await fetch(`${API_BASE}/api/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch (err) {
      console.error("Logout error:", err);
    } finally {
      setUser(null);
      router.push("/login");
    }
  };

  // Change password function (for normal password changes)
  const changePassword = async (currentPassword: string, newPassword: string) => {
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/api/auth/change-password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });

      if (response.ok) {
        // Refresh user to update must_change_password flag
        await refreshUser();
        router.push("/");
      } else {
        const errorData = await response.json();
        setError(errorData.detail || "Password change failed");
        throw new Error(errorData.detail || "Password change failed");
      }
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
        throw err;
      }
      setError("Password change failed");
      throw new Error("Password change failed");
    }
  };

  // Initial setup function (for first login with default credentials)
  const initialSetup = async (currentPassword: string, newEmail: string | null, newPassword: string) => {
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/api/auth/initial-setup`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({
          current_password: currentPassword,
          new_email: newEmail,
          new_password: newPassword,
        }),
      });

      if (response.ok) {
        // Refresh user to update flags
        await refreshUser();
        router.push("/");
      } else {
        const errorData = await response.json();
        setError(errorData.detail || "Setup failed");
        throw new Error(errorData.detail || "Setup failed");
      }
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
        throw err;
      }
      setError("Setup failed");
      throw new Error("Setup failed");
    }
  };

  // Computed properties
  const isAuthenticated = !!user;
  const isAdmin = user?.role === "admin" || user?.role === "superadmin";
  const isSuperAdmin = user?.role === "superadmin";
  const mustChangePassword = user?.must_change_password ?? false;
  const mustChangeEmail = user?.must_change_email ?? false;
  const requiresSetup = mustChangePassword || mustChangeEmail;

  const value: AuthContextType = {
    user,
    loading,
    error,
    login,
    logout,
    changePassword,
    initialSetup,
    refreshUser,
    isAuthenticated,
    isAdmin,
    isSuperAdmin,
    mustChangePassword,
    mustChangeEmail,
    requiresSetup,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Hook to use auth context
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
