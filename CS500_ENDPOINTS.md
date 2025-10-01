# 🎮 CS500 Scraper API Endpoints

Complete guide to the CS500 scraping endpoints.

## 📋 Available Endpoints

### 1. **Full CS500 Scrape** (Recommended) ⭐

**Endpoint**: `POST /api/scrape/cs500-full`

**What it does**:

1. Runs browser automation to collect match IDs from CS500
2. Scrapes markets for those match IDs
3. Stores everything in database

**Use when**: You want the complete CS500 scraping flow in one call

**Example Response**:

```json
{
  "status": "success",
  "message": "Full CS500 scrape complete: 15 match IDs, 120 markets",
  "match_ids_count": 15,
  "markets_count": 120,
  "match_ids": ["123456", "789012", ...]
}
```

**Testing with curl**:

```bash
curl -X POST http://localhost:8000/api/scrape/cs500-full
```

---

### 2. **Match IDs Only**

**Endpoint**: `POST /api/scrape/cs500-matchids`

**What it does**:

- Runs browser automation to collect match IDs only
- Stores match IDs in database

**Use when**: You only want to update match IDs without scraping markets

**Example Response**:

```json
{
  "status": "success",
  "message": "Scraped 15 CS500 match IDs successfully",
  "match_ids_count": 15,
  "match_ids": ["123456", "789012", ...]
}
```

---

### 3. **Markets Only**

**Endpoint**: `POST /api/scrape/cs500`

**What it does**:

- Scrapes markets using existing match IDs in database
- Does NOT run browser automation

**Use when**: You already have match IDs and just want to update markets

**Example Response**:

```json
{
  "status": "success",
  "message": "Scraped 120 CS500 markets",
  "count": 120
}
```

---

## 🌐 Testing with Proxy

Once you've added the proxy to Railway:

```bash
# Set locally for testing
export PROXY_SERVER=http://216.26.250.98:3129

# Or on Windows
$env:PROXY_SERVER="http://216.26.250.98:3129"

# Then test
curl -X POST http://localhost:8000/api/scrape/cs500-full
```

---

## 🖱️ UI Buttons

### Main Page (`/`)

1. **"🎮 CS500 Full Scrape"** button

   - Calls `/api/scrape/cs500-full`
   - Runs complete flow (match IDs + markets)
   - Takes 1-2 minutes
   - **Use this to test proxy!**

2. **"📝 CS500 Markets Only"** button
   - Calls `/api/scrape/cs500`
   - Only scrapes markets (no browser automation)
   - Faster but requires existing match IDs

---

## ✅ Testing Checklist

### Local Testing (Before Railway):

```bash
# 1. Start your server
python main.py

# 2. Test the endpoint
curl -X POST http://localhost:8000/api/scrape/cs500-full

# 3. Check for proxy logs
# Look for: "🌐 Using proxy: http://..."
```

### Railway Testing:

1. **Add environment variables**:

   ```
   DATABASE_PATH=/data/esports_betting.db
   PROXY_SERVER=http://216.26.250.98:3129
   ```

2. **Create volume**: Mount path `/data`

3. **Deploy and check logs**:

   ```
   🌐 Using proxy: http://216.26.250.98:3129
   🌐 Browser configured with proxy: http://216.26.250.98:3129
   🎮 Starting CS500 match ID scraper (browser automation)
   ```

4. **Test via UI**:

   - Go to your Railway URL
   - Click "🎮 CS500 Full Scrape"
   - Wait 1-2 minutes
   - Should see success message

5. **Test via API**:
   ```bash
   curl -X POST https://your-app.up.railway.app/api/scrape/cs500-full
   ```

---

## 🐛 Troubleshooting

### Error: "Failed to start browser"

- ✅ Check Xvfb is running (in Docker)
- ✅ Verify Dockerfile has Chrome/Chromium installed
- ✅ Check Railway logs for display errors

### Error: "No match IDs found"

- ⚠️ CS500 might be blocking your IP/proxy
- ⚠️ CS500 might be down
- ⚠️ No matches available for CS2/LoL

### Proxy not working:

1. Check proxy format: `http://IP:PORT`
2. Verify proxy is online
3. Test proxy independently:
   ```bash
   curl --proxy http://216.26.250.98:3129 https://ipinfo.io
   ```
4. Look for proxy logs in Railway:
   ```
   🌐 Using proxy: http://...
   🌐 Browser configured with proxy: http://...
   ```

### Browser automation timing out:

- Increase timeout in scraper settings
- Check if proxy is slow
- Verify CS500 website is accessible

---

## 🎯 Recommended Workflow

### Development:

1. Use "🎮 CS500 Full Scrape" button to test
2. Check browser automation works
3. Verify data is stored in database

### Production (Railway):

1. Set up proxy as environment variable
2. Create volume for database
3. Let auto-scraper run on schedule
4. Manually trigger "Full Scrape" if needed

---

## 📊 Monitoring

Check Railway logs for:

- ✅ Proxy detection: `🌐 Using proxy:`
- ✅ Browser start: `Starting CS500 match ID scraper`
- ✅ Match IDs collected: `✅ Collected X match IDs`
- ✅ Markets scraped: `✅ Scraped X markets`
- ❌ Errors: `❌ CS500 scraping failed:`

---

**Pro Tip**: Use the "🎮 CS500 Full Scrape" button on your Railway deployment to test if the Canadian proxy works!
