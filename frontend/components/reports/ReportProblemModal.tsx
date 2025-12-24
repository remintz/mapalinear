'use client';

import { useState, useCallback, useEffect } from 'react';
import { X, AlertTriangle, Loader2, ChevronDown } from 'lucide-react';
import { toast } from 'sonner';
import { useProblemTypes } from '@/hooks/useProblemTypes';
import { apiClient } from '@/lib/api';
import { PhotoUpload } from './PhotoUpload';
import { POICombobox } from './POICombobox';
import { AudioRecorder } from './AudioRecorder';

interface POI {
  id: string;
  name: string;
  type: string;
  distance_from_origin_km?: number;
}

interface ReportProblemModalProps {
  isOpen: boolean;
  onClose: () => void;
  mapId?: string;
  pois: POI[];
  userLocation?: { lat: number; lon: number };
}

export function ReportProblemModal({
  isOpen,
  onClose,
  mapId,
  pois,
  userLocation,
}: ReportProblemModalProps) {
  const { problemTypes, isLoading: typesLoading } = useProblemTypes();

  const [selectedTypeId, setSelectedTypeId] = useState<string>('');
  const [selectedPoiId, setSelectedPoiId] = useState<string | null>(null);
  const [description, setDescription] = useState('');
  const [photos, setPhotos] = useState<File[]>([]);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [typeDropdownOpen, setTypeDropdownOpen] = useState(false);

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setSelectedTypeId('');
      setSelectedPoiId(null);
      setDescription('');
      setPhotos([]);
      setAudioBlob(null);
    }
  }, [isOpen]);

  const handleSubmit = useCallback(async () => {
    if (!selectedTypeId) {
      toast.error('Selecione o tipo de problema');
      return;
    }
    if (description.length < 10) {
      toast.error('Descricao deve ter pelo menos 10 caracteres');
      return;
    }

    setIsSubmitting(true);

    try {
      const formData = new FormData();
      formData.append('problem_type_id', selectedTypeId);
      formData.append('description', description);

      if (userLocation) {
        formData.append('latitude', userLocation.lat.toString());
        formData.append('longitude', userLocation.lon.toString());
      }

      if (mapId) {
        formData.append('map_id', mapId);
      }
      if (selectedPoiId) {
        formData.append('poi_id', selectedPoiId);
      }

      // Add photos
      photos.forEach((photo) => {
        formData.append('photos', photo);
      });

      // Add audio
      if (audioBlob) {
        formData.append('audio', audioBlob, 'recording.webm');
      }

      await apiClient.submitProblemReport(formData);

      toast.success('Problema reportado com sucesso!');
      onClose();
    } catch (error) {
      console.error('Error submitting report:', error);
      toast.error(
        error instanceof Error ? error.message : 'Erro ao enviar report'
      );
    } finally {
      setIsSubmitting(false);
    }
  }, [
    selectedTypeId,
    description,
    userLocation,
    mapId,
    selectedPoiId,
    photos,
    audioBlob,
    onClose,
  ]);

  if (!isOpen) return null;

  const selectedType = problemTypes.find((t) => t.id === selectedTypeId);

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-white w-full sm:max-w-lg sm:rounded-lg max-h-[90vh] overflow-y-auto rounded-t-2xl">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            <h2 className="text-lg font-semibold">Reportar Problema</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-zinc-400 hover:text-zinc-600 rounded-full hover:bg-zinc-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Problem Type Selector */}
          <div className="space-y-1">
            <label className="text-sm font-medium text-zinc-700">
              Tipo de Problema *
            </label>
            <div className="relative">
              <button
                type="button"
                onClick={() => setTypeDropdownOpen(!typeDropdownOpen)}
                disabled={typesLoading}
                className={`w-full px-3 py-2 border rounded-lg text-left flex items-center justify-between
                           ${typeDropdownOpen ? 'border-blue-500 ring-2 ring-blue-100' : 'border-zinc-300'}
                           ${typesLoading ? 'opacity-50' : ''}`}
              >
                <span className={selectedType ? 'text-zinc-900' : 'text-zinc-500'}>
                  {typesLoading
                    ? 'Carregando...'
                    : selectedType?.name || 'Selecione o tipo de problema'}
                </span>
                <ChevronDown
                  className={`w-4 h-4 text-zinc-400 transition-transform ${
                    typeDropdownOpen ? 'rotate-180' : ''
                  }`}
                />
              </button>

              {typeDropdownOpen && (
                <div className="absolute z-10 w-full mt-1 bg-white border border-zinc-200 rounded-lg shadow-lg max-h-48 overflow-auto">
                  {problemTypes.map((type) => (
                    <button
                      key={type.id}
                      type="button"
                      onClick={() => {
                        setSelectedTypeId(type.id);
                        setTypeDropdownOpen(false);
                      }}
                      className={`w-full px-3 py-2 text-left text-sm hover:bg-zinc-50
                                 ${type.id === selectedTypeId ? 'bg-blue-50 text-blue-600' : ''}`}
                    >
                      <div className="font-medium">{type.name}</div>
                      {type.description && (
                        <div className="text-xs text-zinc-500">{type.description}</div>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* POI Selector */}
          {pois.length > 0 && (
            <POICombobox
              pois={pois}
              value={selectedPoiId}
              onChange={setSelectedPoiId}
              disabled={isSubmitting}
            />
          )}

          {/* Description */}
          <div className="space-y-1">
            <label className="text-sm font-medium text-zinc-700">
              Descricao *
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Descreva o problema em detalhes..."
              rows={4}
              disabled={isSubmitting}
              className="w-full px-3 py-2 border border-zinc-300 rounded-lg resize-none
                        focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none
                        disabled:opacity-50"
            />
            <div className={`text-xs text-right ${description.length < 10 ? 'text-red-500' : 'invisible'}`}>
              digite mais de 10 caracteres
            </div>
          </div>

          {/* Photo Upload */}
          <PhotoUpload
            photos={photos}
            onPhotosChange={setPhotos}
            maxPhotos={3}
            disabled={isSubmitting}
          />

          {/* Audio Recorder - only renders if supported */}
          <AudioRecorder
            audioBlob={audioBlob}
            onAudioChange={setAudioBlob}
            disabled={isSubmitting}
          />
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-white border-t px-4 py-3 flex gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="flex-1 px-4 py-2 border border-zinc-300 rounded-lg text-zinc-700
                      hover:bg-zinc-50 disabled:opacity-50"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting || !selectedTypeId || description.length < 10}
            className="flex-1 px-4 py-2 bg-amber-500 text-white rounded-lg
                      hover:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed
                      flex items-center justify-center gap-2"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Enviando...
              </>
            ) : (
              'Enviar Reporte'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
