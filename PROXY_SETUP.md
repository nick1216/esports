# 🌐 Setting Up Proxy for CS500 (Canada Access)

CS500 requires Canadian IP access. Here's how to configure a proxy.

## 🚀 Quick Setup on Railway

### Step 1: Get a Canadian Proxy

**Recommended Proxy Services:**

1. **Bright Data (Luminati)** - Most reliable

   - https://brightdata.com
   - ~$500/month for residential proxies
   - Canadian residential IPs

2. **Smartproxy** - Good value

   - https://smartproxy.com
   - ~$75/month for 5GB
   - Canadian datacenter/residential IPs

3. **ProxyMesh** - Budget friendly

   - https://proxymesh.com
   - ~$60/month
   - Canadian datacenter IPs

4. **WebShare.io** - Cheapest option
   - https://webshare.io
   - ~$10-40/month
   - Datacenter IPs (may not work for all sites)

### Step 2: Add Proxy to Railway

Once you have a proxy, add it as an environment variable:

1. Go to your Railway project dashboard
2. Click on your service
3. Go to **"Variables"** tab
4. Click **"+ New Variable"**
5. Add:
   ```
   PROXY_SERVER = http://username:password@proxy-server:port
   ```

**Example formats:**

```bash
# HTTP proxy with auth
PROXY_SERVER=http://username:password@ca.proxy.com:8080

# HTTP proxy without auth
PROXY_SERVER=http://ca.proxy.com:8080

# SOCKS5 proxy
PROXY_SERVER=socks5://username:password@ca.proxy.com:1080
```

### Step 3: Redeploy

Railway will automatically restart your app with the new proxy configuration!

## 🧪 Testing Locally

To test with a proxy on your local machine:

### Windows (PowerShell):

```powershell
$env:PROXY_SERVER="http://username:password@ca.proxy.com:8080"
python run_cs500_scraper.py
```

### Linux/Mac:

```bash
export PROXY_SERVER="http://username:password@ca.proxy.com:8080"
python run_cs500_scraper.py
```

## 🔧 How It Works

The scraper now automatically:

1. Checks for `PROXY_SERVER` environment variable
2. Configures Chrome to route through the proxy
3. All CS500 requests appear to come from Canada

## 💡 Proxy Tips

### For Best Results:

- ✅ Use **residential proxies** (look like real Canadian users)
- ✅ Use **sticky sessions** (same IP for duration)
- ✅ Canadian city: Toronto, Montreal, or Vancouver
- ⚠️ Avoid **datacenter proxies** (may be blocked)
- ⚠️ Avoid **free proxies** (unreliable and often blocked)

### Proxy Types Explained:

1. **Residential Proxies** (Best for CS500)

   - Real Canadian home IPs
   - Harder to detect/block
   - More expensive (~$75-500/month)
   - **Recommended for production**

2. **Datacenter Proxies** (Budget option)

   - Server IPs in Canadian datacenters
   - Easier to detect
   - Cheaper (~$10-60/month)
   - May work, may get blocked

3. **SOCKS5 Proxies**
   - Low-level protocol
   - Works with any traffic
   - Good alternative to HTTP

## 🆓 Free Proxy Options (Not Recommended)

**Free Canadian proxy lists** (unreliable, often blocked):

- https://www.proxy-list.download/HTTPS (filter by Canada)
- https://free-proxy-list.net/ (filter by Canada)

**Format:**

```bash
PROXY_SERVER=http://proxy-ip:port
```

⚠️ **Warning**: Free proxies are:

- Slow and unreliable
- Often blocked by betting sites
- May log your traffic
- Not recommended for production

## 🔍 Verifying Proxy Works

Once configured, check your Railway logs:

```
🌐 Using proxy: http://...
🌐 Browser configured with proxy: http://...
```

If you see these messages, the proxy is configured!

## 🐛 Troubleshooting

### Proxy Not Working?

1. **Check format**: Must be `http://` or `socks5://`
2. **Test credentials**: Verify username/password
3. **Check proxy status**: Is the proxy service up?
4. **Try different proxy**: Some proxies may be blocked by CS500

### CS500 Still Blocking?

1. Use **residential proxy** instead of datacenter
2. Try **different Canadian city**
3. Enable **sticky sessions** (keep same IP)
4. Contact proxy provider for "betting-friendly" IPs

### Connection Timeout?

1. Proxy may be slow - increase timeout
2. Try different proxy server
3. Check if proxy requires authentication

## 💰 Cost Comparison

| Service      | Type        | Price/Month | Best For        |
| ------------ | ----------- | ----------- | --------------- |
| Bright Data  | Residential | ~$500       | Production      |
| Smartproxy   | Residential | ~$75        | Small scale     |
| ProxyMesh    | Datacenter  | ~$60        | Budget          |
| WebShare     | Datacenter  | ~$10-40     | Testing         |
| Free Proxies | Various     | Free        | Not recommended |

## 📝 Next Steps

1. ✅ Choose a proxy service
2. ✅ Get Canadian proxy credentials
3. ✅ Add `PROXY_SERVER` to Railway variables
4. ✅ Test CS500 scraping
5. ✅ Monitor logs for successful connections

---

**Pro Tip**: Start with Smartproxy or ProxyMesh for a good balance of price and reliability!
