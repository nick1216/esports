# 🚀 Deploy to Railway - Quick Guide

## Step 1: Push to GitHub

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Ready for Railway deployment"

# Add your GitHub repo
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git

# Push
git push -u origin main
```

## Step 2: Deploy on Railway

1. **Go to**: [railway.app](https://railway.app)
2. **Sign up** with GitHub (free)
3. Click **"New Project"**
4. Select **"Deploy from GitHub repo"**
5. Choose your repository
6. **Done!** Railway auto-detects the Dockerfile

## Step 3: Get Your URL

- Railway will build and deploy automatically (3-5 minutes)
- Click on your project → **"Settings"** → **"Domains"**
- Copy your Railway URL (e.g., `your-app.up.railway.app`)
- Open in browser - your app is live! 🎉

## Step 4: Monitor Deployment

- Click **"View Logs"** to see deployment progress
- Look for: "✅ Xvfb is ready!" and "Starting FastAPI application..."
- Your app is ready when you see: "Uvicorn running on http://0.0.0.0:8000"

## 💰 Cost

- **First $5 FREE** (credit for new accounts)
- **After**: ~$5-7/month
- Cancel anytime, no commitment

## 🔧 Optional: Set Up Automatic Scraping

Your app has built-in scheduling! Just:

1. Open your deployed app
2. Go to Markets page
3. The scraper runs automatically every 5 minutes (configured in the app)

Alternatively, use Railway Cron:

1. In Railway dashboard, click **"+ New"** → **"Cron Job"**
2. Schedule: `*/5 * * * *` (every 5 minutes)
3. Command: `python run_cs500_scraper.py`

## 📊 What Happens After Deploy?

1. ✅ Database is created automatically
2. ✅ Static files are served
3. ✅ API endpoints are live
4. ✅ Browser automation works (headless Chrome)
5. ✅ Scheduler starts automatically

## 🐛 Troubleshooting

### App won't start?

- Check logs for errors
- Verify all files were pushed to GitHub
- Ensure `start.sh` has proper line endings (LF, not CRLF)

### Can't see logs?

- Click your service → **"Deployments"** → Select latest → **"View Logs"**

### Database issues?

- Database is created fresh on first run
- Located at `/app/esports_betting.db`

### Need help?

- [Railway Discord](https://discord.gg/railway) - Very responsive!
- Check [Railway Docs](https://docs.railway.app)

## 🎯 Next Steps After Deployment

1. Visit your app URL
2. Navigate to Markets page
3. Click "Scrape All" to get initial data
4. Place your first bet!
5. Check Bet Logs and Archive pages

## 🔗 Your Live App Structure

```
https://your-app.railway.app/
├── /                  # Markets dashboard
├── /bets             # Bet tracking
├── /archive          # Historical matches
└── /api/*            # API endpoints
```

## 💡 Pro Tips

1. **Bookmark your URL** - Railway URLs are long
2. **Check logs regularly** - Monitor scraping
3. **Enable notifications** - Railway can notify on failures
4. **Set up custom domain** (optional) - Settings → Domains

---

**That's it! You're live in production! 🚀**

Questions? Issues? Check the Railway docs or their Discord!
