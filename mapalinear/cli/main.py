import typer
import httpx
import json
from typing import Optional, List, Dict, Any, Callable, Tuple
from rich.console import Console
from rich.table import Table
from rich import print as rprint
import os
from pathlib import Path
import time
from rich.progress import Progress, SpinnerColumn, TextColumn
import sys
import itertools

try:
    # Importar o módulo de operações
    from mapalinear.cli.commands.operations import operations_app
    has_operations_module = True
except ImportError:
    # Se não conseguir importar, desabilite o módulo de operações
    has_operations_module = False

app = typer.Typer(help="CLI para extrair dados do OpenStreetMap e criar mapas lineares de estradas")
console = Console()

# Adicionar o módulo de operações, se disponível
if has_operations_module:
    app.add_typer(operations_app, name="operations", help="Gerenciar operações assíncronas")

# API URL - pode ser configurado através de variável de ambiente
API_URL = os.environ.get("MAPALINEAR_API_URL", "http://localhost:8000/api")

# Função utilitária para iniciar uma operação assíncrona
def start_operation(endpoint: str, data: Dict[str, Any], console: Console) -> Tuple[str, bool]:
    """
    Inicia uma operação assíncrona na API.
    
    Args:
        endpoint: Endpoint da API para iniciar a operação
        data: Dados a serem enviados no payload da operação
        console: Console do Rich para exibição
        
    Returns:
        Tupla com (operation_id, success)
    """
    try:
        console.print("[bold green]Iniciando operação...")
        response = httpx.post(
            f"{API_URL}/operations/{endpoint}",
            json=data,
            timeout=30.0  # Timeout generoso para iniciar a operação
        )
        response.raise_for_status()
        operation = response.json()
        operation_id = operation["operation_id"]
        
        console.print(f"[green]Operação iniciada com ID: [bold]{operation_id}[/]")
        return operation_id, True
    except Exception as e:
        console.print(f"[bold red]Erro ao iniciar operação: {str(e)}")
        return "", False


# Função utilitária para fazer polling de operações com animação de cursor
def wait_for_operation(operation_id: str, message: str, console: Console, poll_interval: int = 3) -> Dict[str, Any]:
    """
    Aguarda a conclusão de uma operação assíncrona com animação de cursor.
    
    Args:
        operation_id: ID da operação a ser monitorada
        message: Mensagem a ser exibida durante o polling
        console: Console do Rich para exibição
        poll_interval: Intervalo em segundos entre polls para a API
        
    Returns:
        Dados da operação concluída
    """
    # Indicação clara de início da operação
    console.print(f"[bold green]{message}")
    
    # Configuração para o cursor animado
    cursor_width = 30
    cursor_position = 0
    cursor_direction = 1  # 1 = direita, -1 = esquerda
    animation_chars = list("▮" + "▯"*(cursor_width-1))
    
    # Controle de polling
    last_poll_time = 0
    op_status = None
    
    try:
        console.show_cursor(False)  # Esconde o cursor do terminal
        
        # Loop de polling com animação de cursor
        while True:
            current_time = time.time()
            
            # Verificar se é hora de fazer polling (a cada poll_interval segundos)
            if current_time - last_poll_time >= poll_interval or op_status is None:
                try:
                    # Verificar status da operação
                    status_response = httpx.get(f"{API_URL}/operations/{operation_id}")
                    status_response.raise_for_status()
                    op_status = status_response.json()
                    last_poll_time = current_time
                    
                    if op_status["status"] != "in_progress":
                        break
                except Exception:
                    # Silenciosamente ignora erros de polling
                    pass
            
            # Atualizar posição do cursor (movimento)
            cursor_position += cursor_direction
            if cursor_position >= cursor_width-1:
                cursor_direction = -1
            elif cursor_position <= 0:
                cursor_direction = 1
            
            # Atualizar animação
            animation_chars = ["▯"] * cursor_width
            animation_chars[cursor_position] = "▮"
            
            # Mostrar a barra com movimento de vai e vem
            print(f"\r[{''.join(animation_chars)}]", end="", flush=True)
            
            # Pausa curta para animação fluida
            time.sleep(0.2)
        
        # Limpar a linha após concluir
        print("\r" + " " * (cursor_width + 3), end="\r", flush=True)
        
    finally:
        console.show_cursor(True)  # Certifica-se de restaurar o cursor
    
    return op_status


@app.command()
def search(
    origin: str = typer.Argument(..., help="Local de origem (ex: 'São Paulo, SP')"),
    destination: str = typer.Argument(..., help="Local de destino (ex: 'Rio de Janeiro, RJ')"),
    road_type: str = typer.Option("all", help="Tipo de estrada (highway, motorway, trunk, primary, secondary, all)"),
    output_file: Optional[Path] = typer.Option(None, help="Arquivo para salvar os resultados em JSON"),
    no_wait: bool = typer.Option(False, help="Não aguardar a conclusão da operação, apenas retornar o ID da tarefa"),
):
    """
    Busca estradas entre dois pontos no OpenStreetMap.
    """
    request_data = {
        "origin": origin,
        "destination": destination,
        "road_type": road_type
    }
    
    # Iniciar operação assíncrona
    operation_id, success = start_operation("osm-search", request_data, console)
    if not success:
        return None
    
    if no_wait:
        console.print("[green]Use o comando [bold]operations status " + operation_id + "[/] para verificar o progresso.")
        return operation_id
    
    # Aguardar a conclusão da operação com animação
    message = f"Buscando estradas entre [cyan]{origin}[/] e [cyan]{destination}[/]..."
    op_status = wait_for_operation(operation_id, message, console)
        
    if op_status["status"] == "completed":
        data = op_status["result"]
        # Mostrar resultados
        # Extract key information for display
        total_segments = len(data["road_segments"])
        total_length = data["total_length_km"]
        road_id = data["road_id"]
        
        # Print summary information
        console.print(f"\n[bold]Rota de [cyan]{origin}[/] para [cyan]{destination}[/]")
        console.print(f"Total de segmentos: [cyan]{total_segments}[/]")
        console.print(f"Comprimento total: [cyan]{total_length:.2f} km[/]")
        console.print(f"ID da estrada: [cyan]{road_id}[/]")
        
        # Create a table of segments
        table = Table(show_header=True, header_style="bold green")
        table.add_column("Segmento")
        table.add_column("Nome")
        table.add_column("Tipo")
        table.add_column("Referência")
        table.add_column("Comprimento (km)")
        
        for i, segment in enumerate(data["road_segments"]):
            table.add_row(
                str(i + 1),
                segment["name"] or "-",
                segment["highway_type"],
                segment["ref"] or "-",
                f"{segment['length_meters'] / 1000:.2f}"
            )
        
        console.print(table)
        
        # Save to file if requested
        if output_file:
            with open(output_file, "w") as f:
                json.dump(data, f, indent=2)
            console.print(f"[green]Resultados salvos em [bold]{output_file}[/]")
        
        return road_id
    else:
        console.print(f"[bold red]Falha na operação: {op_status.get('error', 'Erro desconhecido')}")
        return None


@app.command()
def generate_map(
    origin: str = typer.Argument(..., help="Local de origem (ex: 'São Paulo, SP')"),
    destination: str = typer.Argument(..., help="Local de destino (ex: 'Rio de Janeiro, RJ')"),
    road_id: Optional[str] = typer.Option(None, help="ID da estrada (opcional, se já conhecida)"),
    include_cities: bool = typer.Option(True, help="Incluir cidades como marcos"),
    include_gas_stations: bool = typer.Option(True, help="Incluir postos de gasolina como marcos"),
    include_restaurants: bool = typer.Option(False, help="Incluir restaurantes como marcos"),
    include_toll_booths: bool = typer.Option(True, help="Incluir pedágios como marcos"),
    max_distance: float = typer.Option(1000, help="Distância máxima em metros da estrada para incluir pontos de interesse"),
    output_file: Optional[Path] = typer.Option(None, help="Arquivo para salvar os resultados em JSON"),
    no_wait: bool = typer.Option(False, help="Não aguardar a conclusão da operação, apenas retornar o ID da tarefa"),
):
    """
    Gera um mapa linear de uma estrada entre pontos de origem e destino.
    """
    request_data = {
        "origin": origin,
        "destination": destination,
        "road_id": road_id,
        "include_cities": include_cities,
        "include_gas_stations": include_gas_stations,
        "include_restaurants": include_restaurants,
        "include_toll_booths": include_toll_booths,
        "max_distance_from_road": max_distance
    }
    
    # Iniciar operação assíncrona
    operation_id, success = start_operation("linear-map", request_data, console)
    if not success:
        return None
    
    if no_wait:
        console.print("[green]Use o comando [bold]operations status " + operation_id + "[/] para verificar o progresso.")
        return operation_id
    
    # Aguardar a conclusão da operação com animação
    message = f"Gerando mapa linear entre [cyan]{origin}[/] e [cyan]{destination}[/]..."
    op_status = wait_for_operation(operation_id, message, console)
        
    if op_status["status"] == "completed":
        data = op_status["result"]
        
        # Extract key information for display
        map_id = data["id"]
        total_length = data["total_length_km"]
        num_segments = len(data["segments"])
        num_milestones = len(data["milestones"])
        
        # Print summary information
        console.print(f"\n[bold]Mapa linear de [cyan]{origin}[/] para [cyan]{destination}[/]")
        console.print(f"ID do mapa: [cyan]{map_id}[/]")
        console.print(f"Comprimento total: [cyan]{total_length:.2f} km[/]")
        console.print(f"Número de segmentos: [cyan]{num_segments}[/]")
        console.print(f"Número de marcos: [cyan]{num_milestones}[/]")
        
        # Create a table of milestones
        table = Table(show_header=True, header_style="bold green")
        table.add_column("Km")
        table.add_column("Marco")
        table.add_column("Tipo")
        table.add_column("Lado")
        
        # Sort milestones by distance
        milestones = sorted(data["milestones"], key=lambda m: m["distance_from_origin_km"])
        
        for milestone in milestones:
            table.add_row(
                f"{milestone['distance_from_origin_km']:.1f}",
                milestone["name"],
                milestone["type"],
                milestone["side"]
            )
        
        console.print(table)
        
        # Save to file if requested
        if output_file:
            with open(output_file, "w") as f:
                json.dump(data, f, indent=2)
            console.print(f"[green]Mapa salvo em [bold]{output_file}[/]")
        
        return map_id
    else:
        console.print(f"[bold red]Falha na operação: {op_status.get('error', 'Erro desconhecido')}")
        return None


@app.command()
def list_maps():
    """
    Lista todos os mapas salvos.
    """
    with console.status("[bold green]Buscando mapas salvos..."):
        try:
            response = httpx.get(f"{API_URL}/roads/saved-maps")
            response.raise_for_status()
            maps = response.json()
            
            if not maps:
                console.print("[yellow]Nenhum mapa encontrado.")
                return
            
            table = Table(show_header=True, header_style="bold green")
            table.add_column("ID")
            table.add_column("Origem")
            table.add_column("Destino")
            table.add_column("Distância (km)")
            table.add_column("Marcos")
            table.add_column("Data de Criação")
            
            for map_data in maps:
                table.add_row(
                    map_data["id"],
                    map_data["origin"],
                    map_data["destination"],
                    f"{map_data['total_length_km']:.2f}",
                    str(map_data["milestone_count"]),
                    map_data["creation_date"]
                )
            
            console.print(table)
            
        except httpx.HTTPStatusError as e:
            console.print(f"[bold red]Erro HTTP: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            console.print(f"[bold red]Erro de requisição: {str(e)}")
        except Exception as e:
            console.print(f"[bold red]Erro: {str(e)}")


@app.command()
def get_map(map_id: str = typer.Argument(..., help="ID do mapa a ser exibido")):
    """
    Exibe detalhes de um mapa específico.
    """
    with console.status(f"[bold green]Buscando mapa {map_id}..."):
        try:
            response = httpx.get(f"{API_URL}/roads/saved-maps/{map_id}")
            response.raise_for_status()
            map_data = response.json()
            
            console.print(f"\n[bold]Mapa [cyan]{map_id}[/]")
            console.print(f"Origem: [cyan]{map_data['origin']}[/]")
            console.print(f"Destino: [cyan]{map_data['destination']}[/]")
            console.print(f"Distância total: [cyan]{map_data['total_length_km']:.2f} km[/]")
            console.print(f"Número de marcos: [cyan]{map_data['milestone_count']}[/]")
            console.print(f"Data de criação: [cyan]{map_data['creation_date']}[/]")
            
            if map_data["road_refs"]:
                console.print(f"Referências: [cyan]{', '.join(map_data['road_refs'])}[/]")
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                console.print(f"[bold red]Mapa com ID {map_id} não encontrado.")
            else:
                console.print(f"[bold red]Erro HTTP: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            console.print(f"[bold red]Erro de requisição: {str(e)}")
        except Exception as e:
            console.print(f"[bold red]Erro: {str(e)}")


def main():
    app()


if __name__ == "__main__":
    main() 