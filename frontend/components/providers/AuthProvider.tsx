"use client";

import { SessionProvider } from "next-auth/react";
import { ReactNode } from "react";
import { AuthErrorDisplay } from "@/components/auth/AuthErrorDisplay";
import { LoginTracker } from "@/components/auth/LoginTracker";

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  return (
    <SessionProvider>
      <AuthErrorDisplay />
      <LoginTracker />
      {children}
    </SessionProvider>
  );
}
