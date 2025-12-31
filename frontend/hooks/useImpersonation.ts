"use client";

import { useState, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import { AdminUser } from "@/lib/types";
import { apiClient } from "@/lib/api";

interface UseImpersonationReturn {
  // State
  isImpersonating: boolean;
  impersonatedUser: AdminUser | null;
  realAdmin: AdminUser | null;

  // Actions
  startImpersonation: (userId: string) => Promise<void>;
  stopImpersonation: () => Promise<void>;
  checkStatus: () => Promise<void>;

  // Loading states
  isLoading: boolean;
  isStarting: boolean;
  isStopping: boolean;
  error: string | null;
}

export function useImpersonation(): UseImpersonationReturn {
  const { data: session } = useSession();
  const [isImpersonating, setIsImpersonating] = useState(false);
  const [impersonatedUser, setImpersonatedUser] = useState<AdminUser | null>(null);
  const [realAdmin, setRealAdmin] = useState<AdminUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isStarting, setIsStarting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Check impersonation status from the server
  const checkStatus = useCallback(async () => {
    if (!session?.accessToken) {
      setIsLoading(false);
      return;
    }

    try {
      const data = await apiClient.getImpersonationStatus();

      setIsImpersonating(data.is_impersonating);
      if (data.is_impersonating) {
        setImpersonatedUser(data.current_user);
        setRealAdmin(data.real_admin);
      } else {
        setImpersonatedUser(null);
        setRealAdmin(null);
      }
    } catch (err) {
      // apiClient handles 401 automatically and redirects to login
      // For 403 (not admin), we just ignore
      console.error("Error checking impersonation status:", err);
      // Don't set error state for status check failures
    } finally {
      setIsLoading(false);
    }
  }, [session?.accessToken]);

  // Check status on mount and when session changes
  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  const startImpersonation = useCallback(
    async (userId: string) => {
      if (!session?.accessToken) {
        setError("Não autenticado");
        return;
      }

      setIsStarting(true);
      setError(null);

      try {
        const data = await apiClient.startImpersonation(userId);

        // Update state
        setIsImpersonating(true);
        setImpersonatedUser(data.user);

        // Reload the page to refresh all data with the impersonated user context
        window.location.href = "/";
      } catch (err) {
        // apiClient handles 401 automatically and redirects to login
        setError(err instanceof Error ? err.message : "Erro desconhecido");
        setIsStarting(false);
      }
    },
    [session?.accessToken]
  );

  const stopImpersonation = useCallback(async () => {
    if (!session?.accessToken) {
      setError("Não autenticado");
      return;
    }

    setIsStopping(true);
    setError(null);

    try {
      await apiClient.stopImpersonation();

      // Clear state
      setIsImpersonating(false);
      setImpersonatedUser(null);
      setRealAdmin(null);

      // Reload to go back to admin session
      window.location.href = "/admin/users";
    } catch (err) {
      // apiClient handles 401 automatically and redirects to login
      setError(err instanceof Error ? err.message : "Erro desconhecido");
      setIsStopping(false);
    }
  }, [session?.accessToken]);

  return {
    isImpersonating,
    impersonatedUser,
    realAdmin,
    startImpersonation,
    stopImpersonation,
    checkStatus,
    isLoading,
    isStarting,
    isStopping,
    error,
  };
}
