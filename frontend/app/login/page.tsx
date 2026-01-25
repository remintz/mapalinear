"use client";

import { signIn } from "next-auth/react";
import { useSearchParams } from "next/navigation";
import { Map } from "lucide-react";
import { Suspense, useEffect, useRef } from "react";

function LoginContent() {
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get("callbackUrl") || "/search";
  const error = searchParams.get("error");
  const autoLogin = searchParams.get("auto") === "true";
  const hasTriggeredAutoLogin = useRef(false);

  // Auto-trigger Google login when coming from header button
  useEffect(() => {
    if (autoLogin && !error && !hasTriggeredAutoLogin.current) {
      hasTriggeredAutoLogin.current = true;
      signIn("google", { callbackUrl });
    }
  }, [autoLogin, error, callbackUrl]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 px-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8">
        {/* Logo and Title */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-2xl mb-4">
            <Map className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">OraPOIS</h1>
          <p className="mt-2 text-gray-600">
            Pontos de interesse para suas viagens
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600">
              {error === "OAuthSignin"
                ? "Erro ao iniciar login com Google."
                : error === "OAuthCallback"
                ? "Erro ao processar resposta do Google."
                : error === "OAuthAccountNotLinked"
                ? "Este email ja esta vinculado a outra conta."
                : "Ocorreu um erro durante o login."}
            </p>
          </div>
        )}

        {/* Login Button */}
        <button
          onClick={() => signIn("google", { callbackUrl })}
          className="w-full flex items-center justify-center gap-3 px-6 py-3 bg-white border-2 border-gray-200 rounded-xl text-gray-700 font-medium hover:bg-gray-50 hover:border-gray-300 transition-all duration-200"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="#FBBC05"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            />
            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            />
          </svg>
          <span>Entrar com Google</span>
        </button>

        {/* Info Text */}
        <p className="mt-6 text-center text-sm text-gray-500">
          Ao entrar, voce concorda com nossos termos de uso e politica de privacidade.
        </p>

        {/* Features */}
        <div className="mt-8 pt-6 border-t border-gray-100">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Com sua conta voce pode:</h3>
          <ul className="space-y-2 text-sm text-gray-600">
            <li className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 bg-blue-500 rounded-full"></span>
              Salvar mapas de viagens
            </li>
            <li className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 bg-blue-500 rounded-full"></span>
              Acessar seus mapas em qualquer dispositivo
            </li>
            <li className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 bg-blue-500 rounded-full"></span>
              Exportar rotas para GPS
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="animate-pulse text-gray-500">Carregando...</div>
      </div>
    }>
      <LoginContent />
    </Suspense>
  );
}
