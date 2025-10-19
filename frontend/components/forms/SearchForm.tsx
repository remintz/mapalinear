'use client';

import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Search, MapPin, Settings } from 'lucide-react';
import { Button, Input, Card, CardHeader, CardTitle, CardContent } from '@/components/ui';
import { searchFormSchema, SearchFormData } from '@/lib/validations';

interface SearchFormProps {
  onSubmit: (data: SearchFormData) => void;
  isLoading?: boolean;
  error?: string | null;
  progressMessage?: string;
  progressPercent?: number;
  estimatedCompletion?: string | null;
}

export function SearchForm({
  onSubmit,
  isLoading = false,
  error,
  progressMessage = 'Criar Mapa',
  progressPercent = 0,
  estimatedCompletion
}: SearchFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    setValue,
  } = useForm<SearchFormData>({
    resolver: zodResolver(searchFormSchema),
    defaultValues: {
      origin: '',
      destination: '',
      maxDistance: 5,
    },
  });

  const watchedValues = watch();

  const handleFormSubmit = (data: SearchFormData) => {
    onSubmit(data);
  };

  const swapOriginDestination = () => {
    const origin = watchedValues.origin;
    const destination = watchedValues.destination;
    setValue('origin', destination);
    setValue('destination', origin);
  };

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Search className="h-5 w-5" />
          Criar Mapa
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6">
          {/* Error display */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
              {error}
            </div>
          )}

          {/* Origin and Destination */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label htmlFor="origin" className="block text-sm font-medium text-gray-700">
                Origem
              </label>
              <div className="relative">
                <MapPin className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  id="origin"
                  {...register('origin')}
                  placeholder="São Paulo, SP"
                  className="pl-10"
                  disabled={isLoading}
                />
              </div>
              {errors.origin && (
                <p className="text-sm text-red-600">{errors.origin.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <label htmlFor="destination" className="block text-sm font-medium text-gray-700">
                Destino
              </label>
              <div className="relative">
                <MapPin className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  id="destination"
                  {...register('destination')}
                  placeholder="Rio de Janeiro, RJ"
                  className="pl-10"
                  disabled={isLoading}
                />
              </div>
              {errors.destination && (
                <p className="text-sm text-red-600">{errors.destination.message}</p>
              )}
            </div>
          </div>

          {/* Swap button */}
          <div className="flex justify-center">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={swapOriginDestination}
              disabled={isLoading}
              className="text-blue-600 hover:text-blue-700"
            >
              ⇄ Trocar origem e destino
            </Button>
          </div>

          {/* Max Distance */}
          <div className="space-y-2">
            <label htmlFor="maxDistance" className="block text-sm font-medium text-gray-700">
              <span className="flex items-center gap-2">
                Raio de busca dos pontos de interesse
                <div className="group relative">
                  <button type="button" className="text-gray-400 hover:text-gray-600">
                    <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                    </svg>
                  </button>
                  <div className="invisible group-hover:visible absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg whitespace-nowrap z-10">
                    <div className="max-w-xs">
                      Define a que distância da rodovia buscar por postos, restaurantes e pedágios. 
                      Valores menores (1-2km) mostram apenas POIs muito próximos. 
                      Valores maiores (10-20km) incluem estabelecimentos em centros urbanos próximos.
                    </div>
                    <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
                  </div>
                </div>
              </span>
            </label>
            <div className="relative inline-flex items-center">
              <Input
                id="maxDistance"
                type="number"
                {...register('maxDistance', { valueAsNumber: true })}
                min="1"
                max="20"
                step="1"
                disabled={isLoading}
                className="w-20 text-right pr-8"
              />
              <span className="absolute right-2 text-sm text-gray-600 pointer-events-none">km</span>
            </div>
            {errors.maxDistance && (
              <p className="text-sm text-red-600">{errors.maxDistance.message}</p>
            )}
          </div>

          {/* Submit Button */}
          <div className="space-y-3">
            <Button
              type="submit"
              size="lg"
              isLoading={isLoading}
              disabled={isLoading}
              className="w-full"
            >
              {progressMessage}
            </Button>
            
            {/* Progress Bar */}
            {isLoading && (
              <div className="space-y-2">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${progressPercent}%` }}
                  ></div>
                </div>
                <div className="flex justify-between text-xs text-gray-600">
                  <span>{progressPercent}%</span>
                  {estimatedCompletion && (
                    <span>ETA: {new Date(estimatedCompletion).toLocaleTimeString()}</span>
                  )}
                </div>
              </div>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}