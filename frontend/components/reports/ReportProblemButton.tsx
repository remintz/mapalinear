'use client';

import { useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import { ReportProblemModal } from './ReportProblemModal';

interface POI {
  id: string;
  name: string;
  type: string;
  distance_from_origin_km?: number;
}

interface ReportProblemButtonProps {
  mapId?: string;
  pois: POI[];
  userLocation?: { lat: number; lon: number };
}

export function ReportProblemButton({ mapId, pois, userLocation }: ReportProblemButtonProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setIsModalOpen(true)}
        className="fixed bottom-4 left-4 z-40
                   flex items-center gap-2 px-4 py-2
                   bg-amber-500 text-white rounded-full shadow-lg
                   hover:bg-amber-600 active:bg-amber-700
                   transition-colors"
      >
        <AlertTriangle className="w-5 h-5" />
        <span className="text-sm font-medium">Reportar Problema</span>
      </button>

      <ReportProblemModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        mapId={mapId}
        pois={pois}
        userLocation={userLocation}
      />
    </>
  );
}
