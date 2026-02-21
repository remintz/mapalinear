'use client';

import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/lib/api';
import {
  saveMapOffline,
  getMapOffline,
  type CachedMap,
} from '@/lib/offline-storage';
import { ensureStorageQuota } from '@/lib/storage-manager';
import { useOfflineContext } from '@/components/providers/OfflineProvider';
import type { RouteSegment, Milestone } from '@/lib/types';

interface MapData {
  origin: string;
  destination: string;
  total_distance_km: number;
  segments: RouteSegment[];
  milestones: Milestone[];
}

interface UseOfflineMapResult {
  data: MapData | null;
  isLoading: boolean;
  error: string | null;
}

export function useOfflineMap(mapId: string | null): UseOfflineMapResult {
  const [data, setData] = useState<MapData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { isOnline, refreshCachedMapIds } = useOfflineContext();

  const loadFromCache = useCallback(async (id: string): Promise<CachedMap | undefined> => {
    try {
      return await getMapOffline(id);
    } catch {
      return undefined;
    }
  }, []);

  const saveToCache = useCallback(async (id: string, mapData: MapData, creationDate?: string) => {
    try {
      await ensureStorageQuota();
      await saveMapOffline(id, { ...mapData, creation_date: creationDate });
    } catch (err) {
      console.warn('Failed to save map to offline cache:', err);
    }
  }, []);

  useEffect(() => {
    if (!mapId) {
      setIsLoading(false);
      setData(null);
      return;
    }

    let cancelled = false;

    async function loadMap() {
      setIsLoading(true);
      setError(null);

      if (isOnline) {
        // Online: fetch from API, save to cache
        try {
          const savedMap = await apiClient.getMap(mapId!);
          if (cancelled) return;

          const mapData: MapData = {
            origin: savedMap.origin,
            destination: savedMap.destination,
            total_distance_km: savedMap.total_length_km || 0,
            segments: (savedMap.segments || []) as RouteSegment[],
            milestones: savedMap.milestones || [],
          };

          setData(mapData);
          setIsLoading(false);
          saveToCache(mapId!, mapData, savedMap.creation_date)
            .then(() => refreshCachedMapIds());
        } catch {
          if (cancelled) return;
          // API failed even though navigator says online - try cache
          const cached = await loadFromCache(mapId!);
          if (cancelled) return;
          if (cached) {
            setData({
              origin: cached.origin,
              destination: cached.destination,
              total_distance_km: cached.total_distance_km,
              segments: cached.segments,
              milestones: cached.milestones,
            });
          } else {
            setError('Erro ao carregar mapa');
          }
          setIsLoading(false);
        }
      } else {
        // Offline: load from IndexedDB
        const cached = await loadFromCache(mapId!);
        if (cancelled) return;
        if (cached) {
          setData({
            origin: cached.origin,
            destination: cached.destination,
            total_distance_km: cached.total_distance_km,
            segments: cached.segments,
            milestones: cached.milestones,
          });
        } else {
          setError('Mapa não disponível offline');
        }
        setIsLoading(false);
      }
    }

    loadMap();

    return () => { cancelled = true; };
  }, [mapId, isOnline, loadFromCache, saveToCache, refreshCachedMapIds]);

  return { data, isLoading, error };
}
