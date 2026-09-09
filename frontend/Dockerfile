# Static-only deploy — this service serves *just* the built SPA, nothing
# else. Split out from the single-container mode (backend/app/main.py still
# supports mounting frontend/dist/ itself for local/single-service use) so a
# frontend-only change (copy, styling, a new component) never restarts the
# backend process and forces it to reload the multi-GB TTS models back into
# memory — the real, observed cost of the old one-container deployment.
#
# VITE_API_BASE_URL is a *build-time* value (Vite inlines `import.meta.env.*`
# at build time, there is no runtime env var to read once this is a static
# bundle) — set it as a Railway service Variable on this frontend service to
# the backend service's public URL, e.g.
# https://lahgtna-tts-production.up.railway.app (no trailing /api — the
# frontend's own api/client.ts appends that). Left unset, it defaults to ""
# (empty string), which keeps every request relative ("/api/...") — correct
# for local dev (Vite's own proxy) and for the old same-origin single-service
# mode, wrong for this split deploy, which is why it must be set here.

FROM node:22-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

# ---------- Stage 2: static file server ----------
# `serve` (Vercel's own static-file server) over nginx: no template/envsubst
# gymnastics needed to make it honor Railway's injected $PORT, and this repo
# has no other nginx config to maintain. This app has no client-side router
# (see frontend/package.json — no react-router), so no SPA-fallback rewrite
# rule is needed; `serve -s` still enables it defensively for a future route.
FROM node:22-slim AS runtime
WORKDIR /app
RUN npm install -g serve@14
COPY --from=build /app/dist ./dist

# Railway injects $PORT; `serve` reads $PORT itself when -l/--listen isn't
# given a fixed value, so this single CMD works both on Railway and for a
# local `docker run -e PORT=3000`.
ENV PORT=3000
EXPOSE 3000
CMD ["sh", "-c", "serve -s dist -l ${PORT:-3000}"]
