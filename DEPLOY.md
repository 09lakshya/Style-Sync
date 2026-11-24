# Deploying StyleSync (free tier)

| Piece    | Host                              | Why                                                        |
|----------|-----------------------------------|------------------------------------------------------------|
| Frontend | Vercel                            | Free, global CDN, builds from GitHub on every push         |
| Backend  | Hugging Face Space (Docker)       | Free 2 vCPU / 16 GB RAM: enough for CLIP; sleeps only after 48 h idle |
| Database | TiDB Cloud Serverless (MySQL)     | Free, persistent; the Space's disk is wiped on restart     |
| Images   | Cloudinary                        | Already wired in                                           |

Do the steps in order: the backend URL goes into Vercel, and the Vercel URL goes back into the backend.

## 1. Database: TiDB Cloud Serverless

1. Sign up at https://tidbcloud.com and create a **Serverless** cluster (free).
2. Click **Connect**, choose **General**, and generate a password.
3. Create the database: in the SQL editor, run `CREATE DATABASE stylesync;`
4. Build the URL: replace the `mysql://` scheme with `mysql+aiomysql://`:

   ```
   mysql+aiomysql://<user>:<password>@<host>:4000/stylesync
   ```

   If the password contains `@ : / #`, URL-encode it.

Tables are created automatically the first time the backend starts.

## 2. Backend: Hugging Face Space

1. Sign up at https://huggingface.co and create a token with **Write** access
   (Settings → Access Tokens).
2. Fill in the secrets:

   ```
   cp backend/deploy/env.production.example backend/.env.production   # git-ignored
   ```

   For now, set `FRONTEND_ORIGIN=https://placeholder.vercel.app`. You'll fix it in step 4.
3. Push:

   ```
   pip install huggingface_hub
   huggingface-cli login
   python backend/scripts/deploy_hf_space.py <your-hf-username>/stylesync-api --env-file backend/.env.production
   ```

4. Watch the build at `https://huggingface.co/spaces/<user>/stylesync-api`. The first build takes about 10 minutes
   (torch plus the baked-in CLIP model). When it's done, this should return `{"status":"ok"}`:

   ```
   https://<user>-stylesync-api.hf.space/health
   ```

Re-run the same command after any backend change. Leave off `--env-file` if the secrets haven't changed.

> The Space must be **public** for the browser to reach the API. A public Space shows its
> source code (but never its secrets). If the code must stay private, use a paid
> private Space or another host.

## 3. Frontend: Vercel

1. Push this repo to GitHub, then at https://vercel.com click **Add New → Project** and import it.
2. Set **Root Directory** to `frontend`. `frontend/vercel.json` handles the build settings and SPA routing.
3. Under **Environment Variables**, add:

   ```
   VITE_API_URL = https://<user>-stylesync-api.hf.space/api/v1
   ```

4. Deploy. Note the URL, e.g. `https://stylesync.vercel.app`.

## 4. Connect them

In the Space, open **Settings → Variables and secrets** and set `FRONTEND_ORIGIN` to the Vercel URL
(no trailing slash; separate several URLs with commas). The Space restarts on its own.

## Notes

- **Sleep:** a free Space sleeps after 48 h with no requests, and the first request after that takes about 1 minute.
  A free uptime pinger (e.g. UptimeRobot hitting `/health` every few hours) keeps it awake.
- **Local development is unchanged:** SQLite and `localhost` still work with the existing `.env`.
- **Run the image elsewhere:** `docker build -t stylesync-api backend && docker run -p 7860:7860 --env-file backend/.env.production stylesync-api`
