"use client";

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { 
  Download, 
  ExternalLink, 
  MapPin, 
  Route, 
  Fuel, 
  UtensilsCrossed, 
  Coins,
  Building2,
  Clock,
  Navigation
} from 'lucide-react';
import { toast } from 'sonner';

interface POI {
  id: string;
  name: string;
  type: string;
  coordinates: {
    lat: number;
    lon: number;
  };
  distance_from_origin_km: number;
  brand?: string;
  operator?: string;
  opening_hours?: string;
  quality_score?: number;
}

interface RouteSegment {
  id: string;
  name: string;
  geometry: Array<{
    lat: number;
    lon: number;
  }>;
  length_km: number;
}

interface RouteResultsProps {
  origin: string;
  destination: string;
  totalDistance: number;
  segments: RouteSegment[];
  pois: POI[];
}

const POI_ICONS = {
  gas_station: Fuel,
  restaurant: UtensilsCrossed,
  toll_booth: Coins,
  city: Building2,
  town: Building2,
  village: Building2,
} as const;

const POI_COLORS = {
  gas_station: "bg-red-100 text-red-800 border-red-200",
  restaurant: "bg-green-100 text-green-800 border-green-200", 
  toll_booth: "bg-yellow-100 text-yellow-800 border-yellow-200",
  city: "bg-purple-100 text-purple-800 border-purple-200",
  town: "bg-purple-100 text-purple-800 border-purple-200",
  village: "bg-purple-100 text-purple-800 border-purple-200",
} as const;

export function RouteResults({ origin, destination, totalDistance, segments, pois }: RouteResultsProps) {
  const [isExporting, setIsExporting] = useState(false);

  // Agrupar POIs por tipo
  const poiCounts = pois.reduce((acc, poi) => {
    acc[poi.type] = (acc[poi.type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  // Função para download de arquivos
  const downloadFile = async (format: 'geojson' | 'gpx') => {
    setIsExporting(true);
    try {
      const routeData = {
        origin,
        destination,
        total_distance_km: totalDistance,
        segments,
        pois
      };

      const response = await fetch(`/api/export/${format}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(routeData),
      });

      if (!response.ok) {
        throw new Error(`Erro ao exportar ${format.toUpperCase()}`);
      }

      // Criar blob e download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = response.headers.get('Content-Disposition')?.split('filename=')[1] || `rota.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast.success(`Arquivo ${format.toUpperCase()} baixado com sucesso!`);
    } catch (error) {
      console.error('Erro ao exportar:', error);
      toast.error(`Erro ao exportar ${format.toUpperCase()}: ${error instanceof Error ? error.message : 'Erro desconhecido'}`);
    } finally {
      setIsExporting(false);
    }
  };

  // Função para abrir URLs de ferramentas web
  const openWebTool = async (tool: 'umap' | 'overpass') => {
    try {
      const routeData = {
        origin,
        destination,
        total_distance_km: totalDistance,
        segments,
        pois
      };

      const response = await fetch('/api/export/web-urls', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(routeData),
      });

      if (!response.ok) {
        throw new Error('Erro ao gerar URLs');
      }

      const data = await response.json();
      const url = tool === 'umap' ? data.umap_url : data.overpass_turbo_url;
      
      window.open(url, '_blank');
      
      if (tool === 'umap') {
        toast.info('uMap aberto! Clique em "Importar dados" e carregue o arquivo GeoJSON baixado');
      } else {
        toast.info('Overpass Turbo aberto! Veja os POIs existentes na região da rota');
      }
    } catch (error) {
      console.error('Erro ao abrir ferramenta web:', error);
      toast.error('Erro ao abrir ferramenta web');
    }
  };

  return (
    <div className="space-y-6">
      {/* Resumo da Rota */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Route className="h-5 w-5 text-blue-600" />
            <CardTitle>Rota Encontrada</CardTitle>
          </div>
          <CardDescription>
            {origin} → {destination}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{totalDistance.toFixed(1)}</div>
              <div className="text-sm text-gray-600">km</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{segments.length}</div>
              <div className="text-sm text-gray-600">segmentos</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">{pois.length}</div>
              <div className="text-sm text-gray-600">POIs</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">{Object.keys(poiCounts).length}</div>
              <div className="text-sm text-gray-600">tipos</div>
            </div>
          </div>

          {/* Breakdown de POIs */}
          <div className="flex flex-wrap gap-2 mb-6">
            {Object.entries(poiCounts).map(([type, count]) => (
              <Badge 
                key={type} 
                variant="secondary" 
                className={POI_COLORS[type as keyof typeof POI_COLORS] || "bg-gray-100 text-gray-800"}
              >
                {count} {type.replace('_', ' ')}
              </Badge>
            ))}
          </div>

          <Separator className="my-6" />

          {/* Botões de Exportação */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Download className="h-5 w-5" />
              Exportar e Visualizar
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Downloads */}
              <div className="space-y-2">
                <h4 className="font-medium text-gray-700">Baixar Arquivos</h4>
                <div className="space-y-2">
                  <Button 
                    onClick={() => downloadFile('geojson')}
                    disabled={isExporting}
                    className="w-full justify-start"
                    variant="outline"
                  >
                    <Download className="h-4 w-4 mr-2" />
                    GeoJSON (para uMap, QGIS)
                  </Button>
                  <Button 
                    onClick={() => downloadFile('gpx')}
                    disabled={isExporting}
                    className="w-full justify-start"
                    variant="outline"
                  >
                    <Navigation className="h-4 w-4 mr-2" />
                    GPX (para GPS, apps móveis)
                  </Button>
                </div>
              </div>

              {/* Ferramentas Web */}
              <div className="space-y-2">
                <h4 className="font-medium text-gray-700">Abrir em Ferramentas Web</h4>
                <div className="space-y-2">
                  <Button 
                    onClick={() => openWebTool('umap')}
                    className="w-full justify-start"
                    variant="outline"
                  >
                    <ExternalLink className="h-4 w-4 mr-2" />
                    Visualizar no uMap
                  </Button>
                  <Button 
                    onClick={() => openWebTool('overpass')}
                    className="w-full justify-start"
                    variant="outline"
                  >
                    <ExternalLink className="h-4 w-4 mr-2" />
                    Validar no Overpass Turbo
                  </Button>
                </div>
              </div>
            </div>

            <div className="bg-blue-50 p-4 rounded-lg">
              <h4 className="font-medium text-blue-800 mb-2">Como Visualizar:</h4>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• <strong>uMap:</strong> Baixe o GeoJSON → Abra uMap → "Importar dados"</li>
                <li>• <strong>GPX:</strong> Arraste o arquivo para map.project-osrm.org</li>
                <li>• <strong>Overpass:</strong> Compare os POIs encontrados com os dados reais do OSM</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Lista de POIs */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <MapPin className="h-5 w-5 text-green-600" />
            <CardTitle>Pontos de Interesse</CardTitle>
          </div>
          <CardDescription>
            {pois.length} POIs encontrados ao longo da rota
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {pois.map((poi) => {
              const Icon = POI_ICONS[poi.type as keyof typeof POI_ICONS] || MapPin;
              return (
                <div key={poi.id} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                  <Icon className="h-5 w-5 mt-0.5 text-gray-600" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="font-medium truncate">{poi.name}</h4>
                      <Badge
                        variant="secondary"
                        className={`text-xs ${POI_COLORS[poi.type as keyof typeof POI_COLORS] || "bg-gray-100 text-gray-800"}`}
                      >
                        {poi.type.replace('_', ' ')}
                      </Badge>
                      {poi.quality_score !== undefined && (
                        <Badge
                          variant="outline"
                          className={`text-xs ${
                            poi.quality_score >= 0.7 ? 'bg-green-50 text-green-700 border-green-300' :
                            poi.quality_score >= 0.4 ? 'bg-yellow-50 text-yellow-700 border-yellow-300' :
                            'bg-red-50 text-red-700 border-red-300'
                          }`}
                        >
                          Q: {(poi.quality_score * 100).toFixed(0)}%
                        </Badge>
                      )}
                    </div>
                    <div className="text-sm text-gray-600">
                      {poi.distance_from_origin_km.toFixed(1)}km do início
                    </div>
                    {poi.brand && (
                      <div className="text-xs text-gray-500">{poi.brand}</div>
                    )}
                    {poi.opening_hours && (
                      <div className="text-xs text-gray-500 flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {poi.opening_hours}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}