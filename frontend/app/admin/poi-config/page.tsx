"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Settings,
  Tag,
  Save,
  RefreshCw,
  Loader2,
  RotateCcw,
  Check,
} from "lucide-react";
import { toast } from "sonner";
import { apiClient } from "@/lib/api";
import { RequiredTagsConfig } from "@/lib/types";

const POI_TYPE_LABELS: Record<string, string> = {
  gas_station: "Posto de Combustível",
  restaurant: "Restaurante",
  hotel: "Hotel",
  hospital: "Hospital",
  toll_booth: "Pedágio",
  rest_area: "Área de Descanso",
  city: "Cidade",
  town: "Cidade Pequena",
  village: "Vila",
};

const POI_TYPE_ICONS: Record<string, string> = {
  gas_station: "⛽",
  restaurant: "🍽️",
  hotel: "🏨",
  hospital: "🏥",
  toll_booth: "🚧",
  rest_area: "🅿️",
  city: "🏙️",
  town: "🏘️",
  village: "🏡",
};

const TAG_LABELS: Record<string, string> = {
  name: "Nome",
  brand: "Marca",
  operator: "Operadora",
  phone: "Telefone",
  website: "Website",
  opening_hours: "Horário",
  cuisine: "Culinária",
  stars: "Estrelas",
  "addr:street": "Rua",
  "addr:city": "Cidade",
};

export default function POIConfigPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  const [config, setConfig] = useState<RequiredTagsConfig | null>(null);
  const [editedTags, setEditedTags] = useState<Record<string, string[]>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [recalculating, setRecalculating] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  const loadConfig = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiClient.getRequiredTags();
      setConfig(data);
      setEditedTags(data.required_tags);
      setHasChanges(false);
    } catch (error) {
      console.error("Error loading config:", error);
      toast.error("Erro ao carregar configuração");
    } finally {
      setLoading(false);
    }
  }, []);

  // Auth check
  useEffect(() => {
    if (status === "loading") return;
    if (!session?.user?.isAdmin) {
      router.push("/");
    }
  }, [session, status, router]);

  // Load config on mount
  useEffect(() => {
    if (session?.user?.isAdmin) {
      loadConfig();
    }
  }, [session, loadConfig]);

  const handleTagToggle = (poiType: string, tag: string) => {
    setEditedTags((prev) => {
      const currentTags = prev[poiType] || [];
      const newTags = currentTags.includes(tag)
        ? currentTags.filter((t) => t !== tag)
        : [...currentTags, tag];

      return {
        ...prev,
        [poiType]: newTags,
      };
    });
    setHasChanges(true);
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await apiClient.updateRequiredTags(editedTags);
      toast.success("Configuração salva com sucesso!");
      setHasChanges(false);
    } catch (error) {
      console.error("Error saving config:", error);
      toast.error("Erro ao salvar configuração");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!confirm("Restaurar configuração padrão? Suas alterações serão perdidas.")) {
      return;
    }

    try {
      setResetting(true);
      const data = await apiClient.resetRequiredTags();
      setConfig(data);
      setEditedTags(data.required_tags);
      setHasChanges(false);
      toast.success("Configuração restaurada para o padrão");
    } catch (error) {
      console.error("Error resetting config:", error);
      toast.error("Erro ao restaurar configuração");
    } finally {
      setResetting(false);
    }
  };

  const handleRecalculate = async () => {
    if (hasChanges) {
      toast.warning("Salve as alterações antes de recalcular a qualidade.");
      return;
    }

    if (!confirm("Recalcular qualidade de todos os POIs? Isso pode demorar alguns minutos.")) {
      return;
    }

    try {
      setRecalculating(true);
      const result = await apiClient.recalculatePOIQuality();
      toast.success(result.message);
    } catch (error) {
      console.error("Error recalculating:", error);
      toast.error("Erro ao recalcular qualidade");
    } finally {
      setRecalculating(false);
    }
  };

  if (status === "loading" || loading || !session?.user?.isAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!config) {
    return null;
  }

  const poiTypes = Object.keys(POI_TYPE_LABELS);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-20 bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Link href="/admin" className="text-blue-600 hover:text-blue-700">
                <ArrowLeft className="h-5 w-5" />
              </Link>
              <div>
                <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                  <Settings className="h-5 w-5 text-blue-600" />
                  Configuração de Tags Obrigatórias
                </h1>
                <p className="text-sm text-gray-600">
                  Defina quais tags são obrigatórias para cada tipo de POI
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleRecalculate}
                disabled={recalculating || hasChanges}
                className="flex items-center gap-2 px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
              >
                {recalculating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
                Recalcular
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        {/* Info box */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <div className="flex items-start gap-3">
            <Tag className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
            <div>
              <h3 className="font-medium text-blue-900">Como funciona</h3>
              <p className="text-sm text-blue-700 mt-1">
                POIs que não possuírem <strong>todas</strong> as tags obrigatórias para seu tipo
                serão marcados como "baixa qualidade". Após alterar a configuração, clique em
                "Recalcular" para atualizar todos os POIs.
              </p>
            </div>
          </div>
        </div>

        {/* POI Types Configuration */}
        <div className="space-y-4">
          {poiTypes.map((poiType) => {
            const selectedTags = editedTags[poiType] || [];

            return (
              <div
                key={poiType}
                className="bg-white rounded-lg shadow-sm border border-gray-200 p-4"
              >
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-xl">{POI_TYPE_ICONS[poiType]}</span>
                  <h3 className="font-semibold text-gray-900">
                    {POI_TYPE_LABELS[poiType]}
                  </h3>
                  <span className="text-xs text-gray-500 ml-auto">
                    {selectedTags.length} tag{selectedTags.length !== 1 ? "s" : ""} obrigatória
                    {selectedTags.length !== 1 ? "s" : ""}
                  </span>
                </div>

                <div className="flex flex-wrap gap-2">
                  {config.available_tags.map((tag) => {
                    const isSelected = selectedTags.includes(tag);
                    return (
                      <button
                        key={tag}
                        onClick={() => handleTagToggle(poiType, tag)}
                        className={`px-3 py-1.5 rounded-full text-sm flex items-center gap-1.5 transition-colors ${
                          isSelected
                            ? "bg-blue-100 text-blue-700 border border-blue-300"
                            : "bg-gray-100 text-gray-600 border border-gray-200 hover:bg-gray-200"
                        }`}
                      >
                        {isSelected && <Check className="h-3 w-3" />}
                        {TAG_LABELS[tag] || tag}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        {/* Action buttons */}
        <div className="flex items-center justify-between mt-6 pt-6 border-t border-gray-200">
          <button
            onClick={handleReset}
            disabled={resetting}
            className="flex items-center gap-2 px-4 py-2 text-gray-700 hover:text-gray-900"
          >
            {resetting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RotateCcw className="h-4 w-4" />
            )}
            Restaurar Padrão
          </button>

          <button
            onClick={handleSave}
            disabled={saving || !hasChanges}
            className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            Salvar Alterações
          </button>
        </div>

        {hasChanges && (
          <p className="text-center text-sm text-amber-600 mt-4">
            Você tem alterações não salvas
          </p>
        )}
      </main>
    </div>
  );
}
