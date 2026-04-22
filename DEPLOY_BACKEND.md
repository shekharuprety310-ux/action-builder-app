# Backend Deployment (for Vercel frontend)

This app's PDF generation and SharePoint relay use `variation_pdf_server.py`.
If your frontend is on Vercel, host this Python backend separately and paste its URL into **PDF Server URL** in the app.

## Option A: Render (recommended)

1. Push this repo to GitHub (already done).
2. In Render, click **New +** -> **Blueprint**.
3. Select your repo.
4. Render will detect `render.yaml`.
5. Deploy.
6. After deploy, open:
   - `https://<your-render-service>.onrender.com/health`
   - Expect JSON with `"ok": true`.
7. In your Vercel app:
   - Set **PDF Server URL** to `https://<your-render-service>.onrender.com`
8. Test:
   - **Generate Final PDF (Server)**
   - **Generate PDF -> SharePoint (Power Automate)**

## Option B: Railway

1. Create a new project from this GitHub repo.
2. Set service to use:
   - Build: `pip install -r requirements-variation-pdf.txt`
   - Start: `gunicorn variation_pdf_server:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120`
3. Deploy and copy public URL.
4. Use that URL in **PDF Server URL** in the frontend.

## Important for Power Automate

If your HTTP trigger is tenant-protected, Microsoft may return 401/403 unless:
- your flow URL supports anonymous invoke (often includes `sig=...`), or
- you provide a valid Bearer token (scope `https://service.flow.microsoft.com/.default`).

The backend already has detailed error hints for this case.

## Notes

- Keep the frontend on Vercel (static hosting).
- Keep backend on Render/Railway (Python runtime).
- Do not use `http://127.0.0.1:8787` for team usage; use deployed backend URL.
