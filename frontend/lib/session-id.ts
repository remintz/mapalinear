/**
 * Session ID management for correlating frontend errors with API calls.
 *
 * The session ID is a unique identifier generated when the user opens the application.
 * It persists until the browser tab is closed and is sent with every API request
 * to enable correlation of frontend errors with backend API call logs.
 */

const SESSION_ID_KEY = 'mapalinear_session_id';

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
      sessionId = crypto.randomUUID();
      sessionStorage.setItem(SESSION_ID_KEY, sessionId);
    }

    return sessionId;
  } catch {
    // sessionStorage might be disabled (e.g., private browsing in some browsers)
    // Fall back to a temporary ID that won't persist
    return crypto.randomUUID();
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
