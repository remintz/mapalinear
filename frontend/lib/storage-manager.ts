import { getAllCachedMapsMeta, deleteMapOffline, getCacheStats } from './offline-storage';

const MAX_CACHED_MAPS = 20;
const WARNING_SIZE_BYTES = 40 * 1024 * 1024; // 40MB

export async function requestPersistentStorage(): Promise<boolean> {
  if (typeof navigator === 'undefined') return false;

  if (navigator.storage && navigator.storage.persist) {
    return navigator.storage.persist();
  }
  return false;
}

export async function ensureStorageQuota(): Promise<{
  ok: boolean;
  warning?: string;
}> {
  const stats = await getCacheStats();

  if (stats.totalSizeBytes > WARNING_SIZE_BYTES) {
    return {
      ok: true,
      warning: `Cache usando ${(stats.totalSizeBytes / 1024 / 1024).toFixed(1)}MB. Considere remover mapas antigos.`,
    };
  }

  if (stats.mapCount >= MAX_CACHED_MAPS) {
    // Evict oldest map (LRU)
    const metas = await getAllCachedMapsMeta();
    if (metas.length > 0) {
      const oldest = metas[metas.length - 1];
      await deleteMapOffline(oldest.id);
    }
    return {
      ok: true,
      warning: `Limite de ${MAX_CACHED_MAPS} mapas atingido. O mapa mais antigo foi removido.`,
    };
  }

  return { ok: true };
}
