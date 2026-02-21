import { openDB, type DBSchema, type IDBPDatabase } from 'idb';
import type { RouteSegment, Milestone } from './types';

const DB_NAME = 'orapois-offline';
const DB_VERSION = 1;

export interface CachedMap {
  id: string;
  origin: string;
  destination: string;
  total_distance_km: number;
  segments: RouteSegment[];
  milestones: Milestone[];
  cachedAt: number;
  version: number;
  sizeBytes?: number;
}

export interface CachedMapMeta {
  id: string;
  origin: string;
  destination: string;
  total_length_km: number;
  milestone_count: number;
  creation_date: string;
  cachedAt: number;
}

interface OfflineDB extends DBSchema {
  maps: {
    key: string;
    value: CachedMap;
  };
  mapsMeta: {
    key: string;
    value: CachedMapMeta;
    indexes: { 'by-cachedAt': number };
  };
}

let dbPromise: Promise<IDBPDatabase<OfflineDB>> | null = null;

function getDB(): Promise<IDBPDatabase<OfflineDB>> {
  if (!dbPromise) {
    dbPromise = openDB<OfflineDB>(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains('maps')) {
          db.createObjectStore('maps', { keyPath: 'id' });
        }
        if (!db.objectStoreNames.contains('mapsMeta')) {
          const metaStore = db.createObjectStore('mapsMeta', { keyPath: 'id' });
          metaStore.createIndex('by-cachedAt', 'cachedAt');
        }
      },
    });
  }
  return dbPromise;
}

export async function saveMapOffline(
  mapId: string,
  data: {
    origin: string;
    destination: string;
    total_distance_km: number;
    segments: RouteSegment[];
    milestones: Milestone[];
    creation_date?: string;
  }
): Promise<void> {
  const db = await getDB();
  const now = Date.now();

  const serialized = JSON.stringify(data);
  const sizeBytes = new Blob([serialized]).size;

  const cachedMap: CachedMap = {
    id: mapId,
    origin: data.origin,
    destination: data.destination,
    total_distance_km: data.total_distance_km,
    segments: data.segments,
    milestones: data.milestones,
    cachedAt: now,
    version: DB_VERSION,
    sizeBytes,
  };

  const cachedMeta: CachedMapMeta = {
    id: mapId,
    origin: data.origin,
    destination: data.destination,
    total_length_km: data.total_distance_km,
    milestone_count: data.milestones.length,
    creation_date: data.creation_date || new Date().toISOString(),
    cachedAt: now,
  };

  const tx = db.transaction(['maps', 'mapsMeta'], 'readwrite');
  await Promise.all([
    tx.objectStore('maps').put(cachedMap),
    tx.objectStore('mapsMeta').put(cachedMeta),
    tx.done,
  ]);
}

export async function getMapOffline(mapId: string): Promise<CachedMap | undefined> {
  const db = await getDB();
  return db.get('maps', mapId);
}

export async function deleteMapOffline(mapId: string): Promise<void> {
  const db = await getDB();
  const tx = db.transaction(['maps', 'mapsMeta'], 'readwrite');
  await Promise.all([
    tx.objectStore('maps').delete(mapId),
    tx.objectStore('mapsMeta').delete(mapId),
    tx.done,
  ]);
}

export async function getAllCachedMapsMeta(): Promise<CachedMapMeta[]> {
  const db = await getDB();
  const all = await db.getAll('mapsMeta');
  // Sort by cachedAt descending (most recent first)
  return all.sort((a, b) => b.cachedAt - a.cachedAt);
}

export async function getCachedMapIds(): Promise<string[]> {
  const db = await getDB();
  return db.getAllKeys('mapsMeta') as Promise<string[]>;
}

export async function getCacheStats(): Promise<{
  mapCount: number;
  totalSizeBytes: number;
}> {
  const db = await getDB();
  const maps = await db.getAll('maps');
  const totalSizeBytes = maps.reduce((sum, m) => sum + (m.sizeBytes || 0), 0);
  return { mapCount: maps.length, totalSizeBytes };
}
