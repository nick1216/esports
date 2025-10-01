# ✅ Railway Deployment Checklist

## Before You Deploy

- [ ] All files are saved and committed
- [ ] `requirements.txt` includes all dependencies
- [ ] Database file (`.db`) is in `.gitignore` (already done ✓)
- [ ] No hardcoded secrets or API keys

## Files Created ✓

All deployment files are ready:

- ✅ `Dockerfile` - Builds your app container
- ✅ `start.sh` - Starts Xvfb and FastAPI
- ✅ `railway.json` - Railway configuration
- ✅ `railway.toml` - Alternative config format
- ✅ `.dockerignore` - Excludes unnecessary files
- ✅ `.gitignore` - Keeps secrets safe
- ✅ `README.md` - Project documentation
- ✅ `DEPLOY.md` - Deployment guide
- ✅ `requirements.txt` - Python dependencies (already existed ✓)

## Deployment Steps

### 1. Push to GitHub

```bash
# If you haven't initialized git yet:
git init

# Add all files
git add .

# Commit
git commit -m "Ready for Railway deployment"

# Add your GitHub repository
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git

# Push to GitHub
git push -u origin main
```

**Note**: Replace `YOUR_USERNAME` and `YOUR_REPO` with your actual GitHub details.

### 2. Deploy on Railway

1. Go to: https://railway.app
2. Click "Sign up" → Use GitHub
3. Click "New Project"
4. Select "Deploy from GitHub repo"
5. Choose your repository
6. Wait 3-5 minutes ⏰

### 3. Verify Deployment

- [ ] Check logs for "✅ Xvfb is ready!"
- [ ] Check logs for "Uvicorn running"
- [ ] Visit your Railway URL
- [ ] Test the Markets page
- [ ] Try scraping data

## Post-Deployment

### First Steps in Your App

1. [ ] Visit your app URL (e.g., `your-app.up.railway.app`)
2. [ ] Click "Scrape All" to get initial market data
3. [ ] Wait a few minutes for data to populate
4. [ ] Check that markets appear on the dashboard
5. [ ] Try placing a test bet
6. [ ] Check the Bet Logs page
7. [ ] Verify the Archive page works

### Enable Automatic Scraping (Optional)

**Option A: Built-in Scheduler (Recommended)**

- Your app automatically scrapes every 5 minutes
- No additional setup needed!
- Check logs to verify it's working

**Option B: Railway Cron Job**

1. In Railway dashboard: Click "+ New" → "Cron Job"
2. Schedule: `*/5 * * * *`
3. Command: `python run_cs500_scraper.py`

### Monitor Your App

- [ ] Bookmark your Railway URL
- [ ] Check logs regularly (first few days)
- [ ] Monitor RAM usage (should be < 512MB)
- [ ] Verify scraper is running every 5 minutes

## Common Issues & Solutions

### Issue: App won't start

- **Check**: Logs for error messages
- **Solution**: Ensure all files were pushed to GitHub

### Issue: Database errors

- **Check**: Logs for database-related errors
- **Solution**: Database auto-creates on first run, just wait

### Issue: Browser automation fails

- **Check**: Logs for "Xvfb" errors
- **Solution**: Ensure Dockerfile installed all Chrome dependencies

### Issue: Out of memory

- **Check**: Railway dashboard → Metrics
- **Solution**: Upgrade to 1GB RAM in Railway settings (~$2/month extra)

## Useful Commands

### View Logs

```
Railway Dashboard → Your Service → Deployments → Latest → View Logs
```

### Redeploy

```
git add .
git commit -m "Update"
git push
```

Railway auto-deploys on push!

### Manual Trigger (Railway CLI - Optional)

```
railway up
```

## Cost Breakdown

- **First Month**: FREE ($5 credit)
- **After**: $5-7/month
  - Base: $5/month (512MB RAM)
  - Recommended: +$2 for 1GB RAM
  - Total: ~$7/month

## Success Indicators ✓

Your deployment is successful when:

- ✅ Railway shows "Active" status
- ✅ Logs show no errors
- ✅ Can access your app URL
- ✅ Markets page loads
- ✅ Can scrape and see data
- ✅ Database persists between requests
- ✅ Bets can be placed and tracked

## Support Resources

- **Railway Discord**: https://discord.gg/railway (FAST responses!)
- **Railway Docs**: https://docs.railway.app
- **This Project's Guide**: See `DEPLOY.md` and `RAILWAY_DEPLOYMENT.md`

## Next Steps

After successful deployment:

1. [ ] Set up automatic scraping schedule
2. [ ] Configure notifications (Railway → Settings)
3. [ ] Consider custom domain (optional)
4. [ ] Start tracking real bets!
5. [ ] Monitor CLV and EV metrics

---

## Ready to Deploy?

**Current Status**: All files created ✓

**Next Action**: Push to GitHub and deploy on Railway!

```bash
git add .
git commit -m "Ready for deployment"
git push
```

Then go to [railway.app](https://railway.app) and click "New Project"!

🚀 **Good luck! You're ready to go live!** 🚀
