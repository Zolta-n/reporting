# Updating the App After a Code Change

**NAS:** Synology DS225+ · **Access:** QuickConnect (`znponty.cz5.quickconnect.to`) · **App URL:** `https://report.businessintels.com`

---

> **Important:** The Dockerfile uses `COPY . .` — source files are baked into the image.
> A full rebuild is required for every code change. Restarting the container alone is not sufficient.

---

## Step 1 — Download the changed files from Codespaces

Open the project in Codespaces. In the VS Code file explorer, right-click each changed file and choose **Download**. Save to your local machine.

Common files to update:

| File | Location on NAS |
|---|---|
| `backend/reports/weekly.py` | `docker/reporting/backend/reports/` |
| `backend/reports/monthly.py` | `docker/reporting/backend/reports/` |
| `backend/main.py` | `docker/reporting/backend/` |
| `frontend/app.js` | `docker/reporting/frontend/` |
| `frontend/index.html` | `docker/reporting/frontend/` |

---

## Step 2 — Upload to the NAS via File Station

1. Log into DSM at `znponty.cz5.quickconnect.to`
2. Open **File Station**
3. Navigate to `docker/reporting/` and into the subfolder matching the changed file
4. Click **Upload** → select the downloaded file → confirm **Overwrite**

---

## Step 3 — Rebuild and restart via Container Manager

Open **Container Manager**.

**If a `reporting` project already exists under Project:**

1. Click the `reporting` project
2. Click **Action → Rebuild**
3. Click **Start**

**If no project exists (app running as standalone Container):**

1. Go to **Container** → stop and delete the existing reporting container
2. Go to **Project → Create**
3. Fill in:
   - Name: `reporting`
   - Path: `/volume1/docker/reporting`
4. Container Manager detects `docker-compose.yml` automatically — click **Next**
5. On **Web portal settings** — leave checkbox **unchecked** → click **Next**
6. Click **Done** — image builds and container starts automatically

---

## Step 4 — Verify

Open `https://report.businessintels.com` and confirm the app loads. Generate a report to verify the change is live.

---

## Quick Reference

| What | Where |
|---|---|
| DSM login | `znponty.cz5.quickconnect.to` |
| App source on NAS | `/volume1/docker/reporting/` |
| App URL | `https://report.businessintels.com` |
| App port | `8000` |
| Cloudflare tunnel | Container Manager → Project → `cloudflare` |
