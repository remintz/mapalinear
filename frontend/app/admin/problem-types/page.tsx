'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Plus, Edit2, Trash2, Check, X, Loader2, AlertTriangle } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';
import { apiClient, ProblemTypeAdmin } from '@/lib/api';

export default function ProblemTypesPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  const [types, setTypes] = useState<ProblemTypeAdmin[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editSortOrder, setEditSortOrder] = useState(0);

  // New type state
  const [isAdding, setIsAdding] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [newSortOrder, setNewSortOrder] = useState(0);

  const [isSaving, setIsSaving] = useState(false);

  // Sort types by sort_order, then by name
  const sortTypes = (typesArr: ProblemTypeAdmin[]) => {
    return [...typesArr].sort((a, b) => {
      if (a.sort_order !== b.sort_order) {
        return a.sort_order - b.sort_order;
      }
      return a.name.localeCompare(b.name);
    });
  };

  // Check admin access
  useEffect(() => {
    if (status === 'loading') return;
    if (!session?.user?.isAdmin) {
      router.push('/');
    }
  }, [session, status, router]);

  // Fetch types
  const fetchTypes = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await apiClient.getAdminProblemTypes();
      setTypes(data.types);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar tipos');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (session?.user?.isAdmin) {
      fetchTypes();
    }
  }, [session, fetchTypes]);

  // Create type
  const handleCreate = async () => {
    if (!newName.trim()) {
      toast.error('Nome e obrigatorio');
      return;
    }

    setIsSaving(true);
    try {
      const created = await apiClient.createProblemType({
        name: newName.trim(),
        description: newDescription.trim() || undefined,
        sort_order: newSortOrder,
      });
      setTypes(sortTypes([...types, created]));
      setIsAdding(false);
      setNewName('');
      setNewDescription('');
      setNewSortOrder(0);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Erro ao criar tipo');
    } finally {
      setIsSaving(false);
    }
  };

  // Start editing
  const startEdit = (type: ProblemTypeAdmin) => {
    setEditingId(type.id);
    setEditName(type.name);
    setEditDescription(type.description || '');
    setEditSortOrder(type.sort_order);
  };

  // Save edit
  const handleSaveEdit = async () => {
    if (!editingId || !editName.trim()) {
      toast.error('Nome e obrigatorio');
      return;
    }

    setIsSaving(true);
    try {
      const updated = await apiClient.updateProblemType(editingId, {
        name: editName.trim(),
        description: editDescription.trim() || undefined,
        sort_order: editSortOrder,
      });
      setTypes(sortTypes(types.map((t) => (t.id === editingId ? updated : t))));
      setEditingId(null);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Erro ao atualizar tipo');
    } finally {
      setIsSaving(false);
    }
  };

  // Toggle active
  const handleToggleActive = async (type: ProblemTypeAdmin) => {
    try {
      const updated = await apiClient.updateProblemType(type.id, {
        is_active: !type.is_active,
      });
      setTypes(types.map((t) => (t.id === type.id ? updated : t)));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Erro ao alterar status');
    }
  };

  // Delete (soft delete)
  const handleDelete = async (type: ProblemTypeAdmin) => {
    if (!confirm(`Deseja desativar o tipo "${type.name}"?`)) {
      return;
    }

    try {
      await apiClient.deleteProblemType(type.id);
      setTypes(types.map((t) => (t.id === type.id ? { ...t, is_active: false } : t)));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Erro ao desativar tipo');
    }
  };

  if (status === 'loading' || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!session?.user?.isAdmin) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <Link
            href="/admin"
            className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Voltar para Administracao
          </Link>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-8 h-8 text-amber-500" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Tipos de Problema</h1>
                <p className="text-sm text-gray-600">
                  Configure os tipos de problemas que os usuarios podem reportar
                </p>
              </div>
            </div>
            <button
              onClick={() => setIsAdding(true)}
              disabled={isAdding}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg
                        hover:bg-blue-700 disabled:opacity-50"
            >
              <Plus className="w-4 h-4" />
              Novo Tipo
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {/* Add new type form */}
        {isAdding && (
          <div className="mb-6 p-4 bg-white border border-gray-200 rounded-lg shadow-sm">
            <h3 className="font-medium text-gray-900 mb-4">Novo Tipo de Problema</h3>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nome *
                </label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="Ex: Informacao incorreta"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Ordem
                </label>
                <input
                  type="number"
                  value={newSortOrder}
                  onChange={(e) => setNewSortOrder(parseInt(e.target.value) || 0)}
                  min="0"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
                />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Descricao
                </label>
                <input
                  type="text"
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  placeholder="Descricao opcional"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => {
                  setIsAdding(false);
                  setNewName('');
                  setNewDescription('');
                  setNewSortOrder(0);
                }}
                className="px-4 py-2 text-gray-600 hover:text-gray-900"
              >
                Cancelar
              </button>
              <button
                onClick={handleCreate}
                disabled={isSaving || !newName.trim()}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg
                          hover:bg-blue-700 disabled:opacity-50"
              >
                {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                Criar
              </button>
            </div>
          </div>
        )}

        {/* Types list */}
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Nome</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-700 hidden sm:table-cell">
                  Descricao
                </th>
                <th className="px-4 py-3 text-center text-sm font-medium text-gray-700 w-20">
                  Ordem
                </th>
                <th className="px-4 py-3 text-center text-sm font-medium text-gray-700 w-20">
                  Status
                </th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-700 w-24">
                  Acoes
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {types.map((type) => (
                <tr key={type.id} className={!type.is_active ? 'bg-gray-50 opacity-60' : ''}>
                  {editingId === type.id ? (
                    <>
                      <td className="px-4 py-3">
                        <input
                          type="text"
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          className="w-full px-2 py-1 border border-gray-300 rounded"
                        />
                      </td>
                      <td className="px-4 py-3 hidden sm:table-cell">
                        <input
                          type="text"
                          value={editDescription}
                          onChange={(e) => setEditDescription(e.target.value)}
                          className="w-full px-2 py-1 border border-gray-300 rounded"
                        />
                      </td>
                      <td className="px-4 py-3 text-center">
                        <input
                          type="number"
                          value={editSortOrder}
                          onChange={(e) => setEditSortOrder(parseInt(e.target.value) || 0)}
                          className="w-16 px-2 py-1 border border-gray-300 rounded text-center"
                        />
                      </td>
                      <td className="px-4 py-3 text-center">-</td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={handleSaveEdit}
                            disabled={isSaving}
                            className="p-1 text-green-600 hover:bg-green-50 rounded"
                          >
                            <Check className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => setEditingId(null)}
                            className="p-1 text-gray-600 hover:bg-gray-100 rounded"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </>
                  ) : (
                    <>
                      <td className="px-4 py-3">
                        <span className="font-medium text-gray-900">{type.name}</span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 hidden sm:table-cell">
                        {type.description || '-'}
                      </td>
                      <td className="px-4 py-3 text-center text-sm text-gray-600">
                        {type.sort_order}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <button
                          onClick={() => handleToggleActive(type)}
                          className={`px-2 py-1 text-xs rounded-full ${
                            type.is_active
                              ? 'bg-green-100 text-green-700'
                              : 'bg-gray-100 text-gray-600'
                          }`}
                        >
                          {type.is_active ? 'Ativo' : 'Inativo'}
                        </button>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => startEdit(type)}
                            className="p-1 text-gray-600 hover:bg-gray-100 rounded"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDelete(type)}
                            className="p-1 text-red-600 hover:bg-red-50 rounded"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </>
                  )}
                </tr>
              ))}
              {types.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                    Nenhum tipo de problema cadastrado
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
