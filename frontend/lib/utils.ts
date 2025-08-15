import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Utility to combine CSS classes with Tailwind
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format distance for display
 */
export function formatDistance(distanceKm: number): string {
  if (distanceKm < 1) {
    return `${Math.round(distanceKm * 1000)}m`;
  }
  return `${distanceKm.toFixed(1)}km`;
}

/**
 * Validate if a string is a valid Brazilian location format
 */
export function isValidBrazilianLocation(location: string): boolean {
  // Check if location follows pattern "City, State" or "City, UF"
  return /^.+,\s*[A-Z]{2}$/.test(location.trim());
}