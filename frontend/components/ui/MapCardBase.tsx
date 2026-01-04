'use client';

import React, { ReactNode } from 'react';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/badge';
import { Calendar, MapPin } from 'lucide-react';
import { SavedMap } from '@/lib/api';

interface MapCardBaseProps {
  map: SavedMap;
  children: ReactNode; // Action buttons
}

const formatDate = (dateString: string) => {
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return 'Data inválida';
    return new Intl.DateTimeFormat('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  } catch {
    return 'Data inválida';
  }
};

export function MapCardBase({ map, children }: MapCardBaseProps) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-4">
        {/* Route Info */}
        <div className="mb-3">
          <h3 className="text-base font-semibold text-gray-900 mb-1 min-h-[3rem] line-clamp-2">
            {map.origin} → {map.destination}
          </h3>
          <div className="flex flex-wrap items-center gap-2 text-xs text-gray-600">
            <span className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              {formatDate(map.creation_date)}
            </span>
            <span className="flex items-center gap-1">
              <MapPin className="h-3 w-3" />
              {map.milestone_count} pontos
            </span>
            <Badge variant="secondary" className="bg-blue-100 text-blue-800 text-xs">
              {map.total_length_km.toFixed(1)} km
            </Badge>
          </div>
        </div>

        {/* Action Buttons (passed as children) */}
        <div className="flex gap-2">
          {children}
        </div>
      </CardContent>
    </Card>
  );
}
