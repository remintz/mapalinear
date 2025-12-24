'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient, Municipality } from '@/lib/api';

export interface UseMunicipalitiesResult {
  municipalities: Municipality[];
  isLoading: boolean;
  error: Error | null;
  /** Filter municipalities by search term (nome or uf) */
  filter: (search: string) => Municipality[];
}

/**
 * Normalize text for search: remove accents and convert to lowercase.
 */
function normalizeText(text: string): string {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');
}

/**
 * Hook to fetch and cache Brazilian municipalities from IBGE.
 * Data is fetched once and cached for the session.
 */
export function useMunicipalities(): UseMunicipalitiesResult {
  const { data, isLoading, error } = useQuery({
    queryKey: ['municipalities'],
    queryFn: () => apiClient.getMunicipalities(),
    staleTime: 1000 * 60 * 60, // 1 hour - data is very stable
    gcTime: 1000 * 60 * 60 * 24, // 24 hours cache
    refetchOnWindowFocus: false,
    refetchOnMount: false,
  });

  const municipalities = data ?? [];

  /**
   * Filter municipalities by search term.
   * Matches against city name and state code.
   * Search is accent-insensitive and case-insensitive.
   * Results are sorted by relevance: cities starting with the term first.
   */
  const filter = (search: string): Municipality[] => {
    if (!search || search.length < 2) {
      return [];
    }

    const searchNormalized = normalizeText(search.trim());

    // Check if search includes comma (e.g., "São Paulo, SP" or "sao paulo, sp")
    const parts = searchNormalized.split(',').map(p => p.trim());
    const citySearch = parts[0];
    const ufSearch = parts[1]?.toUpperCase();

    return municipalities
      .filter((m) => {
        const nameNormalized = normalizeText(m.nome);
        const nameMatch = nameNormalized.includes(citySearch);
        const ufMatch = !ufSearch || m.uf === ufSearch;
        return nameMatch && ufMatch;
      })
      .sort((a, b) => {
        const aName = normalizeText(a.nome);
        const bName = normalizeText(b.nome);
        const aStartsWith = aName.startsWith(citySearch);
        const bStartsWith = bName.startsWith(citySearch);

        // Cities starting with the term come first
        if (aStartsWith && !bStartsWith) return -1;
        if (!aStartsWith && bStartsWith) return 1;

        // Then sort alphabetically
        return aName.localeCompare(bName);
      })
      .slice(0, 50); // Limit results for performance
  };

  return {
    municipalities,
    isLoading,
    error: error as Error | null,
    filter,
  };
}
