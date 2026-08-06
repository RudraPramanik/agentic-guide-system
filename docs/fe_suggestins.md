> **Locked subset:** `docs/FE_guide.md` — use that for implementation. This file is the broader brainstorm input only.

Core Stack
Category	Recommendation	Why
Framework	Next.js 16 (App Router)	Industry standard, React Server Components
Language	TypeScript	Required
Styling	Tailwind CSS v4	Fast, modern
Components	shadcn/ui	Most AI startups use it
Icons	Lucide	Lightweight
Animations	Motion	Better React animation library
Forms	React Hook Form + Zod	Standard combination
Validation	Zod	Shared types with backend if needed
Data Fetching	TanStack Query v5	Server state
Tables	TanStack Table	Best data table
Charts	Recharts or Tremor	Dashboards
Date	date-fns	Lightweight
Theme	next-themes	Dark/light mode
Notifications	Sonner	Excellent toast system
AI Specific

These are almost becoming standard.

AI SDK

Use the Vercel AI SDK even if your backend is FastAPI.

Why?

It handles

streaming
chat UI
tool calling
markdown rendering
message state
SSE

Your FastAPI endpoint can stream tokens and the SDK consumes them.

Markdown

For AI answers

react-markdown
remark-gfm
rehype-highlight

Optional

Mermaid support
Latex support
Code Blocks
react-syntax-highlighter

or

Shiki
Chat UI

Use

AI SDK UI
shadcn components

Things users now expect

regenerate
stop generation
copy
edit message
streaming
thinking indicator
citations
sources
reasoning blocks
tool results
attachments
State Management

Don't overuse global state.

Recommended

TanStack Query → server state
Zustand → UI state
React Context → auth/theme only

Avoid Redux unless you truly need it.

Authentication

Since FastAPI owns auth

Frontend

Better Auth client or custom JWT handling
HTTP-only cookies

If social login

OAuth through FastAPI
API Layer

Don't call fetch everywhere.

Create

lib/api.ts

AuthAPI
ChatAPI
NotebookAPI
WorkspaceAPI
UserAPI
TravelAPI

Then wrap with TanStack Query.

Real-Time

AI apps increasingly need streaming.

Use

Server-Sent Events (SSE) for LLM output
WebSockets for collaboration/live presence

FastAPI supports both well.

File Uploads

Use

react-dropzone

Supports

drag drop
images
pdf
docs
audio
Maps (for your travel application)

Since your product is travel based

I'd recommend

MapLibre GL
OpenStreetMap
Mapbox vector tiles if needed

Avoid depending entirely on Google Maps.

Image Optimization

Use

Next/Image

For user uploads

Cloudflare R2
S3
Supabase Storage
AI UX Features

Modern AI products commonly include:

Streaming responses
Optimistic UI
Message editing
Conversation branching
Regeneration
Tool execution display
Progress steps
Citation cards
Artifact panel
Split-screen chat + document
Keyboard shortcuts
Drag-and-drop uploads
Error Handling

Use

error.tsx

loading.tsx

not-found.tsx

global-error.tsx

Add

React Error Boundary
retry buttons
toast notifications
Observability

Frontend

Sentry
Vercel Analytics (if hosted there)
PostHog
OpenTelemetry (optional)
Testing
Vitest
React Testing Library
Playwright
Linting
ESLint
Prettier
Husky
lint-staged
Project Structure
app/

components/
    ui/
    chat/
    sidebar/
    map/
    notebook/

features/
    auth/
    chat/
    notebook/
    travel/
    workspace/

hooks/

lib/
    api/
    auth/
    utils/

services/

store/

types/

providers/

constants/

I generally prefer a feature-first organization over organizing primarily by component type once an application grows