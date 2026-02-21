'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { getCachedMapIds } from '@/lib/offline-storage';
import { requestPersistentStorage } from '@/lib/storage-manager';

interface OfflineContextValue {
  isOnline: boolean;
  cachedMapIds: string[];
  refreshCachedMapIds: () => Promise<void>;
}

const OfflineContext = createContext<OfflineContextValue>({
  isOnline: true,
  cachedMapIds: [],
  refreshCachedMapIds: async () => {},
});

export function useOfflineContext() {
  return useContext(OfflineContext);
}

export function OfflineProvider({ children }: { children: React.ReactNode }) {
  const [isOnline, setIsOnline] = useState(() =>
    typeof navigator !== 'undefined' ? navigator.onLine : true
  );
  const [cachedMapIds, setCachedMapIds] = useState<string[]>([]);

  useEffect(() => {
    const goOnline = () => setIsOnline(true);
    const goOffline = () => setIsOnline(false);
    window.addEventListener('online', goOnline);
    window.addEventListener('offline', goOffline);
    // Re-sync: navigator.onLine may change between initial render and effect
    setIsOnline(navigator.onLine);
    return () => {
      window.removeEventListener('online', goOnline);
      window.removeEventListener('offline', goOffline);
    };
  }, []);

  const refreshCachedMapIds = useCallback(async () => {
    try {
      const ids = await getCachedMapIds();
      setCachedMapIds(ids);
    } catch {
      // IndexedDB may not be available
    }
  }, []);

  useEffect(() => {
    refreshCachedMapIds();
    requestPersistentStorage();
  }, [refreshCachedMapIds]);

  return (
    <OfflineContext.Provider value={{ isOnline, cachedMapIds, refreshCachedMapIds }}>
      {children}
    </OfflineContext.Provider>
  );
}
