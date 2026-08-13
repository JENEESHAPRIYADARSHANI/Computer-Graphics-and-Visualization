# SAMS frontend

React (Vite) web UI for the Student Attendance Management System. Talks to
the FastAPI backend in `../api.py` over `/api/*` (proxied to `localhost:8010`
in dev, see `vite.config.js`).

```bash
npm install
npm run dev      # dev server with hot reload
npm run build    # production build -> dist/ (served by api.py if present)
```

See the root `README.md` for how to run this together with the backend.
