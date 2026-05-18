export interface QualityKpi {
  completeness: number;
  validated: number;
  activeErrors: number;
  globalScore: number;
  deltas: {
    completeness: number;
    validated: number;
    activeErrors: number;
    globalScore: number;
  };
}

export const QUALITY_KPIS: QualityKpi = {
  completeness: 87.4,
  validated: 78.2,
  activeErrors: 142,
  globalScore: 84,
  deltas: {
    completeness: 2.1,
    validated: 4.3,
    activeErrors: -8.2,
    globalScore: 1.6,
  },
};

export interface QualityByEntity {
  entity: string;
  target: number;
  actual: number;
  errors: number;
}

export const QUALITY_BY_ENTITY: QualityByEntity[] = [
  { entity: "Clientes", target: 95, actual: 88, errors: 42 },
  { entity: "Productos", target: 95, actual: 91, errors: 28 },
  { entity: "Proveedores", target: 90, actual: 86, errors: 31 },
  { entity: "Ubicaciones", target: 95, actual: 79, errors: 41 },
];

export interface QualityTrend {
  date: string;
  errors: number;
  validated: number;
}

export const QUALITY_TREND: QualityTrend[] = Array.from({ length: 12 }, (_, i) => {
  const month = new Date(Date.UTC(2026, i, 1));
  return {
    date: month.toLocaleDateString("es-PE", { month: "short" }),
    errors: 220 - i * 8 + (i % 3) * 6,
    validated: 60 + i * 2 + (i % 4) * 3,
  };
});

export interface QualityRadarItem {
  metric: string;
  Clientes: number;
  Productos: number;
  Proveedores: number;
  Ubicaciones: number;
}

export const QUALITY_RADAR: QualityRadarItem[] = [
  { metric: "Completitud", Clientes: 88, Productos: 91, Proveedores: 86, Ubicaciones: 79 },
  { metric: "Unicidad", Clientes: 92, Productos: 95, Proveedores: 88, Ubicaciones: 84 },
  { metric: "Validez", Clientes: 80, Productos: 87, Proveedores: 76, Ubicaciones: 71 },
  { metric: "Consistencia", Clientes: 86, Productos: 89, Proveedores: 82, Ubicaciones: 78 },
  { metric: "Actualidad", Clientes: 76, Productos: 84, Proveedores: 73, Ubicaciones: 69 },
];
