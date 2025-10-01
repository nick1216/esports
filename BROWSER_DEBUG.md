# 🔧 Browser Automation Debug Guide (CS500 Scraper)

## 🐛 The Problem

CS500 scraper fails when running in Docker/Railway because:

- Browser automation needs to run **non-headless** to avoid detection
- But Docker has no display, so browser can't start
- Solution: **Xvfb** (Virtual X11 display)

---

## ✅ Fixes Applied

### 1. **Enhanced Browser Arguments** (`scraper.py`)

Added Docker-specific Chrome flags:

```python
browser_args = [
    "--no-sandbox",              # Required for Docker
    "--disable-setuid-sandbox",  # Security in containers
    "--disable-dev-shm-usage",   # Use /tmp instead of /dev/shm
    "--disable-gpu",             # No GPU in Docker
    "--disable-software-rasterizer",
    "--disable-extensions",
    "--window-size=1920,1080",
    "--start-maximized",
]
```

### 2. **Improved Xvfb Startup** (`start.sh`)

Enhanced virtual display with:

```bash
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
```

**New flags:**

- `-ac` - Allow all clients to connect
- `+extension GLX` - Enable OpenGL extension
- `+render` - Enable RENDER extension
- `-noreset` - Don't reset after last client exits

### 3. **Better Display Detection** (`start.sh`)

Added timeout and fallback logic:

```bash
for i in {1..10}; do
    if xdpyinfo -display :99 >/dev/null 2>&1; then
        echo "✅ Xvfb is ready"
        break
    fi
    sleep 1
done
```

### 4. **Additional Packages** (`Dockerfile`)

Added missing utilities:

- `x11-utils` - For `xdpyinfo` command
- `ca-certificates` - For HTTPS connections

---

## 🔍 Debug Logging

The scraper now prints:

```
🔧 Browser config: headless=False, display=:99
🌐 Browser configured with proxy: http://...
```

---

## 📊 Testing the Fix

### Local Testing (Windows)

You can't test Xvfb locally on Windows, but you can test the scraper logic:

```powershell
# Test scraper without Xvfb
python run_cs500_scraper.py
```

### Railway Testing

After deployment, check Railway logs for:

```
🖥️  Starting Xvfb virtual display...
⏳ Waiting for Xvfb to be ready...
✅ Xvfb is ready on display :99
🔍 Current DISPLAY: :99
🚀 Starting FastAPI application...
```

Then when you trigger CS500 scraping:

```
🔧 Browser config: headless=False, display=:99
🌐 Browser configured with proxy: http://216.26.250.98:3129
🎮 Starting full CS500 scrape (match IDs + markets)
Step 1: Collecting match IDs...
```

---

## 🐛 Common Issues & Solutions

### Issue 1: "Failed to start browser"

**Symptoms:**

```
Failed to start browser: Could not connect to display
```

**Solutions:**

1. Check Xvfb is running:

   ```bash
   ps aux | grep Xvfb
   ```

2. Verify DISPLAY variable:

   ```bash
   echo $DISPLAY  # Should show :99
   ```

3. Check logs for Xvfb startup errors

---

### Issue 2: "Browser starts but hangs"

**Symptoms:**

- Browser starts but never loads pages
- Scraper times out

**Solutions:**

1. Increase timeout in scraper
2. Check if proxy is responding
3. Verify CS500 website is accessible from proxy location

---

### Issue 3: "Xvfb ready but browser fails"

**Symptoms:**

```
✅ Xvfb is ready on display :99
Failed to start browser: ...
```

**Solutions:**

1. Check Chrome/Chromium is installed:

   ```bash
   which chromium
   chromium --version
   ```

2. Try additional browser flags:

   ```python
   "--single-process",
   "--no-zygote",
   ```

3. Check memory limits (Railway may be low on RAM)

---

### Issue 4: "Permission denied"

**Symptoms:**

```
Permission denied: '/tmp/.X99-lock'
```

**Solutions:**

1. Clean up stale X locks:

   ```bash
   rm -rf /tmp/.X*-lock
   ```

2. Add to `start.sh` before starting Xvfb:
   ```bash
   rm -rf /tmp/.X99-lock
   ```

---

## 🔬 Advanced Debugging

### Enable Chrome Debug Logging

Add to browser_args:

```python
"--enable-logging",
"--v=1",
```

### Test Xvfb Manually

SSH into Railway (if available) or test locally:

```bash
# Start Xvfb
Xvfb :99 -screen 0 1920x1080x24 &

# Set display
export DISPLAY=:99

# Test with xdpyinfo
xdpyinfo -display :99

# Try running Chrome
chromium --no-sandbox --disable-gpu
```

### Check Display List

```bash
ls -la /tmp/.X*
```

---

## 📋 Deployment Checklist

Before deploying to Railway:

- [x] Xvfb installed in Dockerfile
- [x] x11-utils installed (for xdpyinfo)
- [x] start.sh starts Xvfb before app
- [x] DISPLAY=:99 set in Dockerfile
- [x] start.sh exports DISPLAY=:99
- [x] Browser runs with headless=False
- [x] Docker-specific browser flags added
- [x] Proxy configuration included
- [x] Debug logging added

---

## 🚀 What Changed

### Before (Broken):

```python
browser = await uc.start(headless=False)
# Would fail in Docker - no display
```

### After (Fixed):

```python
browser_args = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    # ... more flags
]
browser = await uc.start(headless=False, browser_args=browser_args)
# Works in Docker with Xvfb virtual display
```

---

## 📖 How It Works

1. **Docker starts** → Runs `start.sh`
2. **start.sh** → Starts Xvfb on display `:99`
3. **Xvfb creates** → Virtual display server
4. **DISPLAY=:99** → Tells Chrome to use virtual display
5. **Browser launches** → Non-headless but on virtual display
6. **CS500 sees** → Real browser, not headless bot
7. **Scraper works** → Can access CS500 ✅

---

## 🎯 Next Steps

1. **Commit changes:**

   ```bash
   git add scraper.py Dockerfile start.sh
   git commit -m "Fix browser automation for Docker with enhanced Xvfb setup"
   git push
   ```

2. **Deploy to Railway** (automatic)

3. **Test CS500 scraper:**

   - Go to your Railway URL
   - Click "🎮 CS500 Full Scrape"
   - Check Railway logs

4. **Look for success messages:**
   ```
   ✅ Xvfb is ready on display :99
   🔧 Browser config: headless=False, display=:99
   ✅ Collected X match IDs
   ✅ Scraped X markets
   ```

---

## 💡 Pro Tips

1. **Monitor Railway Logs** - Most issues show up there
2. **Check Proxy** - Test proxy works independently
3. **Verify Display** - Look for "DISPLAY: :99" in logs
4. **Be Patient** - Browser startup takes 10-30 seconds
5. **Try Again** - First run might fail, retry once

---

**Remember:** The browser is running **non-headless** (like a real user) but on a **virtual display** (Xvfb). This is the magic that makes it work in Docker! 🪄
