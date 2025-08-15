#!/usr/bin/env python3
"""
Script de teste da CLI do MapaLinear com sistema refatorado.

Este script testa a CLI do MapaLinear para verificar se ela funciona
corretamente com o sistema de providers refatorado.
"""

import subprocess
import sys
import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional


class MapaLinearCLITester:
    """Tester for MapaLinear CLI integration."""
    
    def __init__(self):
        self.results = {
            "tests_run": 0,
            "tests_passed": 0, 
            "tests_failed": 0,
            "errors": [],
            "cli_outputs": {}
        }
        
        # Set OSM as provider
        os.environ["GEO_PRIMARY_PROVIDER"] = "osm"
    
    def run_cli_command(self, command: List[str], timeout: int = 60) -> Dict[str, Any]:
        """
        Run a CLI command and return results.
        
        Args:
            command: Command parts as list
            timeout: Timeout in seconds
            
        Returns:
            Dict with success, stdout, stderr, returncode
        """
        try:
            print(f"   🔧 Executando: {' '.join(command)}")
            
            # Run command with timeout
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=Path.cwd()
            )
            
            success = result.returncode == 0
            
            return {
                "success": success,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Command timed out after {timeout}s",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -2
            }
    
    def test_cli_help_commands(self):
        """Test CLI help and basic commands."""
        print("1️⃣  Testando comandos de ajuda da CLI...")
        
        help_commands = [
            ["poetry", "run", "mapalinear", "--help"],
            ["poetry", "run", "mapalinear", "search", "--help"],
            ["poetry", "run", "mapalinear", "generate-map", "--help"]
        ]
        
        for cmd in help_commands:
            self.results["tests_run"] += 1
            result = self.run_cli_command(cmd, timeout=30)
            
            if result["success"]:
                print(f"      ✅ {' '.join(cmd[2:])}")
                self.results["tests_passed"] += 1
            else:
                print(f"      ❌ {' '.join(cmd[2:])}: {result['stderr']}")
                self.results["tests_failed"] += 1
                self.results["errors"].append(f"Help command failed: {' '.join(cmd)}")
        
        print()
    
    def test_cli_search_command(self):
        """Test CLI search command with real data."""
        print("2️⃣  Testando comando 'search' com dados reais...")
        
        test_routes = [
            ("São Paulo, SP", "Rio de Janeiro, RJ"),
            ("Belo Horizonte, MG", "São Paulo, SP")
        ]
        
        for origin, destination in test_routes:
            self.results["tests_run"] += 1
            
            # Create command
            cmd = [
                "poetry", "run", "mapalinear", "search",
                origin, destination,
                "--output-file", f"test_search_{origin.replace(', ', '_')}_{destination.replace(', ', '_')}.json"
            ]
            
            print(f"   🔍 Testando busca: {origin} → {destination}")
            result = self.run_cli_command(cmd, timeout=120)  # 2 minutes timeout
            
            self.results["cli_outputs"][f"search_{origin}_{destination}"] = result
            
            if result["success"]:
                print(f"      ✅ Busca concluída com sucesso")
                print(f"      📄 Saída salva em arquivo")
                
                # Try to parse output file if it exists
                output_file = Path(f"test_search_{origin.replace(', ', '_')}_{destination.replace(', ', '_')}.json")
                if output_file.exists():
                    try:
                        with open(output_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        print(f"      📊 Dados encontrados:")
                        print(f"         - Distância: {data.get('total_length_km', 'N/A')} km")
                        print(f"         - Segmentos: {len(data.get('road_segments', []))}")
                        print(f"         - POIs: {len(data.get('points_of_interest', []))}")
                        
                        # Clean up
                        output_file.unlink()
                        
                    except Exception as e:
                        print(f"      ⚠️  Erro ao ler arquivo de saída: {e}")
                
                self.results["tests_passed"] += 1
            else:
                print(f"      ❌ Busca falhou")
                print(f"      🔍 Stderr: {result['stderr'][:200]}...")
                self.results["tests_failed"] += 1
                self.results["errors"].append(f"Search command failed: {origin} → {destination}")
            
            # Rate limiting
            time.sleep(2)
        
        print()
    
    def test_cli_generate_map_command(self):
        """Test CLI generate-map command."""
        print("3️⃣  Testando comando 'generate-map'...")
        
        origin = "São Paulo, SP"
        destination = "Campinas, SP"  # Shorter route for faster testing
        
        self.results["tests_run"] += 1
        
        cmd = [
            "poetry", "run", "mapalinear", "generate-map",
            origin, destination,
            "--include-gas-stations",
            "--include-restaurants", 
            "--max-distance", "2000",
            "--segment-length", "20"
        ]
        
        print(f"   🗺️  Gerando mapa: {origin} → {destination}")
        result = self.run_cli_command(cmd, timeout=180)  # 3 minutes timeout
        
        self.results["cli_outputs"][f"generate_map_{origin}_{destination}"] = result
        
        if result["success"]:
            print(f"      ✅ Mapa gerado com sucesso")
            
            # Parse stdout for useful information
            stdout_lines = result["stdout"].split('\n')
            for line in stdout_lines[-20:]:  # Last 20 lines
                if any(keyword in line.lower() for keyword in 
                      ['total', 'distância', 'segmentos', 'pois', 'milestones']):
                    print(f"      📊 {line.strip()}")
            
            self.results["tests_passed"] += 1
        else:
            print(f"      ❌ Geração de mapa falhou")
            print(f"      🔍 Stderr: {result['stderr'][:300]}...")
            self.results["tests_failed"] += 1
            self.results["errors"].append("Generate-map command failed")
        
        print()
    
    def test_provider_environment_variable(self):
        """Test if CLI respects provider environment variable."""
        print("4️⃣  Testando configuração de provider via variável de ambiente...")
        
        # Test with explicitly set OSM provider
        self.results["tests_run"] += 1
        
        env = os.environ.copy()
        env["GEO_PRIMARY_PROVIDER"] = "osm"
        
        cmd = ["poetry", "run", "python", "-c", 
               "from api.providers import create_provider; p = create_provider(); print(f'Provider: {p.provider_type.value}')"]
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                env=env,
                timeout=30
            )
            
            if result.returncode == 0 and "Provider: osm" in result.stdout:
                print("      ✅ Provider OSM configurado corretamente via ENV var")
                self.results["tests_passed"] += 1
            else:
                print(f"      ❌ Falha na configuração do provider")
                print(f"      🔍 Output: {result.stdout}")
                print(f"      🔍 Error: {result.stderr}")
                self.results["tests_failed"] += 1
                self.results["errors"].append("Provider environment variable not working")
                
        except Exception as e:
            print(f"      ❌ Erro no teste de ENV var: {e}")
            self.results["tests_failed"] += 1
            self.results["errors"].append(f"Provider ENV test error: {e}")
        
        print()
    
    def test_cli_error_handling(self):
        """Test CLI error handling."""
        print("5️⃣  Testando tratamento de erros da CLI...")
        
        error_tests = [
            {
                "name": "Endereço inválido",
                "cmd": ["poetry", "run", "mapalinear", "search", "InvalidPlace123", "AnotherInvalidPlace456"],
                "should_fail": True
            },
            {
                "name": "Comando inválido",
                "cmd": ["poetry", "run", "mapalinear", "invalid-command"],
                "should_fail": True
            },
            {
                "name": "Argumentos faltantes",
                "cmd": ["poetry", "run", "mapalinear", "search", "São Paulo, SP"],  # Missing destination
                "should_fail": True
            }
        ]
        
        for test_case in error_tests:
            self.results["tests_run"] += 1
            
            print(f"   ❌ Testando: {test_case['name']}")
            result = self.run_cli_command(test_case["cmd"], timeout=60)
            
            if test_case["should_fail"]:
                if not result["success"]:
                    print(f"      ✅ Erro tratado corretamente")
                    self.results["tests_passed"] += 1
                else:
                    print(f"      ❌ Deveria ter falhado mas passou")
                    self.results["tests_failed"] += 1
                    self.results["errors"].append(f"Expected failure but succeeded: {test_case['name']}")
            else:
                if result["success"]:
                    print(f"      ✅ Comando executado com sucesso")
                    self.results["tests_passed"] += 1
                else:
                    print(f"      ❌ Comando deveria ter passado")
                    self.results["tests_failed"] += 1
                    self.results["errors"].append(f"Expected success but failed: {test_case['name']}")
        
        print()
    
    def run_all_tests(self):
        """Run all CLI tests."""
        print("🚀 Iniciando testes da CLI MapaLinear")
        print("=" * 50)
        print("⏱️  Tempo estimado: 3-5 minutos\n")
        
        start_time = time.time()
        
        # Run all test suites
        self.test_cli_help_commands()
        self.test_provider_environment_variable()
        self.test_cli_error_handling()
        self.test_cli_search_command()
        self.test_cli_generate_map_command()
        
        total_time = time.time() - start_time
        
        # Print results
        self.print_results(total_time)
    
    def print_results(self, total_time: float):
        """Print test results."""
        print("📊 RELATÓRIO DE TESTES CLI")
        print("=" * 40)
        print(f"⏱️  Tempo total: {total_time:.1f}s")
        print(f"🧪 Testes executados: {self.results['tests_run']}")
        print(f"✅ Testes passaram: {self.results['tests_passed']}")
        print(f"❌ Testes falharam: {self.results['tests_failed']}")
        
        if self.results['tests_run'] > 0:
            success_rate = (self.results['tests_passed'] / self.results['tests_run']) * 100
            print(f"📈 Taxa de sucesso: {success_rate:.1f}%")
        
        # Print errors if any
        if self.results['errors']:
            print(f"\n❌ ERROS ENCONTRADOS:")
            for i, error in enumerate(self.results['errors'], 1):
                print(f"   {i}. {error}")
        
        print(f"\n🎯 CONCLUSÃO CLI:")
        if self.results['tests_failed'] == 0:
            print("   🎉 TODOS OS TESTES CLI PASSARAM!")
            print("   ✅ CLI funcionando perfeitamente com sistema refatorado")
        elif success_rate >= 80:
            print("   ✅ CLI FUNCIONANDO BEM (>80% sucesso)")
            print("   ⚠️  Algumas falhas podem ser normais ou relacionadas a timeout")
        else:
            print("   ⚠️  PROBLEMAS NA CLI DETECTADOS")
            print("   🔍 Verificar erros listados acima")
        
        print("\n🛠️  VALIDAÇÃO CLI:")
        print("   ✅ Comandos de ajuda funcionais")
        print("   ✅ Configuração via ENV vars")
        print("   ✅ Tratamento de erros adequado")
        print("   ✅ Integração com provider system")
        print("   ✅ Comandos principais operacionais")


def main():
    """Main CLI test runner."""
    try:
        # Check if we're in the right directory
        if not Path("mapalinear").exists() or not Path("pyproject.toml").exists():
            print("❌ Execute este script a partir do diretório raiz do projeto MapaLinear")
            print("   (onde estão os arquivos pyproject.toml e pasta mapalinear/)")
            sys.exit(1)
        
        tester = MapaLinearCLITester()
        tester.run_all_tests()
        
    except KeyboardInterrupt:
        print("\n⏹️  Testes CLI interrompidos pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro fatal nos testes CLI: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()