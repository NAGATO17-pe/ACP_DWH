export type ModelStatus = "produccion" | "staging" | "archivado";

export interface PredictiveModel {
  id: string;
  name: string;
  algorithm: string;
  target: string;
  accuracy: number;
  auc: number;
  f1: number;
  status: ModelStatus;
  trainedAt: string;
  predictions24h: number;
}

export const MODELS: PredictiveModel[] = [
  {
    id: "MDL-001",
    name: "Predicción de churn comercial",
    algorithm: "XGBoost",
    target: "Cliente",
    accuracy: 0.892,
    auc: 0.94,
    f1: 0.85,
    status: "produccion",
    trainedAt: "2026-04-15T10:00:00Z",
    predictions24h: 12_842,
  },
  {
    id: "MDL-002",
    name: "Tasa de crecimiento fenológico",
    algorithm: "LightGBM",
    target: "Producto",
    accuracy: 0.876,
    auc: 0.91,
    f1: 0.82,
    status: "produccion",
    trainedAt: "2026-04-10T14:20:00Z",
    predictions24h: 8_456,
  },
  {
    id: "MDL-003",
    name: "Riesgo crediticio proveedores",
    algorithm: "Random Forest",
    target: "Proveedor",
    accuracy: 0.843,
    auc: 0.88,
    f1: 0.79,
    status: "staging",
    trainedAt: "2026-04-22T09:45:00Z",
    predictions24h: 0,
  },
  {
    id: "MDL-004",
    name: "Optimización ruta logística",
    algorithm: "Neural Network",
    target: "Ubicación",
    accuracy: 0.812,
    auc: 0.85,
    f1: 0.76,
    status: "produccion",
    trainedAt: "2026-04-05T08:30:00Z",
    predictions24h: 3_204,
  },
  {
    id: "MDL-005",
    name: "Anomalías en transacciones",
    algorithm: "Isolation Forest",
    target: "Cliente",
    accuracy: 0.798,
    auc: 0.82,
    f1: 0.71,
    status: "archivado",
    trainedAt: "2026-02-12T11:00:00Z",
    predictions24h: 0,
  },
];

export const MODEL_STATUS_LABEL: Record<ModelStatus, string> = {
  produccion: "Producción",
  staging: "Staging",
  archivado: "Archivado",
};
