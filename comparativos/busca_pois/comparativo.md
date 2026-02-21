# Relatório Comparativo: Busca de POIs

**Data:** 2026-02-21 13:58  
**Rota:** Belo Horizonte, MG → Ouro Preto, MG  
**Comprimento:** 99.1 km  
**Pontos de busca:** 20  
**Raio de busca:** 1000 m  

---

## Resumo Executivo

| Provider | Total POIs | Tempo Médio/Req | Requests |
|----------|------------|-----------------|----------|
| Overpass | 219 | 6.499s | 20 |
| Mapbox | 193 | 0.139s | 140 |
| HERE | 206 | 0.511s | 20 |

## POIs por Categoria

| Categoria | Overpass | Mapbox | HERE |
|---|---|---|---|
| food | 0 | 61 | 0 |
| gas_station | 27 | 0 | 0 |
| hospital | 12 | 25 | 1 |
| hotel | 18 | 35 | 18 |
| other | 0 | 0 | 23 |
| restaurant | 162 | 72 | 164 |

## Detalhamento por Provider

### Overpass

**gas_station** (27 resultados):
- Ipiranga
- BR
- Ipiranga
- Posto Alex
- Sem nome
- ... e mais 22

**hospital** (12 resultados):
- Axial
- Premier Tower
- Instituto Baeta
- Maternidade NeoCenter
- CAV Central de Atendimento ao Viajante
- ... e mais 7

**hotel** (18 resultados):
- Bristol
- Hotel Mercure
- Royal Golden Hotel
- Flamboyant Home Service
- Hotel Boulevard
- ... e mais 13

**restaurant** (162 resultados):
- Pizza Sur
- Fujiyama
- Sem nome
- Redentor
- Sem nome
- ... e mais 157

### Mapbox

**food** (61 resultados):
- Momo Cafe
- Bob's
- Minas Grill
- Frango's no Balde
- Sucos & Cia
- ... e mais 56

**hospital** (25 resultados):
- ManausLAB
- IES
- Clínica de Angiologia
- CMH Medicina Hospitalar Unidade Consultorios
- TV Saúde
- ... e mais 20

**hotel** (35 resultados):
- Hotel Max Savassi
- ibis Belo Horizonte Savassi
- Promenade Ianelli
- Motel
- Savassi
- ... e mais 30

**restaurant** (72 resultados):
- Ice Creamy
- Subway
- Ludica Doces
- Restaurante Outback Steakhouse
- Yo-Yo Mercearia Moderna Oriental
- ... e mais 67

### HERE

**hospital** (1 resultados):
- Hospital Vila da Serra

**hotel** (18 resultados):
- Max Savassi
- Radisson Blu Belo Horizonte Savassi
- República Ameno
- Flat Califórnia BH
- Hotel Príncipe
- ... e mais 13

**other** (23 resultados):
- Spoleto
- Outback Steakhouse
- Pomodori Pizza
- Petrobras
- Petrobras
- ... e mais 18

**restaurant** (164 resultados):
- Terraço Leitura Bar & Restaurante
- Bacio di Latte
- Paris 6 Bistrô
- SUBWAY
- Dona Conceição
- ... e mais 159

## Análise

### Overpass (OpenStreetMap)
- **Vantagens:**
  - Dados abertos e gratuitos
  - Grande base de dados de POIs
  - Não requer API key
- **Desvantagens:**
  - Rate limiting (1 req/s)
  - API pode estar instável
  - Dados menos estruturados

### Mapbox
- **Vantagens:**
  - API rápida e confiável
  - Dados bem estruturados
  - Boa cobertura em áreas urbanas
- **Desvantagens:**
  - Custo após limite gratuito
  - Menor cobertura que OSM em áreas remotas

### HERE
- **Vantagens:**
  - API robusta e confiável
  - Dados de alta qualidade
  - Bom para Brasil
- **Desvantagens:**
  - Custo por requisição
  - Requer API key

### Recomendação
Para o MapaLinear, considerando o custo-benefício:
1. **Overpass** para desenvolvimento e testes (gratuito)
2. **HERE** para produção (melhor qualidade de dados para rotas brasileiras)

---

*Relatório gerado automaticamente em 2026-02-21 13:58*
