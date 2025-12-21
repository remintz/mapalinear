"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import Image from "next/image";
import {
  Users,
  ArrowLeft,
  Shield,
  ShieldOff,
  MapPin,
  Calendar,
  Clock,
  User,
  CheckCircle,
  XCircle,
  Loader2,
} from "lucide-react";
import { AdminUser, AdminUserListResponse } from "@/lib/types";

export default function AdminUsersPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingUser, setUpdatingUser] = useState<string | null>(null);

  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/api"}/admin/users`,
        {
          headers: {
            Authorization: `Bearer ${session?.accessToken}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error("Falha ao carregar usuários");
      }

      const data: AdminUserListResponse = await response.json();
      setUsers(data.users);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro desconhecido");
    } finally {
      setLoading(false);
    }
  }, [session?.accessToken]);

  useEffect(() => {
    if (status === "loading") return;

    if (!session?.user?.isAdmin) {
      router.push("/");
      return;
    }

    fetchUsers();
  }, [session, status, router, fetchUsers]);

  const toggleAdmin = async (userId: string, currentIsAdmin: boolean) => {
    if (userId === session?.user?.id && currentIsAdmin) {
      alert("Você não pode remover seu próprio status de administrador");
      return;
    }

    try {
      setUpdatingUser(userId);

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/api"}/admin/users/${userId}/admin`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${session?.accessToken}`,
          },
          body: JSON.stringify({ is_admin: !currentIsAdmin }),
        }
      );

      if (!response.ok) {
        throw new Error("Falha ao atualizar status de admin");
      }

      const updatedUser: AdminUser = await response.json();
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? updatedUser : u))
      );
    } catch (err) {
      alert(err instanceof Error ? err.message : "Erro ao atualizar");
    } finally {
      setUpdatingUser(null);
    }
  };

  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return "Nunca";
    return new Date(dateString).toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getRelativeTime = (dateString: string | null | undefined) => {
    if (!dateString) return null;

    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 5) return "Agora";
    if (diffMins < 60) return `${diffMins} min atrás`;
    if (diffHours < 24) return `${diffHours}h atrás`;
    if (diffDays < 7) return `${diffDays}d atrás`;
    return null;
  };

  if (status === "loading" || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex items-center gap-3">
          <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
          <span className="text-gray-600">Carregando...</span>
        </div>
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
          <Link
            href="/admin"
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Voltar para Administração
          </Link>

          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Users className="w-8 h-8 text-blue-600" />
            Usuários
          </h1>
          <p className="mt-2 text-gray-600">
            {users.length} usuário{users.length !== 1 ? "s" : ""} cadastrado
            {users.length !== 1 ? "s" : ""}
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Usuário
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Mapas
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Último Acesso
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Cadastro
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Admin
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {users.map((user) => {
                  const relativeTime = getRelativeTime(user.last_login_at);
                  const isOnline = relativeTime === "Agora";

                  return (
                    <tr key={user.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-3">
                          {user.avatar_url ? (
                            <Image
                              src={user.avatar_url}
                              alt={user.name}
                              width={40}
                              height={40}
                              className="rounded-full"
                            />
                          ) : (
                            <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                              <User className="w-5 h-5 text-blue-600" />
                            </div>
                          )}
                          <div>
                            <div className="text-sm font-medium text-gray-900 flex items-center gap-2">
                              {user.name}
                              {user.is_admin && (
                                <Shield className="w-4 h-4 text-blue-600" />
                              )}
                            </div>
                            <div className="text-sm text-gray-500">
                              {user.email}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            user.is_active
                              ? "bg-green-100 text-green-800"
                              : "bg-red-100 text-red-800"
                          }`}
                        >
                          {user.is_active ? (
                            <>
                              <CheckCircle className="w-3 h-3" />
                              Ativo
                            </>
                          ) : (
                            <>
                              <XCircle className="w-3 h-3" />
                              Inativo
                            </>
                          )}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-1 text-sm text-gray-600">
                          <MapPin className="w-4 h-4" />
                          {user.map_count}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-600">
                          <div className="flex items-center gap-1">
                            <Clock className="w-4 h-4" />
                            {relativeTime || formatDate(user.last_login_at)}
                          </div>
                          {isOnline && (
                            <span className="inline-flex items-center gap-1 text-xs text-green-600 mt-1">
                              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                              Online
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-1 text-sm text-gray-600">
                          <Calendar className="w-4 h-4" />
                          {formatDate(user.created_at)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <button
                          onClick={() => toggleAdmin(user.id, user.is_admin)}
                          disabled={updatingUser === user.id}
                          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                            user.is_admin
                              ? "bg-blue-100 text-blue-700 hover:bg-blue-200"
                              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                          } disabled:opacity-50 disabled:cursor-not-allowed`}
                        >
                          {updatingUser === user.id ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : user.is_admin ? (
                            <>
                              <Shield className="w-4 h-4" />
                              Admin
                            </>
                          ) : (
                            <>
                              <ShieldOff className="w-4 h-4" />
                              Usuário
                            </>
                          )}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
