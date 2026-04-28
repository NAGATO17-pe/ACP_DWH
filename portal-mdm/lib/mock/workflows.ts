export type WorkflowStatus =
  | "pendiente"
  | "en-revision"
  | "aprobado"
  | "rechazado";

export interface Workflow {
  id: string;
  entityId: string;
  entityName: string;
  type: "alta" | "modificacion" | "baja";
  requestedBy: string;
  assignedTo: string;
  status: WorkflowStatus;
  createdAt: string;
  changes: number;
}

export const WORKFLOWS: Workflow[] = [
  {
    id: "WF-2041",
    entityId: "ENT-1004",
    entityName: "Distribuidora Andes S.A.",
    type: "modificacion",
    requestedBy: "Carmen Vega",
    assignedTo: "Luis Quispe",
    status: "pendiente",
    createdAt: "2026-04-26T14:32:00Z",
    changes: 4,
  },
  {
    id: "WF-2042",
    entityId: "ENT-1011",
    entityName: "Cooperativa Agraria Cusco",
    type: "alta",
    requestedBy: "Andrea Salas",
    assignedTo: "Daniel Rojas",
    status: "en-revision",
    createdAt: "2026-04-25T09:15:00Z",
    changes: 12,
  },
  {
    id: "WF-2043",
    entityId: "ENT-1018",
    entityName: "Mercados Globales SA",
    type: "modificacion",
    requestedBy: "María Torres",
    assignedTo: "Carmen Vega",
    status: "pendiente",
    createdAt: "2026-04-24T11:48:00Z",
    changes: 2,
  },
  {
    id: "WF-2044",
    entityId: "ENT-1025",
    entityName: "Café de Origen Selva",
    type: "baja",
    requestedBy: "Daniel Rojas",
    assignedTo: "Andrea Salas",
    status: "aprobado",
    createdAt: "2026-04-22T16:05:00Z",
    changes: 1,
  },
  {
    id: "WF-2045",
    entityId: "ENT-1032",
    entityName: "Logística Centro Andina",
    type: "modificacion",
    requestedBy: "Luis Quispe",
    assignedTo: "María Torres",
    status: "rechazado",
    createdAt: "2026-04-20T10:21:00Z",
    changes: 6,
  },
];

export const WORKFLOW_STATUS_LABEL: Record<WorkflowStatus, string> = {
  pendiente: "Pendiente",
  "en-revision": "En revisión",
  aprobado: "Aprobado",
  rechazado: "Rechazado",
};
