import requests
import networkx as nx
import matplotlib.pyplot as plt
from geopy.geocoders import Nominatim
import json
import math
import time

def get_route_overpass(origem, destino):
    # Inicializar o geocodificador
    geolocator = Nominatim(user_agent="route_planner_overpass")
    
    # Geocodificar os locais
    local_origem = geolocator.geocode(f"{origem}, Brasil")
    local_destino = geolocator.geocode(f"{destino}, Brasil")
    
    if not local_origem or not local_destino:
        return "Erro: Não foi possível encontrar uma ou ambas as cidades."
    
    # Obter as coordenadas
    origem_lat, origem_lng = local_origem.latitude, local_origem.longitude
    destino_lat, destino_lng = local_destino.latitude, local_destino.longitude
    
    print(f"Origem: {origem} ({origem_lat}, {origem_lng})")
    print(f"Destino: {destino} ({destino_lat}, {destino_lng})")
    
    # Calcular a bounding box que engloba origem e destino com uma margem
    min_lat = min(origem_lat, destino_lat) - 0.1
    max_lat = max(origem_lat, destino_lat) + 0.1
    min_lng = min(origem_lng, destino_lng) - 0.1
    max_lng = max(origem_lng, destino_lng) + 0.1
    
    # Lista de servidores Overpass alternativos
    overpass_servers = [
        "https://overpass.kumi.systems/api/interpreter",
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
        "https://overpass.openstreetmap.ru/api/interpreter",
        "https://overpass-api.de/api/interpreter"  # Servidor original como backup
    ]
    
    # Montar a consulta Overpass para obter as estradas na área
    overpass_query = f"""
    [out:json];
    (
      way["highway"~"motorway|trunk|primary|secondary|tertiary|residential|unclassified|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link"]
        ({min_lat},{min_lng},{max_lat},{max_lng});
    );
    out body;
    >;
    out skel qt;
    """
    
    # Tentar cada servidor até ter sucesso
    data = None
    for server in overpass_servers:
        try:
            print(f"Tentando baixar dados via {server}...")
            response = requests.get(server, params={'data': overpass_query}, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                print(f"Sucesso ao baixar dados de {server}")
                break
            else:
                print(f"Falha ao baixar dados de {server}: {response.status_code}")
        
        except Exception as e:
            print(f"Erro ao tentar {server}: {str(e)}")
        
        # Aguardar um pouco antes de tentar o próximo servidor
        time.sleep(1)
    
    if not data:
        return "Erro: Não foi possível obter dados de nenhum servidor Overpass."
    
    # Extrair nós e vias
    nodes = {}
    for element in data['elements']:
        if element['type'] == 'node':
            nodes[element['id']] = (element['lat'], element['lon'])
    
    # Criar um grafo direcionado
    G = nx.DiGraph()
    
    # Adicionar nós ao grafo
    for node_id, (lat, lon) in nodes.items():
        G.add_node(node_id, y=lat, x=lon)
    
    # Função para calcular a distância entre dois pontos
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371  # raio da Terra em km
        dLat = math.radians(lat2 - lat1)
        dLon = math.radians(lon2 - lon1)
        a = math.sin(dLat/2) * math.sin(dLat/2) + \
            math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
            math.sin(dLon/2) * math.sin(dLon/2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        return distance * 1000  # em metros
    
    # Dicionário para armazenar metadados das vias
    ways_metadata = {}
    
    # Primeiro passo: coletar metadados de todas as vias
    for element in data['elements']:
        if element['type'] == 'way':
            way_id = element['id']
            way_tags = element.get('tags', {})
            
            ways_metadata[way_id] = {
                'name': way_tags.get('name', "Estrada sem nome"),
                'highway': way_tags.get('highway', "road"),
                'oneway': way_tags.get('oneway') == 'yes',
                'nodes': element['nodes'],
                'distance': float(way_tags.get('distance', 0)),  # Usar se disponível
                'maxspeed': way_tags.get('maxspeed', ''),
                'lanes': way_tags.get('lanes', '1'),
                'ref': way_tags.get('ref', '')  # Referência da via (útil para rodovias)
            }
    
    # Segundo passo: adicionar arestas ao grafo
    for way_id, metadata in ways_metadata.items():
        way_nodes = metadata['nodes']
        is_oneway = metadata['oneway']
        name = metadata['name']
        highway_type = metadata['highway']
        ref = metadata['ref']
        
        # Combinar nome e referência se ambos existirem
        if ref and name != "Estrada sem nome":
            display_name = f"{name} ({ref})"
        elif ref:
            display_name = ref
        else:
            display_name = name
        
        # Se a via tem um comprimento total, calcular comprimento proporcional por segmento
        total_way_length = metadata['distance']
        total_calculated_length = 0
        
        # Calcular comprimento total da via usando haversine para comparação
        if total_way_length == 0 and len(way_nodes) > 1:
            segment_lengths = []
            for i in range(len(way_nodes) - 1):
                node1_id = way_nodes[i]
                node2_id = way_nodes[i + 1]
                
                if node1_id in nodes and node2_id in nodes:
                    node1_lat, node1_lon = nodes[node1_id]
                    node2_lat, node2_lon = nodes[node2_id]
                    
                    segment_length = haversine(node1_lat, node1_lon, node2_lat, node2_lon)
                    segment_lengths.append(segment_length)
                    total_calculated_length += segment_length
        
        # Adicionar cada segmento da via como uma aresta
        for i in range(len(way_nodes) - 1):
            node1_id = way_nodes[i]
            node2_id = way_nodes[i + 1]
            
            if node1_id in nodes and node2_id in nodes:
                node1_lat, node1_lon = nodes[node1_id]
                node2_lat, node2_lon = nodes[node2_id]
                
                # Determinar comprimento do segmento
                if total_way_length > 0 and total_calculated_length > 0:
                    # Se temos o comprimento total da via, calcular proporcionalmente
                    segment_length = haversine(node1_lat, node1_lon, node2_lat, node2_lon)
                    segment_ratio = segment_length / total_calculated_length
                    actual_segment_length = total_way_length * segment_ratio
                else:
                    # Caso contrário, usar cálculo direto
                    actual_segment_length = haversine(node1_lat, node1_lon, node2_lat, node2_lon)
                
                # Adicionar metadados úteis
                edge_data = {
                    'length': actual_segment_length,
                    'name': display_name,
                    'raw_name': name,
                    'ref': ref,
                    'highway': highway_type,
                    'way_id': way_id
                }
                
                # Adicionar aresta em uma direção (de node1 para node2)
                G.add_edge(node1_id, node2_id, **edge_data)
                
                # Se a estrada não for de mão única, adicionar também a aresta na direção oposta
                if not is_oneway:
                    G.add_edge(node2_id, node1_id, **edge_data)
    
    print(f"Grafo criado com {len(G.nodes)} nós e {len(G.edges)} arestas.")
    
    # Verificar se o grafo tem nós suficientes
    if len(G.nodes) < 10:
        return "Erro: Não foram encontradas estradas suficientes na área. Tente aumentar a área de busca."
    
    # Encontrar os nós mais próximos para origem e destino
    origem_node = find_nearest_node(G, origem_lat, origem_lng)
    destino_node = find_nearest_node(G, destino_lat, destino_lng)
    
    if not origem_node or not destino_node:
        return "Erro: Não foi possível encontrar nós próximos para origem ou destino."
    
    print(f"Nó mais próximo da origem: {origem_node}")
    print(f"Nó mais próximo do destino: {destino_node}")
    
    # Calcular a rota mais curta
    print("Calculando a rota mais curta...")
    try:
        rota = nx.shortest_path(G, origem_node, destino_node, weight='length')
        
        # Verificar se a rota tem comprimento adequado
        if len(rota) < 2:
            return "Erro: A rota encontrada é muito curta. Tente aumentar a área de busca."
        
        # Calcular a distância total e gerar instruções de rota agrupadas
        comprimento_rota = 0
        
        # Lista para armazenar os segmentos da rota para processamento posterior
        segmentos_rota = []
        
        # Primeiro, coletar todos os segmentos da rota
        for i in range(len(rota) - 1):
            u = rota[i]
            v = rota[i + 1]
            data = G.get_edge_data(u, v, 0)
            
            comprimento_rota += data['length']
            
            # Armazenar os dados do segmento
            segmentos_rota.append({
                'start_node': u,
                'end_node': v,
                'name': data['name'],
                'raw_name': data['raw_name'],
                'ref': data['ref'],
                'way_id': data['way_id'],
                'length': data['length'],
                'highway': data['highway']
            })
        
        # Agrupar segmentos contíguos com o mesmo nome de rua (não apenas way_id)
        instrucoes = []
        current_name = None
        current_length = 0
        
        for i, segmento in enumerate(segmentos_rota):
            # Verificar se este é um novo nome de rua ou o primeiro segmento
            if i == 0 or segmento['raw_name'] != current_name:
                # Se não é o primeiro segmento, adicionar a instrução para o segmento anterior
                if i > 0:
                    # Buscar o nome formatado do segmento anterior
                    prev_name = segmentos_rota[i-1]['name']
                    instrucoes.append(f"Continue por {int(current_length)} metros em {prev_name}")
                
                # Iniciar novo segmento
                current_name = segmento['raw_name']
                current_length = segmento['length']
            else:
                # Continuamos na mesma rua, acumular distância
                current_length += segmento['length']
        
        # Adicionar o último segmento
        if segmentos_rota:
            last_segment = segmentos_rota[-1]
            instrucoes.append(f"Continue por {int(current_length)} metros em {last_segment['name']}")
        
        # Adicionar destino final
        instrucoes.append(f"Chegue em {destino}")
        
        # Formatar o resultado
        resultado = f"Rota de {origem} para {destino}:\n"
        resultado += f"Distância total: {comprimento_rota/1000:.2f} km\n\n"
        resultado += "Instruções:\n"
        for i, inst in enumerate(instrucoes, 1):
            resultado += f"{i}. {inst}\n"
        
        return resultado
        
    except nx.NetworkXNoPath:
        return "Erro: Não foi possível encontrar uma rota entre os pontos especificados."
    except Exception as e:
        return f"Erro durante o cálculo da rota: {str(e)}"

def find_nearest_node(G, lat, lon):
    """Encontra o nó mais próximo das coordenadas dadas"""
    min_dist = float('inf')
    nearest_node = None
    
    for node, data in G.nodes(data=True):
        if 'y' in data and 'x' in data:
            node_lat = data['y']
            node_lon = data['x']
            
            # Calcular distância
            dist = math.sqrt((lat - node_lat)**2 + (lon - node_lon)**2)
            
            if dist < min_dist:
                min_dist = dist
                nearest_node = node
    
    return nearest_node

if __name__ == "__main__":
    # Definir origem e destino
    origem = "Belo Horizonte"
    destino = "Congonhas"
    
    # Obter e exibir a rota
    resultado = get_route_overpass(origem, destino)
    print("\nResultado da rota:")
    print(resultado)