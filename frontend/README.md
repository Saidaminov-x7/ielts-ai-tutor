# IELTS Mini App frontend

## Local development

From this directory, install the locked dependencies and start Vite:

```sh
npm ci
npm run dev
```

Vite serves the client on port `5173` and proxies `/api` requests to the Python service at `http://localhost:8080`. Start the backend separately with its usual configuration. The app uses the Telegram Mini App `initData` value for every API request; opening the page in a regular browser without Telegram does not create a development identity or bypass authentication.

## Checks and production assets

```sh
npm run typecheck
npm run build
```

The production build is written to `frontend/dist`. It is designed to be served by the Python service on the same HTTPS origin as `/api/v1`.
