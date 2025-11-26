import React from 'react';

interface FilterOption {
  id: string;
  label: string;
  icon: React.ElementType;
  count: number;
}

interface POIFiltersProps {
  filters: FilterOption[];
  activeFilters: Set<string>;
  onFilterToggle: (filterId: string) => void;
}

export function POIFilters({ filters, activeFilters, onFilterToggle }: POIFiltersProps) {
  // Calculate total POIs from active filters
  const totalActivePOIs = filters
    .filter(f => activeFilters.has(f.id))
    .reduce((sum, f) => sum + f.count, 0);

  return (
    <div className="sticky top-0 z-10 bg-gray-50/95 backdrop-blur-sm border-b border-gray-200 py-3 mb-4">
      <div className="flex flex-wrap gap-2">
        {/* Clear filters button - only show when filters are active */}
        {activeFilters.size > 0 && (
          <button
            onClick={() => filters.forEach(f => activeFilters.has(f.id) && onFilterToggle(f.id))}
            className="inline-flex items-center justify-center h-8 px-3 rounded-full text-xs font-medium bg-zinc-100 text-zinc-600 hover:bg-zinc-200 border border-zinc-200 transition-colors"
          >
            Limpar ({activeFilters.size})
          </button>
        )}

        {/* Filter chips */}
        {filters.map((filter) => {
          const isActive = activeFilters.has(filter.id);
          const Icon = filter.icon;

          return (
            <button
              key={filter.id}
              onClick={() => onFilterToggle(filter.id)}
              className={`
                inline-flex items-center gap-1.5 h-8 px-3 rounded-full text-sm font-medium border transition-all duration-200
                ${isActive
                  ? 'bg-zinc-900 text-white border-zinc-900 shadow-sm'
                  : 'bg-white text-zinc-600 border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                }
              `}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-zinc-300' : 'text-zinc-500'}`} />
              <span>{filter.label}</span>
              <span className={`text-xs ml-0.5 ${isActive ? 'text-zinc-400' : 'text-zinc-400'}`}>
                {filter.count}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
