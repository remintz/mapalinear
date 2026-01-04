"use client";

import { useEffect, useRef } from "react";
import { useSession } from "next-auth/react";
import { useAnalytics } from "@/hooks/useAnalytics";
import { EventType } from "@/lib/analytics-types";

/**
 * Component that tracks login events with optional geolocation.
 *
 * This component monitors the session status and sends a login analytics event
 * when the user successfully authenticates. It attempts to capture the user's
 * location (with their permission) to include in the event data.
 *
 * Must be placed inside a SessionProvider.
 */
export function LoginTracker() {
  const { data: session, status } = useSession();
  const { trackAuthEvent, flush } = useAnalytics();

  // Track if we've already sent the login event for this session
  const hasTrackedLogin = useRef(false);
  // Track previous status to detect transition
  const previousStatus = useRef<string | null>(null);

  useEffect(() => {
    // Detect transition from unauthenticated/loading to authenticated
    const wasNotAuthenticated = previousStatus.current !== "authenticated";
    const isNowAuthenticated = status === "authenticated";

    // Update previous status
    previousStatus.current = status;

    // Only track if:
    // 1. User just became authenticated
    // 2. We haven't tracked this login yet
    // 3. We have session data
    if (wasNotAuthenticated && isNowAuthenticated && !hasTrackedLogin.current && session?.user) {
      hasTrackedLogin.current = true;

      // Try to get user's location
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          (position) => {
            // Success - send login event with location
            trackAuthEvent(
              EventType.LOGIN,
              {
                user_email: session.user?.email,
                user_name: session.user?.name,
                login_method: "google",
                location_permission: "granted",
              },
              {
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
              }
            );
            // Flush immediately to ensure the event is sent
            flush();
          },
          (error) => {
            // Location denied or error - send login event without location
            trackAuthEvent(
              EventType.LOGIN,
              {
                user_email: session.user?.email,
                user_name: session.user?.name,
                login_method: "google",
                location_permission: error.code === error.PERMISSION_DENIED ? "denied" : "error",
                location_error: error.message,
              }
            );
            // Flush immediately
            flush();
          },
          {
            timeout: 5000,
            maximumAge: 60000, // Accept cached position up to 1 minute old
            enableHighAccuracy: false, // Don't need high accuracy for login tracking
          }
        );
      } else {
        // Geolocation not supported - send login event without location
        trackAuthEvent(
          EventType.LOGIN,
          {
            user_email: session.user?.email,
            user_name: session.user?.name,
            login_method: "google",
            location_permission: "unsupported",
          }
        );
        flush();
      }
    }
  }, [status, session, trackAuthEvent, flush]);

  // This component doesn't render anything
  return null;
}
