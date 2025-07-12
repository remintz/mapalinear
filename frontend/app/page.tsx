import Link from 'next/link';
import { Button } from '@/components/ui';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui';

export default function Home() {
  return (
    <div className="container mx-auto px-4 py-12">
      <div className="max-w-4xl mx-auto text-center">
        {/* Hero Section */}
        <div className="mb-12">
          <h1 className="text-4xl md:text-6xl font-bold text-gray-900 mb-6">
            Mapas Lineares para suas{' '}
            <span className="text-blue-600">Viagens</span>
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
            Descubra postos de combustível, restaurantes e pedágios ao longo da sua rota.
            Visualize sua viagem de forma linear e planeje suas paradas.
          </p>
          <Link href="/search">
            <Button size="lg" className="text-lg px-8 py-4">
              🛣️ Criar Mapa Linear
            </Button>
          </Link>
        </div>

        {/* Features Section */}
        <div className="grid md:grid-cols-3 gap-8 mb-12">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-center mb-4">
                ⛽ <span className="ml-2">Postos de Combustível</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">
                Encontre postos de combustível ao longo da sua rota com informações 
                sobre localização e distância.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-center mb-4">
                🍽️ <span className="ml-2">Restaurantes</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">
                Descubra opções de alimentação próximas à rodovia para 
                fazer suas refeições durante a viagem.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-center mb-4">
                🛣️ <span className="ml-2">Pedágios</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">
                Visualize a localização dos pedágios para se preparar 
                financeiramente para sua viagem.
              </p>
            </CardContent>
          </Card>
        </div>

        {/* CTA Section */}
        <Card variant="elevated" className="bg-blue-50 border-blue-200">
          <CardContent className="py-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              Pronto para começar?
            </h2>
            <p className="text-gray-600 mb-6">
              Digite sua origem e destino para criar seu mapa linear personalizado.
            </p>
            <Link href="/search">
              <Button variant="primary" size="lg">
                Começar Agora
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
