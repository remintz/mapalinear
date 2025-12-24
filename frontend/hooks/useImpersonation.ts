"use client";

import { useState, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import {
  AdminUser,
  ImpersonationResponse,
  ImpersonationStatusResponse,
  StopImpersonationResponse,
} from "@/lib/types";

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

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/api";

  // Check impersonation status from the server
  const checkStatus = useCallback(async () => {
    if (!session?.accessToken) {
      setIsLoading(false);
      return;
    }

    try {
      const response = await fetch(`${apiUrl}/admin/impersonation-status`, {
        headers: {
          Authorization: `Bearer ${session.accessToken}`,
        },
      });

      if (!response.ok) {
        // If user is not admin, they won't have access to this endpoint - that's fine
        if (response.status === 403) {
          setIsLoading(false);
          return;
        }
        throw new Error("Falha ao verificar status de impersonation");
      }

      const data: ImpersonationStatusResponse = await response.json();

      setIsImpersonating(data.is_impersonating);
      if (data.is_impersonating) {
        setImpersonatedUser(data.current_user);
        setRealAdmin(data.real_admin);
      } else {
        setImpersonatedUser(null);
        setRealAdmin(null);
      }
    } catch (err) {
      console.error("Error checking impersonation status:", err);
      // Don't set error state for status check failures
    } finally {
      setIsLoading(false);
    }
  }, [session?.accessToken, apiUrl]);

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
        const response = await fetch(`${apiUrl}/admin/impersonate/${userId}`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${session.accessToken}`,
          },
        });

        if (!response.ok) {
          const data = await response.json();
          throw new Error(
            data.message || data.detail || "Falha ao iniciar impersonation"
          );
        }

        const data: ImpersonationResponse = await response.json();

        // Update state
        setIsImpersonating(true);
        setImpersonatedUser(data.user);

        // Reload the page to refresh all data with the impersonated user context
        window.location.href = "/";
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erro desconhecido");
        setIsStarting(false);
      }
    },
    [session?.accessToken, apiUrl]
  );

  const stopImpersonation = useCallback(async () => {
    if (!session?.accessToken) {
      setError("Não autenticado");
      return;
    }

    setIsStopping(true);
    setError(null);

    try {
      const response = await fetch(`${apiUrl}/admin/stop-impersonation`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.accessToken}`,
        },
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(
          data.message || data.detail || "Falha ao parar impersonation"
        );
      }

      const _data: StopImpersonationResponse = await response.json();

      // Clear state
      setIsImpersonating(false);
      setImpersonatedUser(null);
      setRealAdmin(null);

      // Reload to go back to admin session
      window.location.href = "/admin/users";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro desconhecido");
      setIsStopping(false);
    }
  }, [session?.accessToken, apiUrl]);

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
