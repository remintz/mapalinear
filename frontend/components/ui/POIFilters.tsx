import React, { useState } from 'react';
import { Badge } from './badge';
import { ChevronDown, ChevronUp } from 'lucide-react';

interface FilterOption {
  id: string;
  label: string;
  emoji: string;
  count: number;
}

interface POIFiltersProps {
  filters: FilterOption[];
  activeFilters: Set<string>;
  onFilterToggle: (filterId: string) => void;
}

export function POIFilters({ filters, activeFilters, onFilterToggle }: POIFiltersProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  // Calculate total POIs from active filters
  const totalActivePOIs = filters
    .filter(f => activeFilters.has(f.id))
    .reduce((sum, f) => sum + f.count, 0);

  return (
    <div className="sticky top-0 z-10 bg-white border-b border-gray-200 pb-3 mb-4">
      {/* Header with expand/collapse button */}
      <div className="flex items-center justify-between mb-2">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900"
        >
          <span>Filtros</span>
          <span className="text-xs text-gray-500">
            ({activeFilters.size} de {filters.length})
          </span>
          {isExpanded ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </button>

        {activeFilters.size > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-600">
              {totalActivePOIs} POIs
            </span>
            <button
              onClick={() => filters.forEach(f => activeFilters.has(f.id) && onFilterToggle(f.id))}
              className="text-xs text-blue-600 hover:text-blue-800 font-medium"
            >
              Limpar
            </button>
          </div>
        )}
      </div>

      {/* Filter chips - only show when expanded */}
      {isExpanded && (
        <div className="flex flex-wrap gap-2">
          {filters.map((filter) => {
            const isActive = activeFilters.has(filter.id);

            return (
              <button
                key={filter.id}
                onClick={() => onFilterToggle(filter.id)}
                className={`
                  inline-flex items-center gap-1.5 px-3 py-2 rounded-full text-sm font-medium
                  transition-all duration-200 active:scale-95
                  ${isActive
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }
                `}
              >
                <span role="img" aria-label={filter.label}>
                  {filter.emoji}
                </span>
                <span>{filter.label}</span>
                <Badge
                  variant={isActive ? 'secondary' : 'default'}
                  className={`ml-1 ${isActive ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-700'}`}
                >
                  {filter.count}
                </Badge>
              </button>
            );
          })}
        </div>
      )}

      {/* Collapsed view - show active filters summary */}
      {!isExpanded && activeFilters.size > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {filters
            .filter(f => activeFilters.has(f.id))
            .map((filter) => (
              <div
                key={filter.id}
                className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
              >
                <span role="img" aria-label={filter.label}>
                  {filter.emoji}
                </span>
                <span>{filter.label}</span>
                <span className="text-blue-600 font-semibold">{filter.count}</span>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
