'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter, useParams } from 'next/navigation';
import {
  ArrowLeft,
  Loader2,
  AlertTriangle,
  MapPin,
  Calendar,
  User,
  Image as ImageIcon,
  Volume2,
  ExternalLink,
  Check,
  Trash2,
} from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';
import { apiClient, ProblemReport } from '@/lib/api';

const STATUS_OPTIONS = [
  { value: 'nova', label: 'Nova', color: 'bg-blue-100 text-blue-700' },
  { value: 'em_andamento', label: 'Em Andamento', color: 'bg-yellow-100 text-yellow-700' },
  { value: 'concluido', label: 'Concluido', color: 'bg-green-100 text-green-700' },
];

export default function ReportDetailsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const params = useParams();
  const reportId = params.id as string;

  const [report, setReport] = useState<ProblemReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Check admin access
  useEffect(() => {
    if (status === 'loading') return;
    if (!session?.user?.isAdmin) {
      router.push('/');
    }
  }, [session, status, router]);

  // Fetch report
  const fetchReport = useCallback(async () => {
    if (!reportId) return;

    setIsLoading(true);
    try {
      const data = await apiClient.getProblemReport(reportId);
      setReport(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar report');
    } finally {
      setIsLoading(false);
    }
  }, [reportId]);

  useEffect(() => {
    if (session?.user?.isAdmin) {
      fetchReport();
    }
  }, [session, fetchReport]);

  const handleStatusChange = async (newStatus: string) => {
    if (!report || report.status === newStatus) return;

    setIsUpdatingStatus(true);
    try {
      const updated = await apiClient.updateProblemReportStatus(report.id, newStatus);
      setReport(updated);
      toast.success('Status atualizado');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Erro ao atualizar status');
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  const handleDelete = async () => {
    if (!report) return;

    setIsDeleting(true);
    try {
      await apiClient.deleteProblemReport(report.id);
      toast.success('Report excluído');
      router.push('/admin/reports');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Erro ao excluir report');
      setShowDeleteConfirm(false);
    } finally {
      setIsDeleting(false);
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getGoogleMapsUrl = (lat: number, lon: number) => {
    return `https://www.google.com/maps?q=${lat},${lon}`;
  };

  // Calculate distance between two coordinates using Haversine formula
  const calculateDistance = (
    lat1: number,
    lon1: number,
    lat2: number,
    lon2: number
  ): number => {
    const R = 6371; // Earth's radius in km
    const dLat = ((lat2 - lat1) * Math.PI) / 180;
    const dLon = ((lon2 - lon1) * Math.PI) / 180;
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos((lat1 * Math.PI) / 180) *
        Math.cos((lat2 * Math.PI) / 180) *
        Math.sin(dLon / 2) *
        Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  };

  const formatDistance = (km: number): string => {
    if (km < 1) {
      return `${Math.round(km * 1000)} m`;
    }
    return `${km.toFixed(1)} km`;
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

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 py-8">
          <Link
            href="/admin/reports"
            className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Voltar para Reports
          </Link>
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
            <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <p className="text-red-700">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!report) {
    return null;
  }

  const imageAttachments = report.attachments.filter((a) => a.type === 'image');
  const audioAttachment = report.attachments.find((a) => a.type === 'audio');

  // Get token for authenticated image/audio URLs
  const token = session?.accessToken;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-6">
          <Link
            href="/admin/reports"
            className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Voltar para Reports
          </Link>
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-8 h-8 text-amber-500" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Detalhes do Report</h1>
                <p className="text-sm text-gray-600">ID: {report.id}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Main content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Problem info */}
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Problema Reportado</h2>

              <div className="mb-4">
                <span className="text-sm text-gray-500">Tipo:</span>
                <p className="font-medium text-gray-900">{report.problem_type.name}</p>
                {report.problem_type.description && (
                  <p className="text-sm text-gray-600">{report.problem_type.description}</p>
                )}
              </div>

              <div className="mb-4">
                <span className="text-sm text-gray-500">Descricao:</span>
                <p className="text-gray-900 whitespace-pre-wrap">{report.description}</p>
              </div>

              {report.poi && (
                <div className="mb-4">
                  <span className="text-sm text-gray-500">POI Relacionado:</span>
                  <p className="font-medium text-gray-900">
                    {report.poi.name} ({report.poi.type})
                  </p>
                  {report.latitude != null && report.longitude != null && (
                    <p className="text-sm text-gray-600">
                      Distância do usuário ao POI:{' '}
                      <span className="font-medium">
                        {formatDistance(
                          calculateDistance(
                            report.latitude,
                            report.longitude,
                            report.poi.latitude,
                            report.poi.longitude
                          )
                        )}
                      </span>
                    </p>
                  )}
                </div>
              )}

              {report.map && (
                <div className="mb-4">
                  <span className="text-sm text-gray-500">Mapa:</span>
                  <p className="text-gray-900">
                    {report.map.origin} → {report.map.destination}
                  </p>
                </div>
              )}
            </div>

            {/* Location */}
            {report.latitude != null && report.longitude != null && (
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <MapPin className="w-5 h-5" />
                  Localizacao
                </h2>

                <p className="text-gray-600 mb-3">
                  Lat: {report.latitude.toFixed(6)}, Lon: {report.longitude.toFixed(6)}
                </p>

                <a
                  href={getGoogleMapsUrl(report.latitude, report.longitude)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700"
                >
                  <ExternalLink className="w-4 h-4" />
                  Ver no Google Maps
                </a>
              </div>
            )}

            {/* Attachments */}
            {report.attachments.length > 0 && (
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Anexos</h2>

                {/* Images */}
                {imageAttachments.length > 0 && (
                  <div className="mb-6">
                    <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
                      <ImageIcon className="w-4 h-4" />
                      Fotos ({imageAttachments.length})
                    </h3>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                      {imageAttachments.map((att) => (
                        <a
                          key={att.id}
                          href={apiClient.getAttachmentUrl(report.id, att.id, token)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="aspect-square bg-gray-100 rounded-lg overflow-hidden hover:opacity-90 transition-opacity"
                        >
                          <img
                            src={apiClient.getAttachmentUrl(report.id, att.id, token)}
                            alt={att.filename}
                            className="w-full h-full object-cover"
                          />
                        </a>
                      ))}
                    </div>
                  </div>
                )}

                {/* Audio */}
                {audioAttachment && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
                      <Volume2 className="w-4 h-4" />
                      Audio
                    </h3>
                    <audio
                      src={apiClient.getAttachmentUrl(report.id, audioAttachment.id, token)}
                      controls
                      className="w-full"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      {audioAttachment.filename} ({(audioAttachment.size_bytes / 1024).toFixed(1)} KB)
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Status */}
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Status</h2>

              <div className="space-y-2">
                {STATUS_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => handleStatusChange(option.value)}
                    disabled={isUpdatingStatus}
                    className={`w-full flex items-center justify-between px-4 py-3 rounded-lg border transition-colors ${
                      report.status === option.value
                        ? `${option.color} border-current`
                        : 'border-gray-200 hover:bg-gray-50'
                    } disabled:opacity-50`}
                  >
                    <span className="font-medium">{option.label}</span>
                    {report.status === option.value && <Check className="w-5 h-5" />}
                  </button>
                ))}
              </div>
            </div>

            {/* User info */}
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <User className="w-5 h-5" />
                Usuario
              </h2>

              <div className="flex items-center gap-3">
                {report.user.avatar_url && (
                  <img
                    src={report.user.avatar_url}
                    alt={report.user.name}
                    className="w-12 h-12 rounded-full"
                  />
                )}
                <div>
                  <p className="font-medium text-gray-900">{report.user.name}</p>
                  <p className="text-sm text-gray-600">{report.user.email}</p>
                </div>
              </div>
            </div>

            {/* Timestamps */}
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Calendar className="w-5 h-5" />
                Datas
              </h2>

              <div className="space-y-3 text-sm">
                <div>
                  <span className="text-gray-500">Criado em:</span>
                  <p className="text-gray-900">{formatDate(report.created_at)}</p>
                </div>
                <div>
                  <span className="text-gray-500">Atualizado em:</span>
                  <p className="text-gray-900">{formatDate(report.updated_at)}</p>
                </div>
              </div>
            </div>

            {/* Delete */}
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Trash2 className="w-5 h-5" />
                Excluir
              </h2>

              {!showDeleteConfirm ? (
                <button
                  onClick={() => setShowDeleteConfirm(true)}
                  className="w-full px-4 py-2 text-red-600 border border-red-300 rounded-lg hover:bg-red-50 transition-colors"
                >
                  Excluir Report
                </button>
              ) : (
                <div className="space-y-3">
                  <p className="text-sm text-gray-600">
                    Tem certeza? Esta ação não pode ser desfeita.
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setShowDeleteConfirm(false)}
                      disabled={isDeleting}
                      className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
                    >
                      Cancelar
                    </button>
                    <button
                      onClick={handleDelete}
                      disabled={isDeleting}
                      className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      {isDeleting ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Excluindo...
                        </>
                      ) : (
                        'Confirmar'
                      )}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
