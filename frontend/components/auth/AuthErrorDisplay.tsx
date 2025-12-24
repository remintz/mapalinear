"use client";

import { useSession } from "next-auth/react";
import { useEffect, useState } from "react";
import { AlertTriangle, X } from "lucide-react";

export function AuthErrorDisplay() {
  const { data: session } = useSession();
  const [dismissed, setDismissed] = useState(false);

  // Reset dismissed state when error changes
  useEffect(() => {
    if (session?.authError) {
      setDismissed(false);
    }
  }, [session?.authError]);

  // Don't show if no error or if dismissed
  if (!session?.authError || dismissed) {
    return null;
  }

  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-red-600 text-white px-4 py-3 shadow-lg">
      <div className="max-w-4xl mx-auto flex items-start gap-3">
        <AlertTriangle className="h-5 w-5 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <p className="font-semibold text-sm">Erro de Autenticacao</p>
          <p className="text-xs mt-1 opacity-90">
            Seu login com Google foi bem-sucedido, mas houve um erro ao conectar com o servidor.
          </p>
          <p className="text-xs mt-2 font-mono bg-red-700 px-2 py-1 rounded inline-block">
            {session.authError}
          </p>
          <p className="text-xs mt-2 opacity-75">
            Por favor, tire um screenshot desta mensagem e envie para o administrador.
          </p>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="p-1 hover:bg-red-700 rounded"
          aria-label="Fechar"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
