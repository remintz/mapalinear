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
                  {estimatedCompletion && (() => {
                    const remainingMs = new Date(estimatedCompletion).getTime() - Date.now();
                    if (remainingMs <= 0) return null;
                    const remainingSec = Math.ceil(remainingMs / 1000);
                    const minutes = Math.floor(remainingSec / 60);
                    const seconds = remainingSec % 60;
                    return <span>Restante: {String(minutes).padStart(2, '0')}:{String(seconds).padStart(2, '0')}</span>;
                  })()}
                </div>
              </div>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}