# 🗄️ Railway SQLite Setup with Persistent Volumes

Your SQLite database needs persistent storage on Railway. Here's how to set it up.

## 🚀 Quick Setup

### Step 1: Create Volume in Railway Dashboard

1. Go to your **Railway Project**
2. Click your **service**
3. Go to **"Volumes"** tab (or "Data" tab)
4. Click **"+ New Volume"**
5. Configure:
   - **Mount Path**: `/data`
   - **Name**: `esports-db-volume` (or any name)
6. Click **"Create"**

### Step 2: Add Environment Variable

Go to **"Variables"** tab and add:

```bash
DATABASE_PATH=/data/esports_betting.db
```

This tells your app to store the database in the persistent volume instead of the ephemeral filesystem.

### Step 3: Deploy

Railway will automatically redeploy with the volume attached!

## 📊 What This Does

- ✅ Database persists across deployments
- ✅ Data survives restarts
- ✅ ~1GB free storage on Railway
- ✅ Automatic backups by Railway

## 🔄 Migration from Local to Railway

Your local `esports_betting.db` won't automatically transfer. Options:

### Option A: Start Fresh (Simplest)

- Railway will create a new empty database
- You'll scrape fresh data from Pinnacle/CS500

### Option B: Upload Local Database

1. **Method 1: Via Railway CLI**

   ```bash
   railway login
   railway link
   railway volumes
   # Use volume ID from above
   railway volumes upload <volume-id> esports_betting.db:/data/esports_betting.db
   ```

2. **Method 2: Copy via API (requires code)**
   - Deploy first
   - Use Railway's shell to upload database file

### Option C: Start fresh and keep local separate

- Local dev: `esports_betting.db` (local file)
- Railway prod: `/data/esports_betting.db` (volume)

## 🎯 Complete Railway Variables List

After setup, you should have:

```bash
DATABASE_PATH=/data/esports_betting.db
PROXY_SERVER=http://216.26.250.98:3129
```

## 🔍 Verifying It Works

Check Railway logs after deployment:

```
✅ Database initialized at /data/esports_betting.db
```

---

## 🐘 Alternative: PostgreSQL (Optional)

If you want a more robust solution, Railway offers **free PostgreSQL**:

### Pros of PostgreSQL:

- ✅ Proper managed database
- ✅ Better for production
- ✅ Automatic backups
- ✅ No volume management needed

### Cons:

- ⚠️ Requires code changes
- ⚠️ Need to migrate schema
- ⚠️ Different SQL syntax

**Would require**: Installing `psycopg2`, updating `database.py` to use PostgreSQL instead of SQLite.

---

**Recommendation**: Start with **SQLite + Volumes** (simpler). Migrate to PostgreSQL later if needed!
