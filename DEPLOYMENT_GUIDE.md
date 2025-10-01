# 🚀 Railway Deployment Guide - Playwright Integration

## ✅ What Was Updated

The application now uses **two separate scrapers**:

1. **`CS500ScraperPlaywright`** - Browser automation for match IDs (uses proxy)
2. **`CS500Scraper`** - API calls for market data (uses proxy)

This separation improves performance and reliability.

---

## 📦 Files Modified for Deployment

### **1. `api.py`**

- ✅ Imported `CS500ScraperPlaywright`
- ✅ Initialized `cs500_playwright_scraper` instance
- ✅ Updated `/api/scrape/cs500-matchids` to use Playwright scraper
- ✅ Updated `/api/scrape/cs500-full` background task to use Playwright scraper
- ✅ Market fetching still uses original `CS500Scraper`

### **2. `Dockerfile`**

- ✅ Added Playwright browser installation: `playwright install --with-deps chromium`
- ✅ Installs Chromium with all required system dependencies

### **3. `requirements.txt`**

- ✅ Already includes `playwright==1.48.0`

### **4. `scraper_playwright.py`**

- ✅ Uses `os.getenv('PROXY_SERVER')` for proxy configuration
- ✅ Handles proxy authentication natively
- ✅ Returns match IDs only

---

## 🔧 Railway Environment Variables

Set these in your Railway dashboard:

### **Required:**

```
PROXY_SERVER=http://username:password@rp.scrapegw.com:6060
```

### **Optional:**

```
DATABASE_PATH=/data/esports_betting.db
PLAYWRIGHT_BROWSER=chromium
```

**Note:** Railway volume should be mounted at `/data` for database persistence.

---

## 🎯 How It Works

### **Architecture:**

```
┌─────────────────────────────────────────┐
│  Railway Deployment                     │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │  FastAPI Application (api.py)     │ │
│  └───────────────────────────────────┘ │
│           │                             │
│           ├─── Match IDs                │
│           │    ↓                        │
│  ┌────────────────────────────────────┐│
│  │  CS500ScraperPlaywright            ││
│  │  • Browser automation (Chromium)   ││
│  │  • Shadow DOM scraping             ││
│  │  • Pagination handling             ││
│  │  • Proxy: PROXY_SERVER env var    ││
│  └────────────────────────────────────┘│
│           │                             │
│           └─── Market Data              │
│                ↓                        │
│  ┌────────────────────────────────────┐│
│  │  CS500Scraper                      ││
│  │  • API calls only                  ││
│  │  • Fast market data fetching       ││
│  │  • Proxy: PROXY_SERVER env var    ││
│  └────────────────────────────────────┘│
│                                         │
│  ┌───────────────────────────────────┐ │
│  │  SQLite Database (/app/data/)     │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

---

## 📋 API Endpoints Using Each Scraper

### **Playwright Scraper (Match IDs):**

- `POST /api/scrape/cs500-matchids` - Collects match IDs via browser
- `POST /api/scrape/cs500-full` - Full workflow (uses both scrapers)

### **Original Scraper (Market Data):**

- `POST /api/scrape/cs500` - Fetches markets for existing match IDs
- Background scheduler - Periodic market updates

---

## 🚀 Deployment Steps

### **1. Commit Changes**

```bash
git add .
git commit -m "Add Playwright scraper for CS500 match IDs"
git push origin main
```

### **2. Railway Will Auto-Deploy**

Railway will:

1. Build Docker image with Playwright
2. Install Chromium browser
3. Start the application

### **3. Setup Persistent Volume**

In Railway dashboard → Settings → Volumes:

- Click "New Volume"
- Mount path: `/data`

This ensures your database persists across deployments.

### **4. Set Environment Variables**

In Railway dashboard → Variables:

```
PROXY_SERVER=http://your-username:your-password@rp.scrapegw.com:6060
DATABASE_PATH=/data/esports_betting.db
```

### **5. Test the Deployment**

Once deployed, test these endpoints:

```bash
# Test match ID collection
curl -X POST https://your-railway-app.railway.app/api/scrape/cs500-matchids

# Test full scrape (background task)
curl -X POST https://your-railway-app.railway.app/api/scrape/cs500-full
```

---

## 🐛 Troubleshooting

### **Issue: "playwright: command not found"**

**Solution:** Railway is still building. Wait for deployment to complete.

### **Issue: "Browser executable doesn't exist"**

**Solution:** Check Dockerfile has:

```dockerfile
RUN playwright install --with-deps chromium
```

### **Issue: "Proxy authentication failed"**

**Solution:**

1. Check `PROXY_SERVER` format: `http://username:password@host:port`
2. Verify proxy credentials in ProxyScrape dashboard
3. Whitelist Railway IP if using IP authentication

### **Issue: "No match IDs found"**

**Possible causes:**

1. CS500 has no events currently
2. Proxy is too slow (increase timeouts in `scraper_playwright.py`)
3. Geo-blocking (ensure proxy is Canadian)

---

## 📊 Monitoring

### **Check Logs:**

Railway dashboard → Logs tab

**Look for:**

- `✅ Playwright browser launched (proxy=True)`
- `✅ Collected X match IDs`
- `✅ Scraped X markets`

### **Check IP:**

Visit: `https://your-railway-app.railway.app/api/check-ip`

This shows Railway's outbound IP (for proxy whitelisting).

---

## 💡 Performance Tips

1. **Match ID scraping:** Runs in background (~1-2 minutes with proxy)
2. **Market data:** Fast API calls (~5-10 seconds)
3. **Scheduled tasks:** Every 5 minutes for markets, every hour for Pinnacle

---

## ✅ Deployment Checklist

- [x] `api.py` updated to use both scrapers
- [x] `Dockerfile` installs Playwright + Chromium
- [x] `requirements.txt` includes Playwright
- [x] `scraper_playwright.py` uses `PROXY_SERVER` env var
- [x] Environment variables set in Railway
- [x] Database path configured for persistent volume
- [x] Static files included in Docker build

---

## 🎉 You're Ready to Deploy!

```bash
git push origin main
```

Railway will automatically build and deploy. Check the dashboard for build logs.

**Test URL:** `https://your-railway-app.railway.app`

---

## 📚 Additional Resources

- **Playwright Docs:** https://playwright.dev/python/
- **Railway Docs:** https://docs.railway.app/
- **ProxyScrape Docs:** https://docs.proxyscrape.com/

---

**Questions?** Check Railway logs or test endpoints manually!
