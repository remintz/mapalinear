import typer
import httpx
import json
import time
from typing import Optional, List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich import print as rprint
import os

operations_app = typer.Typer(help="Gerenciar operações assíncronas")
console = Console()

# API URL - pode ser configurado através de variável de ambiente
API_URL = os.environ.get("MAPALINEAR_API_URL", "http://localhost:8000/api")

@operations_app.command()
def status(
    operation_id: str = typer.Argument(..., help="ID da operação para verificar"),
    wait: bool = typer.Option(False, help="Aguardar a conclusão da operação"),
    timeout: int = typer.Option(600, help="Tempo máximo de espera em segundos (0 para esperar indefinidamente)"),
    interval: int = typer.Option(5, help="Intervalo entre verificações de status em segundos"),
    output_file: Optional[str] = typer.Option(None, help="Salvar resultado da operação em arquivo (apenas para operações completadas)"),
):
    """
    Verifica o status de uma operação assíncrona.
    """
    try:
        if wait:
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold green]Aguardando conclusão da operação..."),
                transient=True,
            ) as progress:
                task = progress.add_task("Aguardando...", total=None)
                
                start_time = time.time()
                while True:
                    response = httpx.get(f"{API_URL}/operations/{operation_id}")
                    response.raise_for_status()
                    operation = response.json()
                    
                    if operation["status"] != "in_progress":
                        break
                    
                    elapsed = time.time() - start_time
                    if timeout > 0 and elapsed > timeout:
                        console.print(f"[bold red]Timeout após {timeout} segundos!")
                        return
                    
                    progress.update(task, description=f"[bold green]Operação em andamento: {operation['progress_percent']:.1f}%")
                    time.sleep(interval)
        else:
            with console.status("[bold green]Verificando status da operação..."):
                response = httpx.get(f"{API_URL}/operations/{operation_id}")
                response.raise_for_status()
                operation = response.json()
        
        # Exibir detalhes da operação
        console.print(f"\n[bold]Operação [cyan]{operation['operation_id']}[/]")
        
        status_color = {
            "in_progress": "yellow",
            "completed": "green",
            "failed": "red"
        }.get(operation["status"], "white")
        
        console.print(f"Status: [{status_color}]{operation['status']}[/]")
        console.print(f"Tipo: [cyan]{operation['type']}[/]")
        console.print(f"Iniciada: [cyan]{operation['started_at']}[/]")
        
        if operation["progress_percent"] > 0:
            console.print(f"Progresso: [cyan]{operation['progress_percent']:.1f}%[/]")
            
        if operation["estimated_completion"]:
            console.print(f"Conclusão estimada: [cyan]{operation['estimated_completion']}[/]")
            
        if operation["status"] == "completed" and operation["result"]:
            console.print("\n[bold green]Resultado da operação:[/]")
            
            # Salvar resultado em arquivo se solicitado
            if output_file and operation["result"]:
                with open(output_file, "w") as f:
                    json.dump(operation["result"], f, indent=2)
                console.print(f"[green]Resultado salvo em [bold]{output_file}[/]")
            else:
                # Mostrar resumo do resultado de acordo com o tipo de operação
                if operation["type"] == "linear_map":
                    result = operation["result"]
                    console.print(f"Mapa linear de [cyan]{result.get('origin')}[/] para [cyan]{result.get('destination')}[/]")
                    console.print(f"ID do mapa: [cyan]{result.get('id')}[/]")
                    console.print(f"Comprimento total: [cyan]{result.get('total_length_km'):.2f} km[/]")
                    console.print(f"Marcos: [cyan]{len(result.get('milestones', []))}[/]")
                    console.print("[green]Para ver o mapa completo, use o comando: [bold]get_map " + result.get('id') + "[/]")
                elif operation["type"] == "osm_search":
                    result = operation["result"]
                    console.print(f"Busca OSM de [cyan]{result.get('origin')}[/] para [cyan]{result.get('destination')}[/]")
                    console.print(f"ID da estrada: [cyan]{result.get('road_id')}[/]")
                    console.print(f"Comprimento total: [cyan]{result.get('total_length_km'):.2f} km[/]")
                    console.print(f"Segmentos: [cyan]{len(result.get('road_segments', []))}[/]")
                else:
                    # Para outros tipos, mostrar um resumo genérico
                    console.print(operation["result"])
            
        if operation["status"] == "failed" and operation["error"]:
            console.print(f"\n[bold red]Erro: {operation['error']}[/]")
            
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print(f"[bold red]Operação com ID {operation_id} não encontrada.")
        else:
            console.print(f"[bold red]Erro HTTP: {e.response.status_code} - {e.response.text}")
    except httpx.RequestError as e:
        console.print(f"[bold red]Erro de requisição: {str(e)}")
    except Exception as e:
        console.print(f"[bold red]Erro: {str(e)}")

@operations_app.command()
def list(
    all: bool = typer.Option(False, help="Listar todas as operações (incluindo concluídas e falhas)"),
    limit: int = typer.Option(10, help="Número máximo de operações a exibir"),
):
    """
    Lista operações assíncronas.
    """
    with console.status("[bold green]Buscando operações..."):
        try:
            response = httpx.get(f"{API_URL}/operations?active_only={not all}")
            response.raise_for_status()
            operations = response.json()
            
            if not operations:
                state = "ativas" if not all else ""
                console.print(f"[yellow]Nenhuma operação {state} encontrada.")
                return
            
            # Limitar número de operações exibidas
            operations = operations[:limit]
            
            table = Table(show_header=True, header_style="bold green")
            table.add_column("ID")
            table.add_column("Tipo")
            table.add_column("Status")
            table.add_column("Progresso")
            table.add_column("Iniciada em")
            
            for op in operations:
                status_color = {
                    "in_progress": "yellow",
                    "completed": "green",
                    "failed": "red"
                }.get(op["status"], "white")
                
                table.add_row(
                    op["operation_id"],
                    op["type"],
                    f"[{status_color}]{op['status']}[/]",
                    f"{op['progress_percent']:.1f}%" if op['progress_percent'] else "-",
                    op["started_at"]
                )
            
            console.print(table)
            
            # Instruções úteis
            if any(op["status"] == "in_progress" for op in operations):
                console.print("\n[yellow]Dica: Use [bold]operations status <id>[/] para verificar o progresso de uma operação específica.")
            
            if all and len(operations) >= limit:
                console.print(f"\n[yellow]Mostrando apenas {limit} operações. Use --limit para ver mais.")
                
        except httpx.HTTPStatusError as e:
            console.print(f"[bold red]Erro HTTP: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            console.print(f"[bold red]Erro de requisição: {str(e)}")
        except Exception as e:
            console.print(f"[bold red]Erro: {str(e)}")

@operations_app.command()
def cancel(operation_id: str = typer.Argument(..., help="ID da operação a ser cancelada")):
    """
    Cancela uma operação em andamento.
    """
    with console.status("[bold yellow]Cancelando operação..."):
        try:
            response = httpx.delete(f"{API_URL}/operations/{operation_id}")
            response.raise_for_status()
            result = response.json()
            
            console.print(f"[green]{result['message']}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                console.print(f"[bold red]Operação com ID {operation_id} não encontrada.")
            elif e.response.status_code == 400:
                console.print(f"[bold red]Erro: {e.response.json().get('detail', 'A operação não pode ser cancelada.')}")
            else:
                console.print(f"[bold red]Erro HTTP: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            console.print(f"[bold red]Erro de requisição: {str(e)}")
        except Exception as e:
            console.print(f"[bold red]Erro: {str(e)}")

@operations_app.command()
def cleanup(max_age_hours: int = typer.Option(24, help="Idade máxima em horas para manter operações")):
    """
    Limpa operações antigas do sistema.
    """
    with console.status("[bold yellow]Limpando operações antigas..."):
        try:
            response = httpx.delete(f"{API_URL}/operations?max_age_hours={max_age_hours}")
            response.raise_for_status()
            result = response.json()
            
            console.print(f"[green]{result['message']}")
        except httpx.HTTPStatusError as e:
            console.print(f"[bold red]Erro HTTP: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            console.print(f"[bold red]Erro de requisição: {str(e)}")
        except Exception as e:
            console.print(f"[bold red]Erro: {str(e)}") 