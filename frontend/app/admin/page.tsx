"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import Link from "next/link";
import { Users, Settings, Shield } from "lucide-react";

export default function AdminPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

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
        </div>
      </div>
    </div>
  );
}
