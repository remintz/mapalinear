'use client';

import React from 'react';
import { WifiOff } from 'lucide-react';
import { useOfflineContext } from '@/components/providers/OfflineProvider';

export function OfflineBanner() {
  const { isOnline } = useOfflineContext();

  if (isOnline) return null;

  return (
    <div className="bg-amber-500 text-white text-sm py-2 px-4 flex items-center justify-center gap-2 z-50">
      <WifiOff className="h-4 w-4" />
      <span>Modo offline - usando dados salvos</span>
    </div>
  );
}
