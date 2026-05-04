export type AuditAction =
  | "creacion"
  | "modificacion"
  | "aprobacion"
  | "rechazo"
  | "eliminacion"
  | "login";

export interface AuditEvent {
  id: string;
  timestamp: string;
  user: string;
  action: AuditAction;
  resource: string;
  details: string;
}

export const AUDIT_EVENTS: AuditEvent[] = [
  {
    id: "AUD-9001",
    timestamp: "2026-04-28T14:22:00Z",
    user: "Carmen Vega",
    action: "aprobacion",
    resource: "WF-2044 — Café de Origen Selva",
    details: "Workflow aprobado tras revisión de cumplimiento.",
  },
  {
    id: "AUD-9000",
    timestamp: "2026-04-28T13:48:00Z",
    user: "Luis Quispe",
    action: "modificacion",
    resource: "ENT-1004 — Distribuidora Andes S.A.",
    details: "Actualizó dirección fiscal y RUC.",
  },
  {
    id: "AUD-8999",
    timestamp: "2026-04-28T11:15:00Z",
    user: "Andrea Salas",
    action: "creacion",
    resource: "ENT-1011 — Cooperativa Agraria Cusco",
    details: "Alta de nuevo cliente con 12 atributos.",
  },
  {
    id: "AUD-8998",
    timestamp: "2026-04-28T09:02:00Z",
    user: "Daniel Rojas",
    action: "rechazo",
    resource: "WF-2045 — Logística Centro Andina",
    details: "Rechazo por documentación incompleta.",
  },
  {
    id: "AUD-8997",
    timestamp: "2026-04-27T17:33:00Z",
    user: "María Torres",
    action: "modificacion",
    resource: "ENT-1018 — Mercados Globales SA",
    details: "Cambio de propietario de la entidad.",
  },
  {
    id: "AUD-8996",
    timestamp: "2026-04-27T08:15:00Z",
    user: "Carmen Vega",
    action: "login",
    resource: "Sesión",
    details: "Inicio de sesión desde 192.168.20.41.",
  },
];

export const AUDIT_ACTION_LABEL: Record<AuditAction, string> = {
  creacion: "Creación",
  modificacion: "Modificación",
  aprobacion: "Aprobación",
  rechazo: "Rechazo",
  eliminacion: "Eliminación",
  login: "Inicio sesión",
};
