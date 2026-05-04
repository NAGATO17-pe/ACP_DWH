# Portal MDM — ACP

Portal único multi-rol (Analistas / Administradores MDM / Ejecutivos) para la
plataforma ACP. Construido con Next.js 16 (App Router), TypeScript 5,
Tailwind CSS 4 y los lineamientos del documento _Plan de Mejora Continua_.

---

## Stack

| Capa            | Tecnología                        |
| --------------- | --------------------------------- |
| Framework       | Next.js 16 (App Router, React 19) |
| Lenguaje        | TypeScript 5                      |
| Estilos         | Tailwind CSS 4 + design tokens    |
| Componentes     | Radix UI (shadcn/ui approach)     |
| Tablas          | TanStack Table v8                 |
| Charts          | Recharts + Plotly.js              |
| Forms           | React Hook Form + Zod             |
| HTTP / Cache    | TanStack Query + fetch            |
| Auth            | JWT httpOnly cookie + jose        |
| Iconos          | Lucide React                      |
| Tests E2E       | Playwright                        |

---

## Requisitos

- **Node.js 20+** (probado con Node 22)
- **npm 9+**
- Un backend **FastAPI** con los endpoints de auth descritos en §5

---

## Setup local

```bash
# 1. Clonar el repo
git clone https://github.com/NAGATO17-pe/portal-mdm.git
cd portal-mdm

# 2. Instalar dependencias
npm install

# 3. Variables de entorno
cp .env.example .env.local
# Edita .env.local con los valores de tu entorno

# 4. Iniciar en desarrollo (Turbopack)
npm run dev
```

El portal estará en `http://localhost:3000`.

---

## Variables de entorno

| Variable              | Default               | Descripción                                       |
| --------------------- | --------------------- | ------------------------------------------------- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Base URL del FastAPI backend                    |
| `JWT_COOKIE_NAME`     | `mdm_session`         | Nombre de la cookie httpOnly de sesión            |
| `JWT_PUBLIC_SECRET`   | _(vacío)_             | Secret HMAC HS256/HS512 para verificar firma JWT  |

> En producción `JWT_PUBLIC_SECRET` es **obligatorio**. Sin él el portal acepta
> cualquier JWT sin verificar firma (solo válido en dev local).

---

## Scripts

```bash
npm run dev         # Servidor desarrollo (Turbopack)
npm run build       # Build de producción
npm run start       # Servidor de producción
npm run lint        # ESLint
npm run test:e2e    # Tests E2E con Playwright (headless)
npm run test:e2e:ui # Tests E2E con UI interactiva
```

---

## Roles y rutas

| Rol        | Prefijos permitidos                             | Home        |
| ---------- | ----------------------------------------------- | ----------- |
| Analista   | `/explore`, `/models`, `/reports`               | `/explore`  |
| Admin      | `/entities`, `/workflows`, `/quality`, `/audit` | `/entities` |
| Ejecutivo  | `/overview`                                     | `/overview` |

El mapping está centralizado en `lib/auth/rbac.ts`.

---

## Arquitectura de carpetas

```
portal-mdm/
├── app/
│   ├── (auth)/login/          # Página de login (RHF + Zod)
│   ├── (analyst)/             # Layout + rutas del analista
│   ├── (admin)/               # Layout + rutas del administrador
│   ├── (executive)/           # Layout + rutas del ejecutivo
│   ├── api/auth/              # Route handlers: login / logout / me
│   ├── error.tsx              # Error boundary global
│   ├── not-found.tsx          # Página 404
│   ├── layout.tsx             # Root layout (fonts, theme, skip-nav)
│   └── globals.css            # Design tokens + Tailwind base
├── components/
│   ├── ui/                    # Button, Card, Badge, Input, Tabs, Skeleton…
│   ├── charts/                # KpiCard, PlotlyChart, Recharts theme
│   ├── data-table/            # DataTable genérico (TanStack Table v8)
│   ├── layout/                # RoleShell, PagePlaceholder
│   └── providers/             # QueryProvider
├── e2e/                       # Tests Playwright
├── lib/
│   ├── api/client.ts          # Wrapper HTTP hacia FastAPI
│   ├── auth/rbac.ts           # Mapping rol → rutas
│   ├── auth/session.ts        # Lectura/verificación JWT server-side
│   ├── schemas/auth.ts        # Zod schemas de auth
│   ├── mock/                  # Datos de prueba (reemplazar con API real)
│   └── format.ts              # Helpers de fecha/número/porcentaje
├── proxy.ts                   # Auth + RBAC gate (Next 16: ex-middleware)
└── playwright.config.ts
```

---

## Integración con FastAPI

El portal consume el backend vía `lib/api/client.ts`. Los contratos esperados:

### `POST /auth/login`

```json
// Request
{ "email": "user@empresa.com", "password": "secreto" }

// Response 200
{ "access_token": "<JWT>", "token_type": "bearer" }
```

El JWT debe contener en su payload:

```json
{ "sub": "user-id", "role": "analyst|admin|executive", "name": "Nombre", "exp": 1234567890 }
```

Firmado con HS256 o HS512 usando el mismo `JWT_PUBLIC_SECRET`.

### `GET /` (health check)

Usado por `lib/api/client.ts` para verificar disponibilidad.

---

## Tests E2E

Los tests en `e2e/` usan una cookie JWT falsa (`e2e/helpers/auth.ts`) para
no necesitar un backend real:

```bash
# Instalar browsers de Playwright (solo primera vez)
npx playwright install chromium

# Correr todos los tests
npm run test:e2e

# Correr con UI visual
npm run test:e2e:ui
```

Suites disponibles:
- `auth.spec.ts` — Login, validaciones, redirección si ya autenticado
- `entities.spec.ts` — DataTable, filtros, paginación
- `workflows.spec.ts` — Cola, stepper, botones de acción
- `analyst.spec.ts` — Modelos, exploración, control de acceso por rol
- `executive.spec.ts` — Overview, control de acceso por rol

---

## Runbook de deploy en producción

### 1. Build

```bash
npm run build
```

### 2. Variables de entorno de producción

```env
NEXT_PUBLIC_API_URL=https://api.tudominio.com
JWT_COOKIE_NAME=mdm_session
JWT_PUBLIC_SECRET=<tu-secret-hmac-256-bits>
```

### 3. Iniciar servidor

```bash
npm run start
# o con PM2:
pm2 start npm --name "portal-mdm" -- start
```

### 4. Nginx (reverse proxy)

```nginx
server {
    listen 443 ssl;
    server_name portal.tudominio.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 5. Variables de entorno en CI/CD

Si se usa GitHub Actions o similar, agregar los secretos:
`NEXT_PUBLIC_API_URL`, `JWT_COOKIE_NAME`, `JWT_PUBLIC_SECRET`.

---

## Convenciones de desarrollo

- **Sin emojis** en UI: usar Lucide React siempre.
- **Touch targets ≥ 44px**, focus rings visibles (2–4px), contraste WCAG AA.
- **Server Components** por defecto; `"use client"` solo donde se necesite.
- `proxy.ts` solo hace gating optimista. La verificación criptográfica vive
  en `lib/auth/session.ts` (Server Components / route handlers).
- **No** agregar lógica en `proxy.ts` que requiera llamadas lentas o DB.

---

## Hoja de ruta post-MVP

| Iteración | Funcionalidades |
| --------- | --------------- |
| Iter 1 (mes 3-4) | Atajos de teclado, vistas guardadas, bulk import CSV |
| Iter 2 (mes 5-6) | Tema light, dashboard ejecutivo drag-and-drop, reportes programados |
| Iter 3 (mes 7+) | Búsqueda semántica, anomaly detection, asistente conversacional |
