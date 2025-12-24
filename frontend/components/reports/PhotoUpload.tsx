'use client';

import { useCallback, useRef } from 'react';
import { Plus, X } from 'lucide-react';

interface PhotoUploadProps {
  photos: File[];
  onPhotosChange: (photos: File[]) => void;
  maxPhotos?: number;
  disabled?: boolean;
}

export function PhotoUpload({
  photos,
  onPhotosChange,
  maxPhotos = 3,
  disabled = false,
}: PhotoUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files || []);
      const remainingSlots = maxPhotos - photos.length;
      const newPhotos = files.slice(0, remainingSlots);

      if (newPhotos.length > 0) {
        onPhotosChange([...photos, ...newPhotos]);
      }

      // Reset input
      if (inputRef.current) {
        inputRef.current.value = '';
      }
    },
    [photos, maxPhotos, onPhotosChange]
  );

  const removePhoto = useCallback(
    (index: number) => {
      const newPhotos = photos.filter((_, i) => i !== index);
      onPhotosChange(newPhotos);
    },
    [photos, onPhotosChange]
  );

  const canAddMore = photos.length < maxPhotos;

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-zinc-700">
        Fotos ({photos.length}/{maxPhotos})
      </label>

      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        multiple
        onChange={handleFileChange}
        disabled={disabled || !canAddMore}
        className="hidden"
      />

      {photos.length === 0 ? (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={disabled}
          className="w-24 h-24 border-2 border-dashed border-zinc-300 rounded-lg
                     flex items-center justify-center
                     text-zinc-400 hover:border-zinc-400 hover:text-zinc-500
                     transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Plus className="w-8 h-8" />
        </button>
      ) : (
        <div className="grid grid-cols-3 gap-2">
          {photos.map((photo, index) => (
            <div key={index} className="relative aspect-square">
              <img
                src={URL.createObjectURL(photo)}
                alt={`Foto ${index + 1}`}
                className="w-full h-full object-cover rounded-lg"
              />
              <button
                type="button"
                onClick={() => removePhoto(index)}
                disabled={disabled}
                className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white
                           rounded-full flex items-center justify-center
                           hover:bg-red-600 disabled:opacity-50"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
          {canAddMore && (
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              disabled={disabled}
              className="aspect-square border-2 border-dashed border-zinc-300 rounded-lg
                         flex items-center justify-center text-zinc-400
                         hover:border-zinc-400 hover:text-zinc-500
                         disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Plus className="w-8 h-8" />
            </button>
          )}
        </div>
      )}
    </div>
  );
}
