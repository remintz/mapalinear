import { useState, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { RouteSearchRequest, RouteSearchResponse } from '@/lib/types';
import { SearchFormData } from '@/lib/validations';

interface UseRouteSearchReturn {
  searchRoute: (data: SearchFormData) => void;
  isLoading: boolean;
  error: string | null;
  data: RouteSearchResponse | null;
  reset: () => void;
  progressMessage: string;
}

export function useRouteSearch(): UseRouteSearchReturn {
  const [error, setError] = useState<string | null>(null);
  const [progressMessage, setProgressMessage] = useState<string>('Criar Mapa');

  const mutation = useMutation({
    mutationFn: async (formData: SearchFormData): Promise<RouteSearchResponse> => {
      // Convert form data to API request format
      const requestData: RouteSearchRequest = {
        origin: formData.origin,
        destination: formData.destination,
        include_gas_stations: formData.includeGasStations,
        include_restaurants: formData.includeRestaurants,
        include_toll_booths: formData.includeTollBooths,
        max_distance: formData.maxDistance,
      };

      return await apiClient.searchRoute(requestData);
    },
    onSuccess: () => {
      setError(null);
      setProgressMessage('Criar Mapa');
    },
    onError: (error: Error) => {
      setError(error.message || 'Erro ao buscar rota. Tente novamente.');
      setProgressMessage('Criar Mapa');
    },
  });

  // Progress messages during loading
  useEffect(() => {
    if (mutation.isPending) {
      setProgressMessage('Conectando ao servidor...');
      
      const timer1 = setTimeout(() => {
        if (mutation.isPending) {
          setProgressMessage('Consultando OpenStreetMap...');
        }
      }, 2000);

      const timer2 = setTimeout(() => {
        if (mutation.isPending) {
          setProgressMessage('Processando rota...');
        }
      }, 8000);

      const timer3 = setTimeout(() => {
        if (mutation.isPending) {
          setProgressMessage('Finalizando busca...');
        }
      }, 15000);

      const timer4 = setTimeout(() => {
        if (mutation.isPending) {
          setProgressMessage('Quase lá... (consulta complexa)');
        }
      }, 30000);

      return () => {
        clearTimeout(timer1);
        clearTimeout(timer2);
        clearTimeout(timer3);
        clearTimeout(timer4);
      };
    }
  }, [mutation.isPending]);

  const searchRoute = (data: SearchFormData) => {
    setError(null);
    setProgressMessage('Iniciando busca...');
    mutation.mutate(data);
  };

  const reset = () => {
    setError(null);
    setProgressMessage('Criar Mapa');
    mutation.reset();
  };

  return {
    searchRoute,
    isLoading: mutation.isPending,
    error: error || (mutation.isError ? 'Erro ao buscar rota. Tente novamente.' : null),
    data: mutation.data || null,
    reset,
    progressMessage,
  };
}