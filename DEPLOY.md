# Deploying StyleSync

| Piece    | Host                                     | Cost                                         |
|----------|------------------------------------------|----------------------------------------------|
| Frontend | Vercel                                   | Free                                         |
| Backend  | Azure VM, Standard B1ms (Docker + Caddy) | About $20/month, from Azure for Students' $100 credit |
| Database | TiDB Cloud Starter (MySQL)               | Free                                         |
| Images   | Cloudinary                               | Free                                         |

The backend needs about 2 GB of RAM for CLIP, which rules out the 512 MB free tiers. A VM
is always on, so there are no cold starts.

## 1. Database: TiDB Cloud Starter

1. At https://tidbcloud.com, create a **Starter** cluster (AWS, `us-east-1`, MySQL compatibility).
2. Under **Networking**, add a rule allowing `0.0.0.0` – `255.255.255.255`. Every connection still needs the
   password and TLS.
3. Click **Connect**, choose **General**, generate a password, and build the URL:

   ```
   mysql+aiomysql://<user>:<password>@<host>:4000/stylesync
   ```

   URL-encode `@ : / # ?` in the password. The backend creates the `stylesync` database's tables on first start
   (create the database itself with `CREATE DATABASE stylesync;`).

## 2. Backend: Azure VM

1. Activate **Azure for Students** (https://azure.microsoft.com/free/students). It gives $100 of credit and needs no card.
2. Create a virtual machine:
   - Image **Ubuntu Server 24.04 LTS (x64)**
   - Region **East US**, the same area as the database
   - Size **Standard_B1ms** (1 vCPU, 2 GiB)
   - Authentication **SSH public key**, username `azureuser`. Choose "Use existing public key" and paste the deploy
     machine's `~/.ssh/id_ed25519.pub`.
   - Inbound ports: **SSH (22), HTTP (80), HTTPS (443)**
   - Disk: **Standard SSD**
   - After creating it, open its **Public IP address** resource and set the assignment to **Static**, so the address
     (and the API URL) never changes.
3. Fill in the secrets:

   ```
   cp backend/deploy/env.production.example backend/.env.production   # git-ignored
   ```

4. One-time server setup (installs Docker, adds swap, sets up the firewall, clones the repo):

   ```
   ssh azureuser@<ip> 'sudo bash -s' < backend/deploy/server_setup.sh
   ```

5. Deploy. Run the same command again for every later update; it pulls `main` from GitHub:

   ```
   bash backend/deploy/deploy_server.sh azureuser@<ip>
   ```

   The first build takes about 10 minutes. The API is then at `https://<ip-with-dashes>.sslip.io/api/v1`.
   sslip.io maps that name to the IP, and Caddy gets a free HTTPS certificate for it automatically.

Logs: `ssh azureuser@<ip> 'cd /opt/stylesync && docker compose -f backend/deploy/docker-compose.yml logs -f api'`

To stop spending credit, **Stop** the VM in the portal. A stopped (deallocated) VM costs only its disk and IP.

## 3. Frontend: Vercel

1. At https://vercel.com, click **Add New → Project** and import the GitHub repo.
2. Set **Root Directory** to `frontend`. `frontend/vercel.json` handles the build settings and SPA routing.
3. Add the environment variable `VITE_API_URL = https://<ip-with-dashes>.sslip.io/api/v1`, then deploy.

## 4. Connect them

Set `FRONTEND_ORIGIN` in `backend/.env.production` to the Vercel URL (no trailing slash; separate several URLs
with commas), then re-run `deploy_server.sh`.

Local development is unchanged: SQLite and `localhost` still work with the existing `.env`.
