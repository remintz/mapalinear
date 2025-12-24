"use client";

import { useImpersonation } from "@/hooks/useImpersonation";
import { Eye, XCircle, Loader2 } from "lucide-react";

export function ImpersonationBanner() {
  const {
    isImpersonating,
    impersonatedUser,
    stopImpersonation,
    isStopping,
  } = useImpersonation();

  if (!isImpersonating || !impersonatedUser) {
    return null;
  }

  return (
    <div className="bg-amber-500 text-white px-4 py-2 flex items-center justify-between shadow-md z-50">
      <div className="flex items-center gap-2">
        <Eye className="w-5 h-5" />
        <span className="font-medium">
          Visualizando como:{" "}
          <span className="font-bold">{impersonatedUser.name}</span>
          <span className="text-amber-100 ml-2">({impersonatedUser.email})</span>
        </span>
      </div>
      <button
        onClick={stopImpersonation}
        disabled={isStopping}
        className="flex items-center gap-2 bg-amber-600 hover:bg-amber-700 px-3 py-1 rounded-md text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isStopping ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Saindo...
          </>
        ) : (
          <>
            <XCircle className="w-4 h-4" />
            Sair da Visualização
          </>
        )}
      </button>
    </div>
  );
}
