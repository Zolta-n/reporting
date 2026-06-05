# Updating the App After a Code Change

**NAS:** Synology DS225+ · **Access:** QuickConnect (`znponty.cz5.quickconnect.to`) · **App URL:** `https://report.businessintels.com`

---

## Automated deployment (normal workflow)

Every push to GitHub triggers an automatic build and deploy:

```
git push → GitHub Actions builds image → ghcr.io registry updated
                                       → Watchtower on NAS detects new image
                                       → Container restarts automatically
```

**You only need to push. Nothing else.**

Watchtower polls the registry every 5 minutes, so the NAS picks up changes within 5 minutes of a push.

---

## One-time NAS setup (Watchtower)

Do this once. After this, all future updates are automatic.

### Step 1 — Make the GitHub package public

1. Go to `https://github.com/Zolta-n/reporting/pkgs/container/reporting`
2. Click **Package settings**
3. Scroll to **Danger Zone** → Change visibility → **Public**
4. Confirm

This lets Watchtower pull the image without credentials.

### Step 2 — Add Watchtower as a Container Manager project

1. Log into DSM → open **Container Manager → Project → Create**
2. Name: `watchtower`
3. Paste this as the compose content:

```yaml
version: "3.9"

services:
  watchtower:
    image: containrrr/watchtower
    container_name: watchtower
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - WATCHTOWER_POLL_INTERVAL=300
      - WATCHTOWER_CLEANUP=true
      - WATCHTOWER_INCLUDE_STOPPED=false
```

4. On **Web portal settings** — leave checkbox **unchecked**
5. Click **Done**

### Step 3 — Update the reporting project on the NAS

This is the last manual update. After this, Watchtower handles everything.

1. In File Station, navigate to `docker/reporting/` and upload the updated `docker-compose.yml` (the one that now uses `image: ghcr.io/zolta-n/reporting:latest` instead of `build: .`)
2. In Container Manager → delete the existing reporting container/project
3. Create new Project:
   - Name: `reporting`
   - Path: `/volume1/docker/reporting`
4. Web portal settings → leave unchecked → Done

---

## Verifying a deployment

After pushing, check the build completed:

- GitHub → Actions tab → confirm the workflow shows a green tick
- Wait up to 5 minutes for Watchtower to pull and restart
- Open `https://report.businessintels.com` to confirm

---

## Quick reference

| What | Where |
|---|---|
| GitHub repo | `https://github.com/Zolta-n/reporting` |
| Container image | `ghcr.io/zolta-n/reporting:latest` |
| GitHub Actions | Repo → Actions tab |
| DSM login | `znponty.cz5.quickconnect.to` |
| App URL | `https://report.businessintels.com` |
| App port | `8000` |
| Watchtower poll interval | every 5 minutes |

---

## Local development (no NAS)

To build and run locally:

```bash
docker build -t reporting-local .
docker run -p 8000:8000 --env-file .env reporting-local
```
