"use client";

import { SessionProvider } from "next-auth/react";
import { ReactNode } from "react";
import { AuthErrorDisplay } from "@/components/auth/AuthErrorDisplay";

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  return (
    <SessionProvider>
      <AuthErrorDisplay />
      {children}
    </SessionProvider>
  );
}
