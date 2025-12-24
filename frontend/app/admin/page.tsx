"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Users, Settings, Shield, UserX } from "lucide-react";
import { toast } from "sonner";

const SIMULATE_USER_KEY = 'mapalinear_simulate_user';

export default function AdminPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [isSimulatingUser, setIsSimulatingUser] = useState(false);

  // Initialize from sessionStorage on mount
  useEffect(() => {
    const stored = sessionStorage.getItem(SIMULATE_USER_KEY);
    if (stored === 'true') {
      setIsSimulatingUser(true);
    }
  }, []);

  const handleSimulateUserToggle = () => {
    if (isSimulatingUser) {
      // Cannot disable via toggle - must logout
      toast.warning('Faça logout e login novamente para restaurar privilégios de administrador.');
      return;
    }
    setIsSimulatingUser(true);
    sessionStorage.setItem(SIMULATE_USER_KEY, 'true');
    toast.info('Modo usuário comum ativado. Faça logout para restaurar privilégios de admin.');
  };

  useEffect(() => {
    if (status === "loading") return;

    if (!session?.user?.isAdmin) {
      router.push("/");
    }
  }, [session, status, router]);

  if (status === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!session?.user?.isAdmin) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Shield className="w-8 h-8 text-blue-600" />
            Administração
          </h1>
          <p className="mt-2 text-gray-600">
            Gerencie usuários e configurações do sistema
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <Link
            href="/admin/users"
            className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-100 rounded-lg">
                <Users className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Usuários</h2>
                <p className="text-sm text-gray-500">
                  Gerenciar usuários e permissões
                </p>
              </div>
            </div>
          </Link>

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 opacity-50 cursor-not-allowed">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-gray-100 rounded-lg">
                <Settings className="w-6 h-6 text-gray-400" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-400">Configurações</h2>
                <p className="text-sm text-gray-400">
                  Em breve
                </p>
              </div>
            </div>
          </div>

          {/* Simulate User Card */}
          <div
            onClick={handleSimulateUserToggle}
            className={`bg-white rounded-lg shadow-sm border p-6 cursor-pointer transition-all ${
              isSimulatingUser
                ? 'border-orange-300 bg-orange-50'
                : 'border-gray-200 hover:shadow-md'
            }`}
          >
            <div className="flex items-center gap-4">
              <div className={`p-3 rounded-lg ${isSimulatingUser ? 'bg-orange-100' : 'bg-purple-100'}`}>
                <UserX className={`w-6 h-6 ${isSimulatingUser ? 'text-orange-600' : 'text-purple-600'}`} />
              </div>
              <div className="flex-1">
                <h2 className={`text-lg font-semibold ${isSimulatingUser ? 'text-orange-900' : 'text-gray-900'}`}>
                  Simular Usuário Comum
                </h2>
                <p className={`text-sm ${isSimulatingUser ? 'text-orange-600' : 'text-gray-500'}`}>
                  {isSimulatingUser
                    ? 'Modo ativo - faça logout para restaurar'
                    : 'Testar como usuário sem privilégios'}
                </p>
              </div>
              <div
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  isSimulatingUser ? 'bg-orange-500' : 'bg-gray-300'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    isSimulatingUser ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
