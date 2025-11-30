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
    <div className="sticky top-16 z-10 bg-gray-50/95 backdrop-blur-sm border-b border-gray-200 lg:border-b-0 lg:border-r lg:bg-transparent lg:backdrop-blur-none py-3 mb-4 lg:mb-0 lg:py-0 lg:pr-4">
      {/* Desktop: Title */}
      <h3 className="hidden lg:block text-sm font-semibold text-gray-900 mb-3">Filtros</h3>

      {/* Filters container - horizontal on mobile, vertical on desktop */}
      <div className="flex flex-wrap gap-2 lg:flex-col lg:gap-1">
        {/* Clear filters button - only show when filters are active */}
        {activeFilters.size > 0 && (
          <button
            onClick={() => filters.forEach(f => activeFilters.has(f.id) && onFilterToggle(f.id))}
            className="inline-flex items-center justify-center h-8 px-3 rounded-full lg:rounded-lg lg:w-full lg:justify-start text-xs font-medium bg-zinc-100 text-zinc-600 hover:bg-zinc-200 border border-zinc-200 transition-colors"
          >
            Limpar ({activeFilters.size})
          </button>
        )}

        {/* Filter chips/buttons */}
        {filters.map((filter) => {
          const isActive = activeFilters.has(filter.id);
          const Icon = filter.icon;

          return (
            <button
              key={filter.id}
              onClick={() => onFilterToggle(filter.id)}
              className={`
                inline-flex items-center gap-1.5 h-8 px-3 rounded-full lg:rounded-lg lg:w-full lg:justify-between text-sm font-medium border transition-all duration-200
                ${isActive
                  ? 'bg-zinc-900 text-white border-zinc-900 shadow-sm'
                  : 'bg-white text-zinc-600 border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                }
              `}
            >
              <span className="inline-flex items-center gap-1.5">
                <Icon className={`w-4 h-4 ${isActive ? 'text-zinc-300' : 'text-zinc-500'}`} />
                <span>{filter.label}</span>
              </span>
              <span className={`text-xs ml-0.5 ${isActive ? 'text-zinc-400' : 'text-zinc-400'}`}>
                {filter.count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Desktop: Total count */}
      <div className="hidden lg:block mt-4 pt-4 border-t border-gray-200">
        <p className="text-xs text-gray-500">
          {totalActivePOIs} pontos selecionados
        </p>
      </div>
    </div>
  );
}
