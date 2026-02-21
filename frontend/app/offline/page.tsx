'use client';

import React from 'react';
import { WifiOff, Map } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { useRouter } from 'next/navigation';

export default function OfflinePage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="text-center max-w-md w-full">
        <div className="bg-amber-100 rounded-full w-20 h-20 flex items-center justify-center mx-auto mb-6">
          <WifiOff className="h-10 w-10 text-amber-600" />
        </div>
        <h1 className="text-xl font-bold text-gray-900 mb-2">Sem conexão</h1>
        <p className="text-sm text-gray-600 mb-6">
          Esta funcionalidade requer conexão com a internet.
          Seus mapas salvos estão disponíveis offline.
        </p>
        <Button onClick={() => router.push('/maps')}>
          <Map className="h-4 w-4 mr-2" />
          Meus Mapas
        </Button>
      </div>
    </div>
  );
}
