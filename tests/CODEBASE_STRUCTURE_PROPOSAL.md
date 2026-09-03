# AutoSocial — Codebase Audit & Proposed Architecture Reorganization

This document details the architectural audit of the AutoSocial monorepo, catalogs current inconsistencies and duplications, and defines the target directory structure to standardize development across backend, frontend, and microservices.

---

## 1. Codebase Audit & Current State Analysis

### A. Monorepo Structural Inconsistencies
1. **Legacy Namespace vs. Modern Product Name**:
   - Monorepo package scopes and TypeScript path aliases retain `@gitroom/...` (`@gitroom/backend`, `@gitroom/nestjs-libraries`, `@gitroom/frontend`, `@gitroom/react`), whereas the product identity, business logic, and UI have evolved into **AutoSocial**.
2. **Backend Controller Sprawl**:
   - In `apps/backend/src/api/routes`, over **50 NestJS controllers** reside in a single flat directory without domain boundaries. Admin, Real Estate, Billing, AutoVoice, Social Media, and Public controllers sit together.
3. **Frontend Component & Lib Leaks**:
   - Misplaced directories outside `src/`:
     - `apps/frontend/components/video-playground/` AND `apps/frontend/components/video-playgrounds/` *(direct folder-level duplication)*.
     - `apps/frontend/lib/timezone.utils.ts` placed outside `src/`, while `apps/frontend/src/lib/` exists.
   - Dual routing models:
     - `apps/frontend/src/app` (Next.js 15 App Router) handles all pages.
     - `apps/frontend/src/pages/api/media` persists under the legacy Pages Router.
4. **Monorepo Root Clutter**:
   - **Committed Private SSH Keys**: `autosocial.pem`, `autosocial-runner.pem`, `autosocial-jenkins.pem`.
   - **Scratch / Temporary Files**: `leep 5`, `ma-generate`, `ma_migrations`, `ql`, `rolled back');`, `t prisma = new PrismaClient();`, `ts = cursor.fetchone()[0]`, `ubprocess`, `ycopg2.connect(db_url)`, `-`.
   - **Uncategorized Scripts & Migrations**: 15+ loose `.sql` files and 10+ `.sh` scripts scattered across root rather than inside `scripts/migrations/` or `scripts/dev/`.

### B. Runtime & Module Findings
1. **Node Native Dependencies**:
   - `canvas@2.11.2` (used for image rendering, collages, and posters) has official prebuilt binaries on Windows for Node 20 LTS. On Node 22/24, it triggers `node-gyp` compiling from source, failing if Visual Studio C++ build tools are not installed.
2. **Missing Dynamic Modules**:
   - Dynamic imports for Nostr provider and MCP services (`@gitroom/nestjs-libraries/chat/start.mcp`) produce expected fallback warnings during backend boot.
3. **MockRedis Compatibility**:
   - When running without Redis (`REDIS_URL` omitted), `MockRedis` in `libraries/nestjs-libraries/src/redis/redis.service.ts` lacks `defineCommand()`, causing Bottleneck rate limiters to throw a TypeError.

---

## 2. The Five Core Portals & Functional Modules

| Portal / Module | Primary Routes | Target Audience | Key Responsibilities |
| :--- | :--- | :--- | :--- |
| **1. Agent Marketing & Social Hub** | `/posts-hub`, `/hyperlocal`, `/media`, `/calendar` | Real Estate Agents | Multi-platform publishing, automated weekly hyperlocal community updates, product offerings, two-way Google Calendar synchronization. |
| **2. ZIP Farming & Lead Generation** | `/zip-farming`, `/reserve-your-zip` | Top Producing Agents | Territorial ZIP code claims, automated Meta Lead Ads campaigns, open house collage generation, lead CRM attribution. |
| **3. AI Intelligence (AutoIntel)** | `/autointel`, `/agents`, `/video-playgrounds` | Agents & Buyers | **AutoVoice**: 24/7 AI phone receptionist (Retell AI).<br>**AutoStaging**: Virtual room staging & 3D WebGL walkthroughs.<br>**Copilot**: Real estate conversational agent & media generation. |
| **4. Public Client & Buyer Engagement** | `/agent-site`, `/agent-directory`, `/3d-tour/[id]`, `/homes/[slug]` | Prospective Homebuyers | Branded agent personal websites, interactive 3D WebGL property tour player, real-time buyer concierge sessions, public lead capture. |
| **5. SuperAdmin Mission Control** | `/admin`, `/mission-control` | Platform Operators & Admins | Multi-tenant organization governance, Stripe Connect split-fee billing, usage-based wallet auto-topups, MLS Gateway rate limiting, lifecycle emails. |

---

## 3. Proposed Repository File Structure

```
autosocial/
├── apps/
│   ├── backend/                     # NestJS API Service (Port 3000)
│   │   ├── src/
│   │   │   ├── api/
│   │   │   │   ├── controllers/     # Categorized by domain (replaces flat routes/)
│   │   │   │   │   ├── admin/       # SuperAdmin, tenant & pricing controllers
│   │   │   │   │   ├── agent/       # Copilot, calendar, posts & media controllers
│   │   │   │   │   ├── autointel/   # AutoVoice (Retell), AutoStaging & tours
│   │   │   │   │   ├── billing/     # Stripe, wallet & payment split controllers
│   │   │   │   │   ├── public/      # Unauthenticated public client endpoints
│   │   │   │   │   └── zip-farming/ # Lead ads, territories & properties
│   │   │   │   ├── guards/          # PoliciesGuard, SuperAdminGuard, Throttler
│   │   │   │   ├── middleware/      # AuthMiddleware, RequestLogger
│   │   │   │   └── filters/         # Exception filters (Payment, Subscription)
│   │   │   ├── services/            # Domain business logic
│   │   │   │   ├── agent-campaign/
│   │   │   │   ├── autostaging/
│   │   │   │   ├── billing/
│   │   │   │   ├── calendar/
│   │   │   │   ├── hyperlocal/
│   │   │   │   └── zip-farming/
│   │   │   ├── app.module.ts
│   │   │   └── main.ts
│   │   ├── tsconfig.json
│   │   └── package.json
│   │
│   ├── frontend/                    # Next.js 15 App (Port 4200)
│   │   ├── public/                  # Static assets, logos, icons
│   │   ├── src/
│   │   │   ├── app/                 # Next.js App Router (unified routing)
│   │   │   │   ├── (auth)/          # /auth/login, /auth/register, /signup
│   │   │   │   ├── (portal)/        # Protected workspace pages
│   │   │   │   │   ├── admin/       # SuperAdmin Mission Control
│   │   │   │   │   ├── autointel/   # AutoVoice & AutoStaging UI
│   │   │   │   │   ├── billing/     # Wallet & subscription management
│   │   │   │   │   ├── hyperlocal/  # Hyperlocal market updates
│   │   │   │   │   ├── posts-hub/   # Multi-platform post scheduler
│   │   │   │   │   └── zip-farming/ # Territory claims & lead ads
│   │   │   │   ├── (public)/        # Public agent sites, 3D tour viewers
│   │   │   │   │   ├── 3d-tour/
│   │   │   │   │   └── agent-site/
│   │   │   │   ├── api/             # App Router Route Handlers (replaces src/pages/api)
│   │   │   │   │   └── media/route.ts
│   │   │   │   ├── layout.tsx
│   │   │   │   └── page.tsx
│   │   │   ├── components/          # Shared & domain UI components
│   │   │   │   ├── admin/
│   │   │   │   ├── autointel/
│   │   │   │   ├── common/          # Modals, buttons, dropdowns, tables
│   │   │   │   ├── layout/          # Consolidated single layout component & top menu
│   │   │   │   ├── posts-hub/
│   │   │   │   └── zip-farming/
│   │   │   ├── hooks/               # Custom React hooks (useUser, useFeatureStatus)
│   │   │   ├── lib/                 # Client utilities (timezone.utils, fetchers)
│   │   │   └── middleware.ts        # Next.js auth & route protection middleware
│   │   ├── next.config.js
│   │   ├── tailwind.config.js
│   │   └── package.json
│   │
│   ├── workers/                     # BullMQ Async Microservice
│   ├── cron/                        # Scheduled Automation Engine (40+ tasks)
│   ├── mls-gateway/                 # MLS Grid Proxy & Compliance Service
│   └── depth-service/               # Python ONNX Depth Estimation Microservice
│
├── libraries/                       # Shared Internal Packages
│   ├── nestjs-libraries/            # Shared NestJS services, Prisma client & repositories
│   ├── helpers/                     # Shared utilities, crypto, formatting, math
│   └── react-shared-libraries/      # Shared React components, design system tokens
│
├── scripts/                         # Automation & Operational Tooling
│   ├── ci/                          # Contract tests & validation
│   ├── dev/                         # Local development startup scripts
│   │   ├── start-local.ps1          # Windows one-click local launcher
│   │   └── stop-local.ps1           # Windows one-click local teardown
│   ├── migrations/                  # Categorized SQL migrations & DB sync scripts
│   └── seed/                        # Database seeders (superadmin, pricing, offerings)
│
├── docs/                            # Platform Documentation & Management Reports
├── .env.example                     # Clean environment variable template
├── docker-compose.local.yml         # Local Redis & PgBouncer containers
├── pnpm-workspace.yaml              # Monorepo workspace configuration
└── README.md                        # Master onboarding and developer guide
```

---

## 4. File Relocation and Cleanup Matrix

| Current Path | Proposed Action | Target Path / Note |
| :--- | :--- | :--- |
| `apps/frontend/components/video-playground/` | **DELETE** | Legacy duplicate of `video-playgrounds/` |
| `apps/frontend/components/video-playgrounds/` | **MOVE** | `apps/frontend/src/components/video-playgrounds/` |
| `apps/frontend/lib/timezone.utils.ts` | **MOVE** | `apps/frontend/src/lib/timezone.utils.ts` |
| `apps/frontend/src/pages/api/media/` | **CONVERT** | `apps/frontend/src/app/api/media/route.ts` (Remove Pages router) |
| `autosocial.pem`, `autosocial-runner.pem`, `autosocial-jenkins.pem` | **REMOVE FROM GIT** | Add `*.pem` to `.gitignore`; distribute securely via AWS SSM / Vault |
| `leep 5`, `ql`, `ubprocess`, `ma-generate`, etc. | **DELETE** | Remove temporary command output files from root |
| 15+ standalone `*.sql` files in root | **MOVE** | `scripts/migrations/` |
| 10+ standalone `*.sh` scripts in root | **MOVE** | `scripts/dev/` or `scripts/maintenance/` |
