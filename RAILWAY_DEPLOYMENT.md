# Deploying to Railway

## Why Railway?

- **Best value**: $5/month for 1GB+ RAM (vs Render's $7)
- **Easy setup**: Push to GitHub, one-click deploy
- **Built-in cron**: Easy scheduled tasks
- **Better performance**: Faster builds, no cold starts

## 🚀 Deployment Steps

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-github-repo-url>
git push -u origin main
```

### 2. Deploy to Railway

1. Go to [Railway.app](https://railway.app)
2. Sign up with GitHub
3. Click **"New Project"**
4. Select **"Deploy from GitHub repo"**
5. Choose your repository
6. Railway will automatically detect the Dockerfile

### 3. Add Environment Variables

In Railway dashboard:

- Click your service
- Go to **"Variables"** tab
- Add:
  - `DISPLAY` = `:99`
  - `PORT` = `8000`

### 4. Set Up Cron Job for CS500 Scraper

Option A: Use Railway Cron (Recommended)

1. In Railway dashboard, click **"+ New"**
2. Select **"Cron Job"**
3. Configure:
   - **Schedule**: `*/5 * * * *` (every 5 minutes)
   - **Command**: `sh -c "Xvfb :99 -screen 0 1920x1080x24 & sleep 2 && python run_cs500_scraper.py"`
   - **Environment**: Same as web service

Option B: Use Built-in Scheduler (in your app)

- Your app already has scheduler functionality in `api.py`
- Just enable it from the web UI after deployment

### 5. Deploy!

Railway will automatically:

- ✅ Build your Docker image
- ✅ Deploy your web service
- ✅ Set up cron jobs
- ✅ Give you a public URL

## 📊 Monitoring

Railway provides:

- **Logs**: Real-time logs for debugging
- **Metrics**: CPU, RAM, Network usage
- **Deployments**: History of all deployments
- **Build logs**: See Docker build progress

## 💰 Pricing

**Hobby Plan**: $5/month

- 512MB RAM (upgradable)
- 8GB storage
- Unlimited builds
- Unlimited deployments
- **First $5 FREE** (new accounts)

For your app with browser scraping:

- **Estimated**: $5-8/month
- May need to upgrade RAM to 1GB ($2 extra)

## 🔧 Advanced Configuration

### Persistent Storage

Add to `railway.json`:

```json
{
  "deploy": {
    "volumes": [
      {
        "mountPath": "/app/data",
        "name": "esports-data"
      }
    ]
  }
}
```

Then update database path to `/app/data/esports_betting.db`

### Custom Domain

1. Go to **"Settings"** → **"Domains"**
2. Add your domain
3. Update DNS records

### Health Checks

Railway automatically monitors your `/` endpoint.
For custom health check, add to `railway.json`:

```json
{
  "deploy": {
    "healthcheckPath": "/api/stats",
    "healthcheckTimeout": 100
  }
}
```

## 🆚 Railway vs Render

| Feature    | Railway    | Render        |
| ---------- | ---------- | ------------- |
| Price      | $5/mo      | $7/mo         |
| RAM        | 512MB+     | 512MB         |
| Setup      | Easy       | Easy          |
| Build time | Faster     | Slower        |
| Free tier  | No         | Yes (limited) |
| Cron jobs  | Included   | Included      |
| Best for   | Production | Testing       |

## 🚂 Getting Started NOW

1. **Sign up**: [railway.app](https://railway.app)
2. **Connect GitHub**: One click
3. **Deploy**: Select your repo
4. **Done**: Get your URL in 5 minutes

Railway gives you **$5 free credit** to start, so you can test it for free for a month!

## 📝 Files Needed

You already have everything:

- ✅ `Dockerfile` (ready)
- ✅ `start.sh` (ready)
- ✅ `railway.json` (just created)
- ✅ All your Python files

Just push to GitHub and deploy!

## 🔗 Useful Links

- [Railway Docs](https://docs.railway.app)
- [Railway CLI](https://docs.railway.app/develop/cli) (optional)
- [Railway Templates](https://railway.app/templates)
- [Railway Discord](https://discord.gg/railway) (great support!)
