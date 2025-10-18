import { useState, useCallback, useRef } from 'react';
import { apiClient } from '@/lib/api';
import { RouteSearchRequest, RouteSearchResponse, AsyncOperation, POIType } from '@/lib/types';
import { SearchFormData } from '@/lib/validations';

interface UseAsyncRouteSearchReturn {
  searchRoute: (data: SearchFormData) => void;
  isLoading: boolean;
  error: string | null;
  data: RouteSearchResponse | null;
  reset: () => void;
  progressMessage: string;
  progressPercent: number;
  estimatedCompletion: string | null;
}

export function useAsyncRouteSearch(): UseAsyncRouteSearchReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<RouteSearchResponse | null>(null);
  const [progressMessage, setProgressMessage] = useState<string>('Buscar Rota');
  const [progressPercent, setProgressPercent] = useState<number>(0);
  const [estimatedCompletion, setEstimatedCompletion] = useState<string | null>(null);
  
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const currentOperationIdRef = useRef<string | null>(null);

  const clearPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  }, []);

  const pollOperationStatus = useCallback(async (operationId: string) => {
    try {
      const operation = await apiClient.getOperationStatus(operationId);
      
      // Update progress
      setProgressPercent(operation.progress_percent);
      setEstimatedCompletion(operation.estimated_completion || null);
      
      // Update progress message based on percentage and type
      if (operation.progress_percent <= 10) {
        setProgressMessage('Iniciando busca...');
      } else if (operation.progress_percent <= 30) {
        setProgressMessage('Consultando OpenStreetMap...');
      } else if (operation.progress_percent <= 60) {
        setProgressMessage('Processando rota...');
      } else if (operation.progress_percent <= 90) {
        setProgressMessage('Buscando pontos de interesse...');
      } else {
        setProgressMessage('Finalizando...');
      }

      // Handle completion
      if (operation.status === 'completed') {
        clearPolling();
        setIsLoading(false);
        setProgressMessage('Buscar Rota');
        setProgressPercent(100);
        
        if (operation.result) {
          // Debug log to see what data we're receiving
          console.log('Dados recebidos da API:', operation.result);
          
          // Debug milestone types distribution
          if (operation.result.milestones) {
            const typeCount = operation.result.milestones.reduce((acc: any, m: any) => {
              acc[m.type] = (acc[m.type] || 0) + 1;
              return acc;
            }, {});
            console.log('Distribuição de tipos de milestones:', typeCount);
          }
          
          // Validate and sanitize the result data
          // Map API response fields to expected frontend fields
          
          // Filter milestones to get only POIs (gas stations, restaurants, toll booths)
          const poiTypes = ['gas_station', 'restaurant', 'toll_booth'];
          const filteredMilestones = operation.result.milestones?.filter((milestone: any) => 
            poiTypes.includes(milestone.type)
          ) || [];
          
          // Convert milestones to POI format
          const pois = filteredMilestones.map((milestone: any) => ({
            id: milestone.id,
            name: milestone.name,
            type: milestone.type as POIType, // Map to POIType enum
            coordinates: milestone.coordinates,
            distance_from_origin_km: milestone.distance_from_origin_km,
            tags: milestone.tags || {},
            operator: milestone.operator,
            brand: milestone.brand,
            opening_hours: milestone.opening_hours,
            quality_score: milestone.quality_score
          }));
          
          const sanitizedResult = {
            ...operation.result,
            // API returns total_length_km, not total_distance_km
            total_distance_km: operation.result.total_length_km || 0,
            // Extract relevant POIs from milestones  
            pois: pois,
            segments: operation.result.segments || [],
            origin: operation.result.origin || 'Origem não especificada',
            destination: operation.result.destination || 'Destino não especificado',
            // Keep all milestones for future use
            milestones: operation.result.milestones || []
          };
          
          console.log('Dados sanitizados:', sanitizedResult);
          
          setData(sanitizedResult);
          setError(null);
        } else {
          setError('Resultado não encontrado.');
        }
      } else if (operation.status === 'failed') {
        clearPolling();
        setIsLoading(false);
        setProgressMessage('Buscar Rota');
        setProgressPercent(0);
        setError(operation.error || 'Erro na busca da rota.');
      }
      // If still in_progress, continue polling
      
    } catch (err) {
      console.error('Error polling operation status:', err);
      // Don't stop polling on individual poll errors, just log them
    }
  }, [clearPolling]);

  const startPolling = useCallback((operationId: string) => {
    currentOperationIdRef.current = operationId;
    
    // Poll immediately, then every 2 seconds
    pollOperationStatus(operationId);
    
    pollingIntervalRef.current = setInterval(() => {
      pollOperationStatus(operationId);
    }, 2000);
  }, [pollOperationStatus]);

  const searchRoute = useCallback(async (formData: SearchFormData) => {
    try {
      setIsLoading(true);
      setError(null);
      setData(null);
      setProgressPercent(0);
      setProgressMessage('Iniciando busca...');
      setEstimatedCompletion(null);
      
      // Convert form data to API request format
      const requestData: RouteSearchRequest = {
        origin: formData.origin,
        destination: formData.destination,
        include_gas_stations: formData.includeGasStations,
        include_food: formData.includeRestaurants,
        include_toll_booths: formData.includeTollBooths,
        max_distance: formData.maxDistance,
      };

      // Start async operation
      const { operation_id } = await apiClient.startAsyncRouteSearch(requestData);
      
      // Start polling for progress
      startPolling(operation_id);
      
    } catch (err) {
      setIsLoading(false);
      setProgressMessage('Buscar Rota');
      setProgressPercent(0);
      
      const errorMessage = err instanceof Error ? err.message : 'Erro ao iniciar busca da rota.';
      setError(errorMessage);
    }
  }, [startPolling]);

  const reset = useCallback(() => {
    clearPolling();
    currentOperationIdRef.current = null;
    setIsLoading(false);
    setError(null);
    setData(null);
    setProgressMessage('Buscar Rota');
    setProgressPercent(0);
    setEstimatedCompletion(null);
  }, [clearPolling]);

  return {
    searchRoute,
    isLoading,
    error,
    data,
    reset,
    progressMessage,
    progressPercent,
    estimatedCompletion,
  };
}