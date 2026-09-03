# AutoSocial — Enterprise AI Marketing & Operating System for Real Estate

AutoSocial is a comprehensive, multi-tenant AI marketing automation and business operating platform engineered specifically for modern real estate brokerages and agents. It consolidates social media management, automated hyperlocal market updates, territorial ZIP farming, Facebook Lead Ads, AI voice receptionists, virtual 3D room staging, and client websites into a unified, autonomous ecosystem.

---

## 🏗️ High-Level Architecture

AutoSocial is designed as a high-throughput, event-driven monorepo managed with `pnpm` workspaces:

```
                          ┌───────────────────────────┐
                          │   Next.js 15 Frontend     │
                          │   (Port 4200 - App Router)│
                          └─────────────┬─────────────┘
                                        │ REST / WebSockets
                                        ▼
┌─────────────────────────┐       ┌───────────────────────────┐       ┌─────────────────────────┐
│       Apps / Cron       │       │       NestJS Backend      │       │     Apps / Workers      │
│  (40+ Scheduled Jobs)   │◄─────►│    (Port 3000 REST API)   │◄─────►│   (BullMQ Microservice) │
└───────────┬─────────────┘       └─────────────┬─────────────┘       └───────────┬─────────────┘
            │                                   │                                 │
            └─────────────────────────┬─────────┴─────────────────────────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼                                               ▼
  ┌───────────────────────┐                       ┌───────────────────────┐
  │   PgBouncer (6432)    │                       │     Redis (6379)      │
  │   PostgreSQL RDS      │                       │   BullMQ Queues & WS  │
  └───────────────────────┘                       └───────────────────────┘
```

### Application Services Summary
- **`apps/backend`**: Core NestJS REST & WebSocket API, business rules, Stripe billing, and integrations.
- **`apps/frontend`**: Next.js 15 App Router web application containing all agent, client, and administrative portals.
- **`apps/workers`**: Dedicated NestJS microservice processing asynchronous BullMQ queue jobs (video generation, media uploads, ad sync).
- **`apps/cron`**: Scheduled runner orchestrating 40+ background routines (social post publishing, MLS sync, Retell voice processing, billing rollups).
- **`apps/mls-gateway`**: Independent Fastify/Express compliance gateway that acts as the secure proxy to the national MLS Grid API.
- **`apps/depth-service`**: Standalone Python FastAPI microservice utilizing ONNX `Depth-Anything-Small` for 3D depth-map estimation.

---

## 💻 Tech Stack

### Frontend
- **Framework**: Next.js 15 (React 19, TypeScript)
- **Routing**: Next.js App Router with Route Handlers
- **Styling**: Tailwind CSS, SCSS, Mantine UI, BlueprintJS Icons
- **State & Data Fetching**: SWR, Custom Fetch Utilities, React Context
- **AI & Rich Media**: CopilotKit, Three.js / WebGL, Retell Web Client SDK

### Backend & Infrastructure
- **Runtime**: Node.js 20 LTS
- **API Framework**: NestJS 11 (Express-based), Swagger / OpenAPI
- **Database & ORM**: PostgreSQL, Prisma ORM 6.5.0, PgBouncer (Connection Pooling)
- **Queues & Cache**: Redis 7, BullMQ, Bottleneck (Rate Limiting)
- **External AI Providers**: OpenAI (GPT-4o, DALL-E 3), Google Gemini, Retell AI (Voice), Kling 3.0, Grok
- **Data Integrations**: MLS Grid API, RentCast API, Meta Graph API (Facebook & Instagram), Stripe Connect

---

## 📦 The Five Portals & Functional Modules

### 1. Agent Marketing & Social Hub
- **Routes**: `/posts-hub`, `/hyperlocal`, `/media`, `/calendar`
- **Purpose**: Autonomous content creation and scheduled publishing across Facebook, Instagram, LinkedIn, X, TikTok, YouTube, and Pinterest.
- **Features**: Weekly automated hyperlocal market infographics, product offerings showcase, Canva-style media editor, and two-way Google Calendar event synchronization.

### 2. ZIP Farming & Lead Generation Portal
- **Routes**: `/zip-farming`, `/reserve-your-zip`
- **Purpose**: Exclusive geographical market claiming and automated ad management.
- **Features**: Exclusive ZIP code territory locking, automated Meta Lead Ads campaigns, MLS open house collage generation, and instant lead CRM attribution.

### 3. AI Intelligence Portal (AutoIntel: AutoVoice & AutoStaging)
- **Routes**: `/autointel`, `/agents`, `/video-playgrounds`
- **Purpose**: Deep AI multi-modal real estate tooling.
- **Features**:
  - **AutoVoice**: Autonomous 24/7 AI phone receptionist powered by Retell AI with live caller qualification and hot-lead detection.
  - **AutoStaging**: Virtual furniture placement, photo decluttering, and 3D WebGL walkthrough generation using neural depth estimation.
  - **Copilot**: Interactive conversational assistant with custom real estate prompts and video generation playgrounds.

### 4. Public Client & Buyer Engagement Portal
- **Routes**: `/agent-site`, `/agent-directory`, `/3d-tour/[id]`, `/homes/[slug]`
- **Purpose**: High-converting public client portals and listing showcases.
- **Features**: Dynamic agent branded landing pages, responsive 3D tour viewer, interactive buyer concierge inquiry sessions, and CAN-SPAM compliant unsubscribe handling.

### 5. SuperAdmin Mission Control
- **Routes**: `/admin`, `/mission-control`
- **Purpose**: Multi-tenant platform governance, monetization, and system telemetry.
- **Features**: Tenant management and organization impersonation, Stripe Connect split fee configurations, usage-based wallet auto-topup management, MLS Gateway rate limiting, and lifecycle email automation.

---

## ⚙️ Prerequisites

Ensure the following tools are installed on your host machine:

- **Node.js**: Version `20.x` LTS *(Recommended: Install via `fnm` or `nvm`)*.
  *Note: Node 20 is required for prebuilt `canvas` native module support on Windows without C++ compiler tools.*
- **pnpm**: Version `10.6.1` (`npm install -g pnpm@10.6.1`)
- **OpenSSH**: Windows OpenSSH client or Linux/macOS SSH
- **PostgreSQL Client / psql**: (Optional, for manual query inspection)

---

## 🔐 Environment Configuration

Create a `.env` file in the root directory by copying the template:

```bash
cp .env.example .env
```

### Critical Environment Variables

```env
# Application Environment
APP_ENV=local
NODE_ENV=development

# URL Configuration
MAIN_URL=http://localhost:4200
FRONTEND_URL=http://localhost:4200
NEXTAUTH_URL=http://localhost:4200
NEXT_PUBLIC_BACKEND_URL=http://localhost:3000
NEXT_PUBLIC_WS_URL=http://localhost:3000
BACKEND_INTERNAL_URL=http://localhost:3000

# Database Configuration (via PgBouncer Tunnel)
DATABASE_URL=postgresql://postgres:autosocial-database@localhost:6432/autosocial_dev?schema=public&connection_limit=50&pool_timeout=60&connect_timeout=30&sslmode=disable

# Direct PostgreSQL Fallback (Direct RDS Tunnel)
# DATABASE_URL=postgresql://postgres:autosocial-database@localhost:5433/autosocial_dev?sslmode=require&schema=public

# Redis Configuration (via Tunnel or Local Docker)
REDIS_URL=redis://localhost:6379
REDIS_HOST=localhost
REDIS_PORT=6379

# Security & Secrets
JWT_SECRET=supersecretjwtkeythatisatleast32characterslong!
NEXTAUTH_SECRET=superlongrandomstring1234567890abcdef

# AI & Third-Party API Keys
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
RETELL_API_KEY=key_...
STRIPE_SECRET_KEY=sk_test_...
```

---

## 🚀 Local Development Setup & Execution

### 1. Install Workspace Dependencies

Using Node 20 LTS:

```bash
# Verify Node version is 20.x
node -v

# Install dependencies across all monorepo apps and libraries
pnpm install
```

### 2. Generate Prisma Client

```bash
pnpm run prisma-generate
```

### 3. Establish Remote Services Tunnel (RDS, PgBouncer & Redis)

If developing against the cloud development database and Redis instance:

```powershell
# On Windows PowerShell:
Start-Process -FilePath "ssh" -ArgumentList "-4", "-i", "autosocial.pem", `
    "-L", "127.0.0.1:6432:127.0.0.1:6432", `
    "-L", "127.0.0.1:6379:192.168.64.2:6379", `
    "-L", "127.0.0.1:5433:autosocial-db-restored.c2lsueui04qd.us-east-1.rds.amazonaws.com:5432", `
    "-o", "ServerAliveInterval=30", `
    "-o", "ExitOnForwardFailure=yes", `
    "-N", "ec2-user@52.205.155.200" -WindowStyle Hidden
```

Alternatively, run local infrastructure using Docker:

```bash
docker compose -f docker-compose.local.yml up -d
```

### 4. Running Backend and Frontend Independently

#### Run Backend Service (NestJS — Port 3000)
```bash
# From workspace root
pnpm --filter ./apps/backend run dev
```
*Healthcheck:* `http://localhost:3000` (Returns `200 OK`)

#### Run Frontend Application (Next.js — Port 4200)
```bash
# From workspace root
pnpm --filter ./apps/frontend run dev
```
*Access UI:* [http://localhost:4200](http://localhost:4200)

#### Run Auxiliary Services (Optional)
```bash
# Background Workers (BullMQ)
pnpm --filter ./apps/workers run dev

# Cron Automation Scheduler
pnpm --filter ./apps/cron run dev

# MLS Grid Gateway (Port 3010)
pnpm --filter ./apps/mls-gateway run dev
```

---

## ⚡ One-Click Startup Scripts (Windows)

To automate starting and stopping the entire local development stack:

- **Start All Services**:
  ```powershell
  .\start-local.ps1
  ```
- **Stop All Services**:
  ```powershell
  .\stop-local.ps1
  ```

---

## 🧪 Testing & Verification

- **Contract Tests**: `pnpm run test:contract:copilot`
- **Unit & Integration Tests**: `pnpm run test`
- **Database Status Check**:
  ```bash
  node -e 'require("dotenv").config(); const { PrismaClient } = require("@prisma/client"); new PrismaClient().user.count().then(c => console.log("Users in DB:", c));'
  ```
