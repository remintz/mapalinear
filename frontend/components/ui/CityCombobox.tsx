'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { useMunicipalities } from '@/hooks/useMunicipalities';
import { Municipality } from '@/lib/api';
import { MapPin, ChevronDown, Loader2, X } from 'lucide-react';

interface CityComboboxProps {
  /** Current value in format "City, UF" */
  value: string;
  /** Called when value changes */
  onChange: (value: string) => void;
  /** Placeholder text */
  placeholder?: string;
  /** Whether the input is disabled */
  disabled?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Input ID for form labels */
  id?: string;
  /** Error state */
  error?: boolean;
}

export function CityCombobox({
  value,
  onChange,
  placeholder = 'Digite o nome da cidade...',
  disabled = false,
  className,
  id,
  error = false,
}: CityComboboxProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [inputValue, setInputValue] = useState(value);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const { filter, isLoading } = useMunicipalities();

  // Get filtered results based on input
  const filteredMunicipalities = filter(inputValue);

  // Sync input value with external value
  useEffect(() => {
    setInputValue(value);
  }, [value]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Scroll highlighted item into view
  useEffect(() => {
    if (isOpen && listRef.current) {
      const highlightedItem = listRef.current.children[highlightedIndex] as HTMLElement;
      if (highlightedItem) {
        highlightedItem.scrollIntoView({ block: 'nearest' });
      }
    }
  }, [highlightedIndex, isOpen]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setInputValue(newValue);
    setIsOpen(true);
    setHighlightedIndex(0);

    // Also update the form value as user types
    onChange(newValue);
  };

  const handleSelectMunicipality = useCallback((municipality: Municipality) => {
    const formattedValue = `${municipality.nome}, ${municipality.uf}`;
    setInputValue(formattedValue);
    onChange(formattedValue);
    setIsOpen(false);
    inputRef.current?.blur();
  }, [onChange]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!isOpen) {
      if (e.key === 'ArrowDown' || e.key === 'Enter') {
        setIsOpen(true);
        e.preventDefault();
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightedIndex((prev) =>
          prev < filteredMunicipalities.length - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : 0));
        break;
      case 'Enter':
        e.preventDefault();
        if (filteredMunicipalities[highlightedIndex]) {
          handleSelectMunicipality(filteredMunicipalities[highlightedIndex]);
        }
        break;
      case 'Escape':
        setIsOpen(false);
        break;
      case 'Tab':
        setIsOpen(false);
        break;
    }
  };

  const handleClear = () => {
    setInputValue('');
    onChange('');
    inputRef.current?.focus();
  };

  return (
    <div ref={containerRef} className="relative w-full">
      <div className="relative">
        <MapPin className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />

        <input
          ref={inputRef}
          id={id}
          type="text"
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => inputValue.length >= 2 && setIsOpen(true)}
          placeholder={placeholder}
          disabled={disabled}
          autoComplete="off"
          className={cn(
            'block w-full rounded-md border border-gray-300 pl-10 pr-16 py-2',
            'text-gray-900 placeholder-gray-500',
            'focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500',
            'disabled:bg-gray-50 disabled:text-gray-500 disabled:cursor-not-allowed',
            error && 'border-red-300 focus:border-red-500 focus:ring-red-500',
            className
          )}
        />

        <div className="absolute right-2 top-1/2 transform -translate-y-1/2 flex items-center gap-1">
          {isLoading && (
            <Loader2 className="h-4 w-4 text-gray-400 animate-spin" />
          )}

          {inputValue && !disabled && (
            <button
              type="button"
              onClick={handleClear}
              className="p-1 text-gray-400 hover:text-gray-600 rounded"
            >
              <X className="h-4 w-4" />
            </button>
          )}

          <ChevronDown
            className={cn(
              'h-4 w-4 text-gray-400 transition-transform',
              isOpen && 'transform rotate-180'
            )}
          />
        </div>
      </div>

      {/* Dropdown */}
      {isOpen && filteredMunicipalities.length > 0 && (
        <ul
          ref={listRef}
          className="absolute z-50 mt-1 w-full max-h-60 overflow-auto rounded-md bg-white py-1 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none"
        >
          {filteredMunicipalities.map((municipality, index) => (
            <li
              key={municipality.id}
              onClick={() => handleSelectMunicipality(municipality)}
              onMouseEnter={() => setHighlightedIndex(index)}
              className={cn(
                'cursor-pointer select-none px-3 py-2 text-sm',
                index === highlightedIndex
                  ? 'bg-blue-50 text-blue-900'
                  : 'text-gray-900 hover:bg-gray-50'
              )}
            >
              <span className="font-medium">{municipality.nome}</span>
              <span className="ml-2 text-gray-500">{municipality.uf}</span>
            </li>
          ))}
        </ul>
      )}

      {/* No results message */}
      {isOpen && inputValue.length >= 2 && filteredMunicipalities.length === 0 && !isLoading && (
        <div className="absolute z-50 mt-1 w-full rounded-md bg-white py-3 px-4 shadow-lg ring-1 ring-black ring-opacity-5 text-sm text-gray-500">
          Nenhuma cidade encontrada
        </div>
      )}

      {/* Loading message */}
      {isOpen && inputValue.length >= 2 && isLoading && (
        <div className="absolute z-50 mt-1 w-full rounded-md bg-white py-3 px-4 shadow-lg ring-1 ring-black ring-opacity-5 text-sm text-gray-500 flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" />
          Carregando cidades...
        </div>
      )}
    </div>
  );
}
