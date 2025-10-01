# 🎮 CS500 Scraper on Railway - Complete Guide

Two ways to run CS500 scraping on Railway: **Button/Endpoint** vs **Cron Job**

---

## 🎯 Option 1: Button/Endpoint (Recommended to Start)

### ✅ What I Just Built

The CS500 endpoint now uses **background tasks** to avoid Railway timeouts!

**How it works:**

1. Click "🎮 CS500 Full Scrape" button
2. Endpoint returns immediately (no timeout!)
3. Scraping runs in background (1-2 minutes)
4. Page auto-refreshes after 2 minutes to show new data

### ✅ Pros

- ✅ Easy to test (just click button)
- ✅ Works on Railway (no timeout issues)
- ✅ Good for manual/on-demand scraping
- ✅ Already implemented!

### ⚠️ Cons

- ⚠️ Requires manual trigger
- ⚠️ Not automatic

### 📋 Setup (Easy!)

1. **Deploy to Railway** (already done if you followed previous steps)
2. **Add environment variables**:
   ```
   DATABASE_PATH=/data/esports_betting.db
   PROXY_SERVER=http://216.26.250.98:3129
   ```
3. **Create volume**: Mount path `/data`
4. **Test**:
   - Go to your Railway URL
   - Click "🎮 CS500 Full Scrape"
   - Wait ~2 minutes
   - Page auto-refreshes with new data

### 📊 Monitoring

Check Railway logs for:

```
🌐 Using proxy: http://216.26.250.98:3129
🎮 Starting full CS500 scrape (match IDs + markets)
Step 1: Collecting match IDs...
✅ Collected 15 match IDs
Step 2: Scraping markets...
✅ Scraped 120 markets
```

---

## 🤖 Option 2: Railway Cron Job (For Automation)

If you want **automatic** scraping on a schedule.

### ✅ Pros

- ✅ Fully automatic
- ✅ Runs on schedule (every 5 mins, hourly, etc.)
- ✅ No manual intervention needed
- ✅ No timeout limits

### ⚠️ Cons

- ⚠️ More complex setup
- ⚠️ Costs Railway credits (even on free tier)
- ⚠️ Requires separate service

### 📋 Setup (Advanced)

#### Method A: HTTP Cron (Easier)

1. **In Railway Dashboard**:

   - Click "New" → "Cron Job"
   - Schedule: `*/5 * * * *` (every 5 minutes)
   - Command: Leave blank
   - HTTP Target: `https://your-app.up.railway.app/api/scrape/cs500-full`
   - Method: `POST`

2. **Done!** Railway will hit your endpoint every 5 minutes

#### Method B: Command Cron (More Control)

1. **Create a simple runner script** (`cron_cs500.py`):

   ```python
   import asyncio
   import requests
   import os

   async def main():
       url = os.getenv("APP_URL", "http://localhost:8000")
       response = requests.post(f"{url}/api/scrape/cs500-full")
       print(f"Status: {response.status_code}")
       print(f"Response: {response.json()}")

   if __name__ == "__main__":
       asyncio.run(main())
   ```

2. **In Railway**:
   - Create new Cron Job
   - Schedule: `*/5 * * * *`
   - Command: `python cron_cs500.py`
   - Add environment variable: `APP_URL=https://your-app.up.railway.app`

---

## 🎯 Which Should You Use?

### Use **Button/Endpoint** (Option 1) if:

- ✅ You want to test first
- ✅ You scrape manually/on-demand
- ✅ You want simpler setup
- ✅ You're just starting out

**→ This is already implemented and ready to go!**

### Use **Cron Job** (Option 2) if:

- ✅ You want fully automatic scraping
- ✅ You need it to run 24/7 without manual intervention
- ✅ You don't mind the extra setup
- ✅ You're ready for production

---

## 💡 Recommended Workflow

### Phase 1: Testing (Use Button)

1. Deploy with button/endpoint
2. Test proxy works
3. Verify data is being scraped
4. Monitor for issues

### Phase 2: Production (Add Cron if needed)

1. Once testing is successful
2. Add Railway Cron Job for automation
3. Keep button for manual override
4. Monitor both systems

---

## 🧪 Testing Your Deployment

### Step 1: Test Endpoint Locally

```powershell
# Set proxy
$env:PROXY_SERVER="http://216.26.250.98:3129"

# Start server
python main.py

# Test endpoint
curl -X POST http://localhost:8000/api/scrape/cs500-full
```

### Step 2: Test on Railway

1. **Via UI**:

   - Go to `https://your-app.up.railway.app`
   - Click "🎮 CS500 Full Scrape"
   - Check logs in Railway dashboard

2. **Via API**:
   ```bash
   curl -X POST https://your-app.up.railway.app/api/scrape/cs500-full
   ```

### Step 3: Check Results

**Expected Response:**

```json
{
  "status": "success",
  "message": "CS500 scraping started in background. Check logs for progress.",
  "note": "This may take 1-2 minutes. Refresh the page to see updated data."
}
```

**Check Railway Logs:**

```
🌐 Using proxy: http://216.26.250.98:3129
🌐 Browser configured with proxy: http://216.26.250.98:3129
🎮 Starting full CS500 scrape (match IDs + markets)
Step 1: Collecting match IDs...
✅ Collected 15 match IDs
Step 2: Scraping markets...
✅ Scraped 120 markets
```

---

## 🐛 Troubleshooting

### "Background task not completing"

- Check Railway logs for errors
- Verify Xvfb is running
- Check if proxy is working

### "No data after 2 minutes"

- Check logs for scraping errors
- Proxy might be blocked
- CS500 might be down
- Try a different proxy

### "Railway timeout error"

- Should NOT happen with background tasks
- If it does, endpoint returns too early
- Check Railway plan limits

### "Proxy not working"

1. Verify `PROXY_SERVER` environment variable is set
2. Check proxy is online: `curl --proxy http://216.26.250.98:3129 https://ipinfo.io`
3. Look for proxy logs: `🌐 Using proxy:`
4. Try a different proxy

---

## 📊 Current Setup Summary

### What You Have Now:

- ✅ **3 CS500 endpoints** (full, match IDs only, markets only)
- ✅ **Background task processing** (no timeouts)
- ✅ **UI button** (easy testing)
- ✅ **Auto-refresh** (shows new data after 2 mins)
- ✅ **Proxy support** (routes through Canada)
- ✅ **Database persistence** (Railway volumes)

### Ready to Deploy:

```bash
git add api.py static/script.js
git commit -m "Add background task processing for CS500 scraper"
git push
```

### On Railway:

1. Create volume: `/data`
2. Add variables:
   - `DATABASE_PATH=/data/esports_betting.db`
   - `PROXY_SERVER=http://216.26.250.98:3129`
3. Deploy
4. Test button!

---

## 🎉 Summary

**Answer to your question**:

✅ **YES, the button will work with Railway!**

I've updated the endpoint to use **background tasks**, so it:

- Returns immediately (no timeout)
- Scrapes in the background
- Auto-refreshes the page after 2 minutes

**Just click the button and check the Railway logs to see progress!** 🚀

If you want fully automatic scraping later, you can add a Railway Cron Job, but the button is perfect for testing and manual use.
