"use client";

import { signIn, signOut, useSession } from "next-auth/react";
import { LogIn, LogOut, User, Loader2 } from "lucide-react";
import Image from "next/image";
import { useAnalytics } from "@/hooks/useAnalytics";

export function LoginButton() {
  const { data: session, status } = useSession();
  const { trackAuthEvent } = useAnalytics();

  if (status === "loading") {
    return (
      <div className="flex items-center gap-2 px-3 py-2 text-gray-500">
        <Loader2 className="w-4 h-4 animate-spin" />
        <span className="hidden sm:inline text-sm">Carregando...</span>
      </div>
    );
  }

  if (session?.user) {
    return (
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-2 px-2">
          {session.user.image ? (
            <Image
              src={session.user.image}
              alt={session.user.name || "Avatar"}
              width={32}
              height={32}
              className="rounded-full"
            />
          ) : (
            <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
              <User className="w-4 h-4 text-blue-600" />
            </div>
          )}
          <span className="hidden sm:inline text-sm font-medium text-gray-700 max-w-[120px] truncate">
            {session.user.name}
          </span>
        </div>
        <button
          onClick={() => {
            // Track logout event
            trackAuthEvent('logout', { user_id: session.user.id });
            // Clear admin simulation mode on logout
            sessionStorage.removeItem('mapalinear_simulate_user');
            signOut();
          }}
          className="flex items-center gap-1 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors"
          title="Sair"
        >
          <LogOut className="w-4 h-4" />
          <span className="hidden sm:inline">Sair</span>
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={() => {
        trackAuthEvent('login', { provider: 'google' });
        signIn("google");
      }}
      className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
    >
      <LogIn className="w-4 h-4" />
      <span>Entrar com Google</span>
    </button>
  );
}
