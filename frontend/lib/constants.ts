// POI Type configurations
export const POI_CONFIGS = {
  gas_station: {
    label: 'Postos de Combustível',
    color: '#22c55e', // green-500
    icon: '⛽',
  },
  restaurant: {
    label: 'Restaurantes',
    color: '#f59e0b', // amber-500
    icon: '🍽️',
  },
  toll_booth: {
    label: 'Pedágios',
    color: '#ef4444', // red-500
    icon: '🛣️',
  },
  city: {
    label: 'Cidades',
    color: '#3b82f6', // blue-500
    icon: '🏙️',
  },
} as const;

// Default form values
export const DEFAULT_SEARCH_VALUES = {
  origin: '',
  destination: '',
  includeGasStations: true,
  includeRestaurants: false,
  includeTollBooths: true,
  maxDistance: 1000,
} as const;

// API endpoints
export const API_ENDPOINTS = {
  LINEAR_MAP: '/roads/linear-map',
  HEALTH: '/health',
} as const;

// App metadata
export const APP_CONFIG = {
  name: 'MapaLinear',
  description: 'Mapas lineares para viagens brasileiras',
  version: '1.0.0',
} as const;