'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient, ProblemType } from '@/lib/api';

export interface UseProblemTypesResult {
  problemTypes: ProblemType[];
  isLoading: boolean;
  error: Error | null;
}

/**
 * Hook to fetch active problem types for the report form.
 */
export function useProblemTypes(): UseProblemTypesResult {
  const { data, isLoading, error } = useQuery({
    queryKey: ['problemTypes'],
    queryFn: () => apiClient.getProblemTypes(),
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 30, // 30 minutes cache
    refetchOnWindowFocus: false,
  });

  return {
    problemTypes: data ?? [],
    isLoading,
    error: error as Error | null,
  };
}
