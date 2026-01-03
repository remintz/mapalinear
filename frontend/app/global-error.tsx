'use client';

import { useEffect } from 'react';
import { reportReactError } from '@/lib/error-reporter';

/**
 * Global error boundary that catches errors in the root layout.
 * This is a fallback for errors that occur outside of the regular error boundary.
 *
 * Note: This component must define its own <html> and <body> tags
 * because the root layout is unavailable when this renders.
 */
export default function GlobalError({
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
    console.error('[Global Error Boundary]', error);
  }, [error]);

  return (
    <html lang="pt-BR">
      <body>
        <div
          style={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: '#f9fafb',
            padding: '1rem',
          }}
        >
          <div
            style={{
              textAlign: 'center',
              padding: '2rem',
              maxWidth: '28rem',
            }}
          >
            <div
              style={{
                width: '4rem',
                height: '4rem',
                margin: '0 auto 1.5rem',
                borderRadius: '50%',
                backgroundColor: '#fee2e2',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <svg
                style={{ width: '2rem', height: '2rem', color: '#dc2626' }}
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

            <h1
              style={{
                fontSize: '1.5rem',
                fontWeight: 'bold',
                color: '#111827',
                marginBottom: '0.5rem',
              }}
            >
              Algo deu errado
            </h1>

            <p
              style={{
                color: '#6b7280',
                marginBottom: '1.5rem',
              }}
            >
              Ocorreu um erro critico. Nossa equipe foi notificada
              automaticamente.
            </p>

            <button
              onClick={() => reset()}
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                backgroundColor: '#2563eb',
                color: 'white',
                borderRadius: '0.5rem',
                border: 'none',
                cursor: 'pointer',
                fontSize: '1rem',
                marginBottom: '0.75rem',
              }}
            >
              Tentar novamente
            </button>

            <a
              href="/"
              style={{
                display: 'block',
                width: '100%',
                padding: '0.75rem 1rem',
                border: '1px solid #d1d5db',
                color: '#374151',
                borderRadius: '0.5rem',
                textDecoration: 'none',
                textAlign: 'center',
              }}
            >
              Voltar ao inicio
            </a>
          </div>
        </div>
      </body>
    </html>
  );
}
