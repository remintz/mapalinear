'use client';

import { ReactNode, useEffect } from 'react';
import {
  setupGlobalErrorHandlers,
  cleanupGlobalErrorHandlers,
} from '@/lib/error-reporter';
import { getSessionId } from '@/lib/session-id';

interface ErrorReporterProviderProps {
  children: ReactNode;
}

/**
 * Provider that initializes global error handlers and session ID.
 *
 * This provider should be placed near the root of the application,
 * inside other providers that it might depend on (like AuthProvider).
 *
 * It sets up:
 * - Session ID generation/retrieval
 * - Global window.onerror handler
 * - Unhandled promise rejection handler
 */
export function ErrorReporterProvider({
  children,
}: ErrorReporterProviderProps) {
  useEffect(() => {
    // Initialize session ID (creates one if it doesn't exist)
    const sessionId = getSessionId();
    if (sessionId) {
      console.debug('[ErrorReporter] Session ID:', sessionId.slice(0, 8) + '...');
    }

    // Set up global error handlers
    setupGlobalErrorHandlers();

    // Cleanup on unmount
    return () => {
      cleanupGlobalErrorHandlers();
    };
  }, []);

  return <>{children}</>;
}
