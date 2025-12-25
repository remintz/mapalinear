import Link from 'next/link';
import { Button } from '@/components/ui';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { Badge } from '@/components/ui/badge';

export default function Home() {
  return (
    <div className="container mx-auto px-4 py-12">
      <div className="max-w-6xl mx-auto">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <Badge className="mb-4 bg-blue-100 text-blue-800 border-blue-200">
            Powered by OpenStreetMap
          </Badge>
          <h1 className="text-5xl md:text-7xl font-bold text-gray-900 mb-6">
            Seu Auxílio nas{' '}
            <span className="text-blue-600">Estradas</span>
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
            Planeje suas viagens pelas estradas brasileiras com pontos de interesse organizados por distância.
            Encontre postos, restaurantes, cidades e muito mais ao longo do caminho.
          </p>
          <div className="flex gap-4 justify-center">
            <Link href="/search">
              <Button size="lg" className="text-lg px-8 py-4">
                🗺️ Criar Mapa Agora
              </Button>
            </Link>
            <Link href="/maps">
              <Button size="lg" variant="outline" className="text-lg px-8 py-4">
                📂 Meus Mapas
              </Button>
            </Link>
          </div>
        </div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-16">
          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className="text-2xl">⛽</span>
                <span>Postos de Combustível</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600 text-sm">
                Localize postos com informações de marca, lado da pista e distância exata do ponto de partida.
              </p>
            </CardContent>
          </Card>

          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className="text-2xl">🍽️</span>
                <span>Restaurantes e Cafés</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600 text-sm">
                Encontre opções de alimentação, incluindo restaurantes, lanchonetes e cafés próximos à rota.
              </p>
            </CardContent>
          </Card>

          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className="text-2xl">🏙️</span>
                <span>Cidades e Vilas</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600 text-sm">
                Visualize cidades, vilas e povoados ao longo da rota com raio de busca otimizado.
              </p>
            </CardContent>
          </Card>

          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className="text-2xl">💰</span>
                <span>Pedágios</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600 text-sm">
                Identifique todos os pedágios no percurso para planejar os custos da viagem.
              </p>
            </CardContent>
          </Card>

          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className="text-2xl">🏨</span>
                <span>Hotéis e Camping</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600 text-sm">
                Encontre opções de hospedagem para viagens longas, incluindo hotéis e áreas de camping.
              </p>
            </CardContent>
          </Card>

          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className="text-2xl">🏥</span>
                <span>Serviços Essenciais</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600 text-sm">
                Hospitais, delegacias e outros serviços essenciais para emergências.
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Key Features */}
        <div className="mb-16">
          <h2 className="text-3xl font-bold text-center mb-10">Recursos Principais</h2>
          <div className="grid md:grid-cols-1 gap-8 max-w-2xl mx-auto">
            <Card className="border-blue-200 bg-blue-50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-blue-900">
                  <span className="text-2xl">💾</span>
                  Mapas Salvos
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-blue-800 mb-4">
                  Todos os mapas criados são automaticamente salvos e podem ser acessados a qualquer momento.
                </p>
                <ul className="text-sm text-blue-700 space-y-2">
                  <li>✓ Salvamento automático</li>
                  <li>✓ Abertura instantânea</li>
                  <li>✓ Gerenciamento simplificado</li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* CTA Section */}
        <Card className="bg-gradient-to-r from-blue-600 to-blue-700 border-0 text-white">
          <CardContent className="py-12 text-center">
            <h2 className="text-3xl font-bold mb-4">
              Pronto para Planejar sua Viagem?
            </h2>
            <p className="text-blue-100 mb-8 text-lg max-w-2xl mx-auto">
              Crie seu primeiro mapa agora e descubra tudo que existe ao longo do caminho.
              É rápido, fácil e completamente gratuito!
            </p>
            <div className="flex gap-4 justify-center">
              <Link href="/search">
                <Button size="lg" variant="secondary" className="text-lg px-8 py-4">
                  Começar Agora →
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>

        {/* Footer Info */}
        <div className="text-center mt-12 text-gray-500 text-sm space-y-1">
          <p>
            OraPOIS utiliza dados do{' '}
            <a href="https://www.openstreetmap.org" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
              OpenStreetMap
            </a>
            {' '}© OpenStreetMap contributors
          </p>
          <p className="text-xs text-gray-400">© MTZ</p>
        </div>
      </div>
    </div>
  );
}
