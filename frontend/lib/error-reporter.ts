/**
 * Error reporting service for sending frontend errors to the backend.
 *
 * Captures JavaScript errors, unhandled promise rejections, and React errors,
 * and sends them to the backend API for logging and analysis.
 */

import { getSessionId } from './session-id';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api';

export type ErrorType =
  | 'unhandled_error'
  | 'unhandled_rejection'
  | 'react_error'
  | 'api_error';

export interface ErrorReport {
  error_type: ErrorType;
  message: string;
  stack_trace?: string;
  component_stack?: string;
  url: string;
  user_id?: string;
  extra_context?: Record<string, unknown>;
}

// Track if handlers are already set up to avoid duplicates
let handlersInitialized = false;

// Queue for errors that occur before the API is ready
let errorQueue: ErrorReport[] = [];
let isProcessingQueue = false;

/**
 * Report an error to the backend.
 *
 * @param report - Error report data
 * @returns Promise that resolves when the error is reported (or fails silently)
 */
export async function reportError(report: ErrorReport): Promise<void> {
  const sessionId = getSessionId();

  // Don't report errors if we don't have a session ID (SSR)
  if (!sessionId) {
    return;
  }

  try {
    const payload = {
      session_id: sessionId,
      error_type: report.error_type,
      message: report.message.slice(0, 5000), // Limit message length
      url: report.url.slice(0, 2000),
      stack_trace: report.stack_trace?.slice(0, 10000),
      component_stack: report.component_stack?.slice(0, 5000),
      user_id: report.user_id,
      extra_context: report.extra_context,
    };

    // Use fetch directly to avoid circular dependency with api.ts
    await fetch(`${API_URL}/frontend-errors`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Session-ID': sessionId,
      },
      body: JSON.stringify(payload),
    });
  } catch {
    // Silently fail - we don't want error reporting to cause more errors
    console.debug('[ErrorReporter] Failed to report error:', report.message);
  }
}

/**
 * Process queued errors.
 */
async function processErrorQueue(): Promise<void> {
  if (isProcessingQueue || errorQueue.length === 0) {
    return;
  }

  isProcessingQueue = true;

  try {
    const errors = [...errorQueue];
    errorQueue = [];

    for (const error of errors) {
      await reportError(error);
    }
  } finally {
    isProcessingQueue = false;
  }
}

/**
 * Queue an error for later reporting.
 * Used when we need to ensure errors are reported even during initialization.
 */
function queueError(report: ErrorReport): void {
  errorQueue.push(report);

  // Try to process queue after a short delay
  setTimeout(() => {
    processErrorQueue();
  }, 100);
}

/**
 * Handle window.onerror events.
 */
function handleWindowError(
  message: Event | string,
  source?: string,
  lineno?: number,
  colno?: number,
  error?: Error
): boolean {
  const errorMessage = typeof message === 'string' ? message : message.type;

  const report: ErrorReport = {
    error_type: 'unhandled_error',
    message: errorMessage,
    stack_trace: error?.stack,
    url: typeof window !== 'undefined' ? window.location.href : '',
    extra_context: {
      source,
      lineno,
      colno,
    },
  };

  queueError(report);

  // Return false to allow default error handling
  return false;
}

/**
 * Handle unhandled promise rejections.
 */
function handleUnhandledRejection(event: PromiseRejectionEvent): void {
  const error = event.reason;
  const message =
    error instanceof Error
      ? error.message
      : typeof error === 'string'
        ? error
        : 'Unhandled promise rejection';

  const report: ErrorReport = {
    error_type: 'unhandled_rejection',
    message,
    stack_trace: error instanceof Error ? error.stack : undefined,
    url: typeof window !== 'undefined' ? window.location.href : '',
  };

  queueError(report);
}

/**
 * Set up global error handlers.
 * Should be called once when the application initializes.
 */
export function setupGlobalErrorHandlers(): void {
  if (typeof window === 'undefined' || handlersInitialized) {
    return;
  }

  handlersInitialized = true;

  // Handle uncaught JavaScript errors
  window.onerror = handleWindowError;

  // Handle unhandled promise rejections
  window.addEventListener('unhandledrejection', handleUnhandledRejection);

  // Process any queued errors
  processErrorQueue();
}

/**
 * Clean up global error handlers.
 * Should be called when the application unmounts.
 */
export function cleanupGlobalErrorHandlers(): void {
  if (typeof window === 'undefined' || !handlersInitialized) {
    return;
  }

  handlersInitialized = false;

  window.onerror = null;
  window.removeEventListener('unhandledrejection', handleUnhandledRejection);
}

/**
 * Report a React error from an Error Boundary.
 *
 * @param error - The error that was caught
 * @param errorInfo - React error info with component stack
 * @param userId - Optional user ID if available
 */
export function reportReactError(
  error: Error,
  errorInfo?: { componentStack?: string },
  userId?: string
): void {
  const report: ErrorReport = {
    error_type: 'react_error',
    message: error.message,
    stack_trace: error.stack,
    component_stack: errorInfo?.componentStack,
    url: typeof window !== 'undefined' ? window.location.href : '',
    user_id: userId,
  };

  queueError(report);
}

/**
 * Report an API error.
 *
 * @param error - The error that occurred
 * @param context - Additional context about the API call
 */
export function reportApiError(
  error: Error,
  context?: {
    url?: string;
    method?: string;
    status?: number;
    userId?: string;
  }
): void {
  const report: ErrorReport = {
    error_type: 'api_error',
    message: error.message,
    stack_trace: error.stack,
    url: typeof window !== 'undefined' ? window.location.href : '',
    user_id: context?.userId,
    extra_context: {
      api_url: context?.url,
      method: context?.method,
      status: context?.status,
    },
  };

  queueError(report);
}
