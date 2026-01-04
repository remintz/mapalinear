/**
 * Analytics hook for tracking user events.
 *
 * Provides methods to track user behavior, feature usage, errors, and performance metrics.
 * Events are batched and sent to the backend periodically or when the user leaves the page.
 */

import { useCallback, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { getSessionId } from '@/lib/session-id';
import {
  UserEvent,
  DeviceInfo,
  DeviceType,
  EventCategory,
  EventType,
  getCategoryForEventType,
} from '@/lib/analytics-types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api';

// Configuration
const FLUSH_INTERVAL_MS = 5000; // 5 seconds
const MAX_BATCH_SIZE = 100;

// Module-level state for the event queue (singleton)
let eventQueue: UserEvent[] = [];
let flushTimeoutId: NodeJS.Timeout | null = null;
let deviceInfo: DeviceInfo | null = null;

/**
 * Detect device type from user agent.
 */
function detectDeviceType(userAgent: string): DeviceType {
  const ua = userAgent.toLowerCase();

  if (/mobile|android|iphone|ipod|blackberry|windows phone/i.test(ua)) {
    return 'mobile';
  }

  if (/tablet|ipad/i.test(ua)) {
    return 'tablet';
  }

  return 'desktop';
}

/**
 * Detect OS from user agent.
 */
function detectOS(userAgent: string): string {
  const ua = userAgent;

  if (/Windows/i.test(ua)) {
    const match = ua.match(/Windows NT (\d+\.\d+)/);
    const version = match ? match[1] : '';
    const versionMap: Record<string, string> = {
      '10.0': '10/11',
      '6.3': '8.1',
      '6.2': '8',
      '6.1': '7',
    };
    return `Windows ${versionMap[version] || version}`;
  }

  if (/Mac OS X/i.test(ua)) {
    const match = ua.match(/Mac OS X ([\d_]+)/);
    const version = match ? match[1].replace(/_/g, '.') : '';
    return `macOS ${version}`;
  }

  if (/iPhone|iPad|iPod/i.test(ua)) {
    const match = ua.match(/OS ([\d_]+)/);
    const version = match ? match[1].replace(/_/g, '.') : '';
    return `iOS ${version}`;
  }

  if (/Android/i.test(ua)) {
    const match = ua.match(/Android ([\d.]+)/);
    const version = match ? match[1] : '';
    return `Android ${version}`;
  }

  if (/Linux/i.test(ua)) {
    return 'Linux';
  }

  return 'Unknown';
}

/**
 * Detect browser from user agent.
 */
function detectBrowser(userAgent: string): string {
  const ua = userAgent;

  // Order matters - check more specific browsers first
  if (/Edg\//i.test(ua)) {
    const match = ua.match(/Edg\/([\d.]+)/);
    return `Edge ${match ? match[1].split('.')[0] : ''}`;
  }

  if (/Chrome/i.test(ua) && !/Chromium/i.test(ua)) {
    const match = ua.match(/Chrome\/([\d.]+)/);
    return `Chrome ${match ? match[1].split('.')[0] : ''}`;
  }

  if (/Safari/i.test(ua) && !/Chrome/i.test(ua)) {
    const match = ua.match(/Version\/([\d.]+)/);
    return `Safari ${match ? match[1].split('.')[0] : ''}`;
  }

  if (/Firefox/i.test(ua)) {
    const match = ua.match(/Firefox\/([\d.]+)/);
    return `Firefox ${match ? match[1].split('.')[0] : ''}`;
  }

  return 'Unknown';
}

/**
 * Get device information (cached).
 */
function getDeviceInfo(): DeviceInfo | null {
  if (typeof window === 'undefined') {
    return null;
  }

  if (deviceInfo) {
    return deviceInfo;
  }

  const userAgent = navigator.userAgent;

  deviceInfo = {
    deviceType: detectDeviceType(userAgent),
    os: detectOS(userAgent),
    browser: detectBrowser(userAgent),
    screenWidth: window.screen.width,
    screenHeight: window.screen.height,
  };

  return deviceInfo;
}

/**
 * Flush events to the backend.
 */
async function flushEvents(): Promise<void> {
  if (eventQueue.length === 0) {
    return;
  }

  const events = [...eventQueue];
  eventQueue = [];

  try {
    const sessionId = getSessionId();
    const payload = JSON.stringify({ events });

    // Always use fetch for reliable delivery and error handling
    await fetch(`${API_URL}/events/track`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Session-ID': sessionId,
      },
      body: payload,
    });
  } catch (error) {
    // Silently fail - put events back in queue for retry
    console.debug('[Analytics] Failed to flush events:', error);
    eventQueue.unshift(...events);
  }
}

/**
 * Schedule a flush if not already scheduled.
 */
function scheduleFlush(): void {
  if (flushTimeoutId === null) {
    flushTimeoutId = setTimeout(() => {
      flushTimeoutId = null;
      flushEvents();
    }, FLUSH_INTERVAL_MS);
  }
}

/**
 * Queue an event for sending.
 */
function queueEvent(event: UserEvent): void {
  eventQueue.push(event);

  // Flush immediately if batch is full
  if (eventQueue.length >= MAX_BATCH_SIZE) {
    flushEvents();
  } else {
    scheduleFlush();
  }
}

/**
 * Analytics hook return type.
 */
export interface UseAnalyticsReturn {
  trackEvent: (
    eventType: string,
    eventData?: Record<string, unknown>,
    options?: {
      category?: string;
      pagePath?: string;
      durationMs?: number;
      latitude?: number;
      longitude?: number;
    }
  ) => void;
  trackPageView: (pagePath: string, referrer?: string) => void;
  trackPerformance: (eventType: string, durationMs: number, context?: Record<string, unknown>) => void;
  trackMapEvent: (eventType: string, eventData?: Record<string, unknown>) => void;
  trackConversion: (eventType: string, eventData?: Record<string, unknown>) => void;
  trackAuthEvent: (eventType: string, eventData?: Record<string, unknown>, location?: { latitude: number; longitude: number }) => void;
  trackPOIFilterToggle: (filterName: string, enabled: boolean) => void;
  trackPOIClick: (poiId: string, poiName: string, poiType: string) => void;
  flush: () => Promise<void>;
}

/**
 * Hook for tracking user analytics events.
 *
 * @returns Object with tracking methods
 */
export function useAnalytics(): UseAnalyticsReturn {
  const { data: session } = useSession();
  const userId = session?.user?.id as string | undefined;

  // Set up flush on page unload
  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const handleBeforeUnload = () => {
      flushEvents();
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'hidden') {
        flushEvents();
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      document.removeEventListener('visibilitychange', handleVisibilityChange);

      // Clear scheduled flush
      if (flushTimeoutId) {
        clearTimeout(flushTimeoutId);
        flushTimeoutId = null;
      }
    };
  }, []);

  /**
   * Track a generic event.
   */
  const trackEvent = useCallback(
    (
      eventType: string,
      eventData?: Record<string, unknown>,
      options?: {
        category?: string;
        pagePath?: string;
        durationMs?: number;
        latitude?: number;
        longitude?: number;
      }
    ) => {
      const sessionId = getSessionId();
      if (!sessionId) return;

      const device = getDeviceInfo();
      const category = options?.category || getCategoryForEventType(eventType) || EventCategory.INTERACTION;

      const event: UserEvent = {
        event_type: eventType,
        event_category: category,
        session_id: sessionId,
        user_id: userId,
        event_data: eventData,
        device_type: device?.deviceType,
        os: device?.os,
        browser: device?.browser,
        screen_width: device?.screenWidth,
        screen_height: device?.screenHeight,
        page_path: options?.pagePath || (typeof window !== 'undefined' ? window.location.pathname : undefined),
        referrer: typeof document !== 'undefined' ? document.referrer : undefined,
        duration_ms: options?.durationMs,
        latitude: options?.latitude,
        longitude: options?.longitude,
      };

      queueEvent(event);
    },
    [userId]
  );

  /**
   * Track a page view.
   */
  const trackPageView = useCallback(
    (pagePath: string, referrer?: string) => {
      const sessionId = getSessionId();
      if (!sessionId) return;

      const device = getDeviceInfo();

      const event: UserEvent = {
        event_type: EventType.PAGE_VIEW,
        event_category: EventCategory.NAVIGATION,
        session_id: sessionId,
        user_id: userId,
        device_type: device?.deviceType,
        os: device?.os,
        browser: device?.browser,
        screen_width: device?.screenWidth,
        screen_height: device?.screenHeight,
        page_path: pagePath,
        referrer: referrer || (typeof document !== 'undefined' ? document.referrer : undefined),
      };

      queueEvent(event);
    },
    [userId]
  );

  /**
   * Track a performance event.
   */
  const trackPerformance = useCallback(
    (eventType: string, durationMs: number, context?: Record<string, unknown>) => {
      trackEvent(eventType, context, {
        category: EventCategory.PERFORMANCE,
        durationMs,
      });
    },
    [trackEvent]
  );

  /**
   * Track a map management event.
   */
  const trackMapEvent = useCallback(
    (eventType: string, eventData?: Record<string, unknown>) => {
      trackEvent(eventType, eventData, {
        category: EventCategory.MAP_MANAGEMENT,
      });
    },
    [trackEvent]
  );

  /**
   * Track a conversion funnel event.
   */
  const trackConversion = useCallback(
    (eventType: string, eventData?: Record<string, unknown>) => {
      trackEvent(eventType, eventData, {
        category: EventCategory.CONVERSION,
      });
    },
    [trackEvent]
  );

  /**
   * Track an authentication event.
   */
  const trackAuthEvent = useCallback(
    (eventType: string, eventData?: Record<string, unknown>, location?: { latitude: number; longitude: number }) => {
      trackEvent(eventType, eventData, {
        category: EventCategory.AUTH,
        latitude: location?.latitude,
        longitude: location?.longitude,
      });
    },
    [trackEvent]
  );

  /**
   * Track POI filter toggle.
   */
  const trackPOIFilterToggle = useCallback(
    (filterName: string, enabled: boolean) => {
      trackEvent(EventType.POI_FILTER_TOGGLE, { filter_name: filterName, enabled }, {
        category: EventCategory.PREFERENCES,
      });
    },
    [trackEvent]
  );

  /**
   * Track POI click.
   */
  const trackPOIClick = useCallback(
    (poiId: string, poiName: string, poiType: string) => {
      trackEvent(EventType.POI_CLICK, { poi_id: poiId, poi_name: poiName, poi_type: poiType }, {
        category: EventCategory.INTERACTION,
      });
    },
    [trackEvent]
  );

  /**
   * Force flush all queued events.
   */
  const flush = useCallback(async () => {
    await flushEvents();
  }, []);

  return {
    trackEvent,
    trackPageView,
    trackPerformance,
    trackMapEvent,
    trackConversion,
    trackAuthEvent,
    trackPOIFilterToggle,
    trackPOIClick,
    flush,
  };
}

/**
 * Standalone function to track an event (for use outside of React components).
 */
export function trackAnalyticsEvent(
  eventType: string,
  eventData?: Record<string, unknown>,
  options?: {
    userId?: string;
    category?: string;
    pagePath?: string;
    durationMs?: number;
  }
): void {
  const sessionId = getSessionId();
  if (!sessionId) return;

  const device = getDeviceInfo();
  const category = options?.category || getCategoryForEventType(eventType) || EventCategory.INTERACTION;

  const event: UserEvent = {
    event_type: eventType,
    event_category: category,
    session_id: sessionId,
    user_id: options?.userId,
    event_data: eventData,
    device_type: device?.deviceType,
    os: device?.os,
    browser: device?.browser,
    screen_width: device?.screenWidth,
    screen_height: device?.screenHeight,
    page_path: options?.pagePath || (typeof window !== 'undefined' ? window.location.pathname : undefined),
    referrer: typeof document !== 'undefined' ? document.referrer : undefined,
    duration_ms: options?.durationMs,
  };

  queueEvent(event);
}
