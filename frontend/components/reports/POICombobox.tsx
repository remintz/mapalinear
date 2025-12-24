'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { ChevronDown, X, MapPin } from 'lucide-react';

interface POI {
  id: string;
  name: string;
  type: string;
  distance_from_origin_km?: number;
}

interface POIComboboxProps {
  pois: POI[];
  value: string | null;
  onChange: (poiId: string | null) => void;
  placeholder?: string;
  disabled?: boolean;
}

const POI_TYPE_LABELS: Record<string, string> = {
  gas_station: 'Posto',
  restaurant: 'Restaurante',
  hotel: 'Hotel',
  camping: 'Camping',
  hospital: 'Hospital',
  toll_booth: 'Pedágio',
  city: 'Cidade',
  town: 'Cidade',
  village: 'Vila',
};

export function POICombobox({
  pois,
  value,
  onChange,
  placeholder = 'Selecione um POI (opcional)',
  disabled = false,
}: POIComboboxProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const selectedPoi = pois.find((poi) => poi.id === value);

  const filteredPois = pois.filter((poi) => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return (
      poi.name.toLowerCase().includes(searchLower) ||
      (POI_TYPE_LABELS[poi.type] || poi.type).toLowerCase().includes(searchLower)
    );
  });

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Reset highlight on filter change
  useEffect(() => {
    setHighlightedIndex(0);
  }, [search]);

  const handleSelect = useCallback(
    (poiId: string) => {
      onChange(poiId);
      setIsOpen(false);
      setSearch('');
    },
    [onChange]
  );

  const handleClear = useCallback(() => {
    onChange(null);
    setSearch('');
  }, [onChange]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) {
      if (e.key === 'ArrowDown' || e.key === 'Enter') {
        setIsOpen(true);
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightedIndex((i) => Math.min(i + 1, filteredPois.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex((i) => Math.max(i - 1, 0));
        break;
      case 'Enter':
        e.preventDefault();
        if (filteredPois[highlightedIndex]) {
          handleSelect(filteredPois[highlightedIndex].id);
        }
        break;
      case 'Escape':
        setIsOpen(false);
        break;
    }
  };

  return (
    <div ref={containerRef} className="relative">
      <label className="text-sm font-medium text-zinc-700 block mb-1">
        POI relacionado (opcional)
      </label>

      <div
        className={`relative flex items-center border rounded-lg bg-white
                    ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                    ${isOpen ? 'border-blue-500 ring-2 ring-blue-100' : 'border-zinc-300'}`}
      >
        <div className="flex-1 flex items-center">
          {selectedPoi && !isOpen ? (
            <div className="flex items-center gap-2 px-3 py-2 w-full">
              <MapPin className="w-4 h-4 text-zinc-400" />
              <span className="truncate">{selectedPoi.name}</span>
              <span className="text-xs text-zinc-500">
                ({POI_TYPE_LABELS[selectedPoi.type] || selectedPoi.type})
              </span>
            </div>
          ) : (
            <input
              ref={inputRef}
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                if (!isOpen) setIsOpen(true);
              }}
              onFocus={() => setIsOpen(true)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={disabled}
              className="w-full px-3 py-2 bg-transparent outline-none text-sm"
            />
          )}
        </div>

        {selectedPoi && !isOpen && (
          <button
            type="button"
            onClick={handleClear}
            disabled={disabled}
            className="p-2 text-zinc-400 hover:text-zinc-600"
          >
            <X className="w-4 h-4" />
          </button>
        )}

        <button
          type="button"
          onClick={() => !disabled && setIsOpen(!isOpen)}
          disabled={disabled}
          className="p-2 text-zinc-400"
        >
          <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-zinc-200 rounded-lg shadow-lg max-h-60 overflow-auto">
          {filteredPois.length === 0 ? (
            <div className="px-3 py-2 text-sm text-zinc-500">Nenhum POI encontrado</div>
          ) : (
            filteredPois.map((poi, index) => (
              <button
                key={poi.id}
                type="button"
                onClick={() => handleSelect(poi.id)}
                className={`w-full px-3 py-2 text-left text-sm flex items-center gap-2
                            hover:bg-zinc-50
                            ${index === highlightedIndex ? 'bg-blue-50' : ''}
                            ${poi.id === value ? 'text-blue-600 font-medium' : ''}`}
              >
                <MapPin className="w-4 h-4 text-zinc-400 flex-shrink-0" />
                <span className="truncate flex-1">{poi.name}</span>
                <span className="text-xs text-zinc-500 flex-shrink-0">
                  {POI_TYPE_LABELS[poi.type] || poi.type}
                </span>
                {poi.distance_from_origin_km !== undefined && (
                  <span className="text-xs text-zinc-400 flex-shrink-0">
                    {poi.distance_from_origin_km.toFixed(1)} km
                  </span>
                )}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
