# Relatório Comparativo: OSM vs HERE Maps - Qualidade de POIs

**Data:** 2025-12-14
**Trajeto Analisado:** Belo Horizonte → Ouro Preto (99 km)
**Status:** Análise Concluída

---

## 1. Resumo Executivo

Este relatório compara a qualidade dos dados de POIs (Points of Interest) entre OpenStreetMap (OSM) e HERE Maps, usando como base o trajeto BH-Ouro Preto armazenado no banco de dados do MapaLinear.

### Conclusão Principal

O HERE Maps oferece **melhor qualidade de dados cadastrais** (nomes, telefones, websites, horários), enquanto o OSM com enriquecimento Google Places oferece **melhor cobertura de ratings**. Uma abordagem híbrida é recomendada.

---

## 2. Dados Quantitativos

### POIs Encontrados no Trajeto

| Categoria | OSM (atual) | HERE Maps | Diferença |
|-----------|-------------|-----------|-----------|
| Postos de Combustível | 13 | ~10-15 | Similar |
| Restaurantes | 36 | 100+ | HERE 3x mais |
| Hotéis/Pousadas | 16 | 100+ | HERE 6x mais |
| Hospitais | 1 | ~90* | HERE muito mais |
| Cidades/Vilas | 8 | N/A | Apenas OSM |

*HERE inclui clínicas, óticas e outros estabelecimentos de saúde na categoria "Hospital"

---

## 3. Análise Qualitativa por Categoria

### 3.1 Postos de Combustível

| Critério | OSM | HERE | Vencedor |
|----------|-----|------|----------|
| POIs com nome próprio | 54% (7/13) | ~90% | **HERE** |
| Marcas identificadas | 46% (6/13) | ~80% | **HERE** |
| Telefone disponível | 0% (0/13) | ~60% | **HERE** |
| Cobertura geográfica | Boa | Boa | Empate |

**Exemplos Comparativos:**

| Km | OSM | HERE |
|----|-----|------|
| 11 | Posto Fernanda | Ipiranga Tel: +553130451008 |
| 16 | Posto Mutuca [Ipiranga] | Ipiranga |
| 18 | BR [BR] | Petrobras Tel: +553135420962 |
| 21 | Posto Água Boa | Bandeira Branca |

**Observação:** OSM usa nomes genéricos como "fuel" para postos não identificados.

### 3.2 Restaurantes

| Critério | OSM | HERE | Vencedor |
|----------|-----|------|----------|
| POIs com nome próprio | 69% (25/36) | ~95% | **HERE** |
| Tipo de cozinha | 0% | Sim (via categoria) | **HERE** |
| Rating disponível | 78% (28/36)* | Não nativo** | **OSM** |
| Telefone disponível | 6% (2/36) | ~50% | **HERE** |
| Volume de POIs | 36 | 100+ | **HERE** |

*Ratings obtidos via enriquecimento Google Places
**HERE possui referências TripAdvisor/Yelp, mas não retorna ratings diretamente

**Exemplos OSM com nomes genéricos:**
- `cafe` (sem nome)
- `fast_food` (sem nome)
- `restaurant` (sem nome)

**Exemplos HERE:**
- Bar e Restaurante 7 d'Ouro [Restaurante]
- Restaurante Jacubas [Restaurante]
- Mais1cafe [Fast Food]

### 3.3 Hotéis/Pousadas

| Critério | OSM | HERE | Vencedor |
|----------|-----|------|----------|
| POIs com nome próprio | 100% | 100% | Empate |
| Rating disponível | 94% (15/16)* | Não nativo | **OSM** |
| Telefone disponível | 6% (1/16) | ~80% | **HERE** |
| Website disponível | 13% (2/16) | ~60% | **HERE** |
| Horários de funcionamento | 0% | ~40% | **HERE** |
| Volume de POIs | 16 | 100+ | **HERE** |

*Ratings obtidos via enriquecimento Google Places

**Exemplos OSM:**
```
Hotel Água Boa ★4.0(467)
Hotel Bandeirantes ★4.5(243)
Pousada Clássica ★4.6(896)
```

**Exemplos HERE:**
```
Pousada Laços de Minas [tel] [web]
History Hostel [tel] [web]
Hotel Barroco Mineiro [tel] [web]
```

---

## 4. Campos Disponíveis por Provedor

### OSM (com Google Places)

| Campo | Disponibilidade | Fonte |
|-------|-----------------|-------|
| Nome | ~70% (resto genérico) | OSM |
| Coordenadas | 100% | OSM |
| Categoria | 100% | OSM |
| Marca/Bandeira | ~50% (postos) | OSM |
| Rating | ~80% | Google Places |
| Review Count | ~80% | Google Places |
| Google Maps URI | ~80% | Google Places |
| Telefone | ~5% | OSM |
| Website | ~10% | OSM |
| Horários | ~5% | OSM |
| Endereço estruturado | Não | - |

### HERE Maps

| Campo | Disponibilidade | Fonte |
|-------|-----------------|-------|
| Nome | ~95% | HERE |
| Coordenadas | 100% | HERE |
| Categoria | 100% | HERE |
| Subcategoria | 100% | HERE |
| Telefone | ~60-80% | HERE |
| Website | ~50-60% | HERE |
| Horários | ~40% | HERE |
| Endereço estruturado | 100% | HERE |
| Referência TripAdvisor | ~30% | HERE |
| Referência Yelp | ~20% | HERE |
| Rating | Não nativo | - |

---

## 5. Estrutura de Dados HERE

Exemplo de resposta HERE para um hotel:

```json
{
  "title": "Pousada Laços de Minas",
  "id": "here:pds:place:0767h3h4-b501cb0af83541538b612edf3906c899",
  "address": {
    "label": "Pousada Laços de Minas, Rua dos Paulistas, 43, Centro, Ouro Preto - MG, 35400-030, Brasil",
    "countryCode": "BRA",
    "state": "Minas Gerais",
    "city": "Ouro Preto",
    "district": "Centro",
    "street": "Rua dos Paulistas",
    "postalCode": "35400-030",
    "houseNumber": "43"
  },
  "position": { "lat": -20.38539, "lng": -43.50202 },
  "categories": [
    { "id": "500-5000-0053", "name": "Hotel", "primary": true },
    { "id": "500-5100-0057", "name": "Pensão" }
  ],
  "contacts": [
    {
      "phone": [{ "value": "+553135522597" }],
      "www": [{ "value": "http://www.lacosdeminas.com.br" }]
    }
  ],
  "openingHours": [{ "text": ["seg.-dom.: 00:00 - 24:00"] }],
  "references": [
    { "supplier": { "id": "tripadvisor" }, "id": "2402590" },
    { "supplier": { "id": "yelp" }, "id": "Nv_URBAb-MwPzUO0qwxrNQ" }
  ]
}
```

---

## 6. Custos

### OSM
- **Custo:** Gratuito
- **Rate Limit:** 1 req/segundo (Overpass API)
- **Termos:** Atribuição obrigatória

### HERE Maps
- **Free Tier:** 250.000 transações/mês
- **Custo acima:** ~$0.50-5.00 por 1.000 requests (varia por endpoint)
- **Rate Limit:** Configurável (10 req/s no plano free)

### Google Places (enriquecimento atual)
- **Custo:** ~$17-35 por 1.000 requests
- **Cache:** 30 dias (conforme ToS)

---

## 7. Recomendações

### Opção 1: Abordagem Híbrida (Recomendada)

```
OSM (gratuito) + Google Places (ratings) + HERE (dados de contato)
```

**Vantagens:**
- Melhor qualidade de dados combinada
- Ratings disponíveis
- Dados de contato completos
- Custo controlado (HERE apenas para enriquecimento)

**Implementação:**
1. Manter OSM como provedor principal de POIs
2. Manter Google Places para ratings (já implementado)
3. Adicionar HERE para enriquecer telefone/website/horários

### Opção 2: HERE como Provedor Principal

```
HERE (principal) + Google Places (ratings)
```

**Vantagens:**
- Dados mais completos nativamente
- Menos processamento de enriquecimento
- Endereços estruturados

**Desvantagens:**
- Custo maior
- Dependência de API paga

### Opção 3: Manter Atual

```
OSM + Google Places
```

**Vantagens:**
- Já funciona
- Menor custo
- Ratings disponíveis

**Desvantagens:**
- Nomes genéricos em ~30% dos POIs
- Poucos dados de contato

---

## 8. Próximos Passos

1. [ ] Implementar modelo de dados que suporte múltiplos provedores por POI
2. [ ] Completar implementação HERE Provider (POI Search, Route)
3. [ ] Criar sistema de enriquecimento HERE (opcional por usuário)
4. [ ] Adicionar flag de provedor premium no perfil do usuário
5. [ ] Implementar merge inteligente de dados OSM + HERE

---

## Anexo: Mapeamento de Categorias OSM ↔ HERE

| Categoria MapaLinear | OSM Tag | HERE Category ID |
|---------------------|---------|------------------|
| GAS_STATION | amenity=fuel | 700-7600-0116 |
| RESTAURANT | amenity=restaurant | 100-1000 |
| HOTEL | tourism=hotel | 500-5000 |
| HOSPITAL | amenity=hospital | 800-8000 |
| PHARMACY | amenity=pharmacy | 900-9100-0102 |
| ATM | amenity=atm | 900-9400-0000 |
| POLICE | amenity=police | 900-9300-0100 |
| MECHANIC | shop=car_repair | 700-7850 |
| SUPERMARKET | shop=supermarket | 600-6300 |

---

**Documento gerado por:** Claude Code
**Versão:** 1.0
