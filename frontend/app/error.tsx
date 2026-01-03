'use client';

import { useEffect } from 'react';
import { reportReactError } from '@/lib/error-reporter';
import { getCurrentSessionId } from '@/lib/session-id';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Report error to backend
    reportReactError(error);

    // Also log to console for development
    console.error('[Error Boundary]', error);
  }, [error]);

  const sessionId = getCurrentSessionId();

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="text-center p-8 max-w-md">
        <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-red-100 flex items-center justify-center">
          <svg
            className="w-8 h-8 text-red-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>

        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          Erro inesperado
        </h2>

        <p className="text-gray-600 mb-6">
          Ocorreu um erro ao carregar esta pagina. O problema foi registrado
          automaticamente e nossa equipe sera notificada.
        </p>

        <div className="space-y-3">
          <button
            onClick={() => reset()}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Tentar novamente
          </button>

          <a
            href="/"
            className="block w-full px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Voltar ao inicio
          </a>
        </div>

        {sessionId && (
          <p className="mt-6 text-xs text-gray-400">
            ID da sessao: {sessionId.slice(0, 8)}...
          </p>
        )}
      </div>
    </div>
  );
}
