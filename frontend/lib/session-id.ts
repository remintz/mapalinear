/**
 * Session ID management for correlating frontend errors with API calls.
 *
 * The session ID is a unique identifier generated when the user opens the application.
 * It persists until the browser tab is closed and is sent with every API request
 * to enable correlation of frontend errors with backend API call logs.
 */

const SESSION_ID_KEY = 'mapalinear_session_id';

/**
 * Generate a UUID v4 with fallback for environments where crypto.randomUUID is not available.
 */
function generateUUID(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  // Fallback implementation for older browsers or restricted contexts
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Get or create a session ID.
 *
 * - If a session ID exists in sessionStorage, return it
 * - Otherwise, generate a new UUID v4 and store it
 * - Returns empty string on server-side rendering
 */
export function getSessionId(): string {
  // Return empty string during SSR
  if (typeof window === 'undefined') {
    return '';
  }

  try {
    let sessionId = sessionStorage.getItem(SESSION_ID_KEY);

    if (!sessionId) {
      sessionId = generateUUID();
      sessionStorage.setItem(SESSION_ID_KEY, sessionId);
    }

    return sessionId;
  } catch {
    // sessionStorage might be disabled (e.g., private browsing in some browsers)
    // Fall back to a temporary ID that won't persist
    return generateUUID();
  }
}

/**
 * Clear the current session ID.
 * Useful when user logs out or wants to start a fresh session.
 */
export function clearSessionId(): void {
  if (typeof window === 'undefined') {
    return;
  }

  try {
    sessionStorage.removeItem(SESSION_ID_KEY);
  } catch {
    // Ignore errors if sessionStorage is disabled
  }
}

/**
 * Get the current session ID without creating a new one.
 * Returns null if no session ID exists.
 */
export function getCurrentSessionId(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }

  try {
    return sessionStorage.getItem(SESSION_ID_KEY);
  } catch {
    return null;
  }
}
