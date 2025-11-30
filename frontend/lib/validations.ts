import { z } from 'zod';

// Search form validation schema
export const searchFormSchema = z.object({
  origin: z
    .string()
    .min(1, 'Origem é obrigatória')
    .regex(/^.+,\s*[A-Z]{2}$/, 'Formato: Cidade, UF (ex: São Paulo, SP)'),
  destination: z
    .string()
    .min(1, 'Destino é obrigatório')
    .regex(/^.+,\s*[A-Z]{2}$/, 'Formato: Cidade, UF (ex: Rio de Janeiro, RJ)'),
  maxDistance: z
    .number()
    .min(1, 'Distância deve ser maior que 0')
    .max(20, 'Distância máxima: 20km'),
});

export type SearchFormData = z.infer<typeof searchFormSchema>;