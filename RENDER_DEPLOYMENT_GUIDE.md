# 🚀 Complete Render.com Deployment Guide

Step-by-step guide to deploy your Discord Automod Bot to Render.com for **FREE** 24/7 hosting.

---

## 📋 Prerequisites Checklist

Before starting, make sure you have:

- [x] GitHub account with code pushed to repository
- [ ] Discord bot token (from Discord Developer Portal)
- [ ] OpenAI API key (FREE - recommended) OR Z.ai API key
- [ ] MongoDB Atlas database (FREE tier)
- [ ] Redis database (Upstash FREE tier recommended)
- [ ] Render.com account (FREE)

---

## Part 1️⃣: Get Required API Keys & Services

### 1.1 Discord Bot Token

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **New Application**
3. Name your bot (e.g., "Automod Bot")
4. Go to **Bot** tab on the left
5. Click **Add Bot** → **Yes, do it!**
6. Under "Privileged Gateway Intents", enable:
   - ✅ **Presence Intent**
   - ✅ **Server Members Intent**
   - ✅ **Message Content Intent** (CRITICAL!)
7. Click **Reset Token** → **Copy** the token
8. **Save this token** - you'll need it for Render

**Bot Permissions Calculator:**
- Go to **OAuth2** → **URL Generator**
- Scopes: Select `bot` and `applications.commands`
- Bot Permissions: Select:
  - ✅ Read Messages/View Channels
  - ✅ Send Messages
  - ✅ Manage Messages
  - ✅ Timeout Members
  - ✅ Kick Members
  - ✅ Ban Members
  - ✅ Read Message History
- Copy the generated URL at the bottom
- **Save this URL** - you'll use it to invite the bot to your server

---

### 1.2 OpenAI API Key (FREE - Recommended)

**Why OpenAI?** The Moderation API is completely FREE with 95% accuracy!

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in
3. Click your profile (top right) → **View API keys**
4. Click **Create new secret key**
5. Name it "Automod Bot"
6. **Copy and save the key** (starts with `sk-proj-...`)

**Note:** You can also add Z.ai key later, but OpenAI alone works perfectly!

---

### 1.3 MongoDB Atlas Database (FREE)

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Click **Try Free** → Sign up
3. Create a **FREE** M0 cluster:
   - Provider: **AWS** (or any)
   - Region: Choose closest to you
   - Cluster Name: `AutomodCluster`
4. Click **Create**
5. **Security Quickstart:**
   - **Username:** `automodbot`
   - **Password:** Generate a secure password → **Copy it!**
   - Click **Create User**
6. **Network Access:**
   - Click **Add IP Address**
   - Click **Allow Access from Anywhere** (`0.0.0.0/0`)
   - Click **Confirm**
7. Wait for cluster to deploy (~3-5 minutes)
8. Click **Connect** → **Connect your application**
9. Copy the connection string (looks like):
   ```
   mongodb+srv://automodbot:<password>@automodcluster.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
10. **Replace `<password>`** with your actual password
11. **Add database name** after `.net/`: 
    ```
    mongodb+srv://automodbot:yourpassword@automodcluster.xxxxx.mongodb.net/automod?retryWrites=true&w=majority
    ```
12. **Save this connection string!**

---

### 1.4 Redis Database - Upstash (FREE)

1. Go to [Upstash](https://upstash.com/)
2. Sign up with GitHub
3. Click **Create Database**
4. Configure:
   - Name: `automod-cache`
   - Type: **Regional**
   - Region: Choose closest to your Render region
   - Eviction: **LRU**
5. Click **Create**
6. Click your database → **Details** tab
7. **Copy** the **REST URL** (looks like):
   ```
   redis://default:xxxxxxxxxxxxx@us1-massive-halibut-12345.upstash.io:6379
   ```
8. **Save this URL!**

---

## Part 2️⃣: Deploy to Render.com

### 2.1 Create Render Account

1. Go to [Render.com](https://render.com/)
2. Click **Get Started for Free**
3. Sign up with **GitHub** (recommended)
4. Authorize Render to access your GitHub

---

### 2.2 Create Background Worker

**CRITICAL: Use Background Worker, NOT Web Service!**

1. In Render Dashboard, click **New +** (top right)
2. Select **Background Worker** ⚠️ NOT "Web Service"!
3. Connect your repository:
   - If you don't see your repo, click **Configure account** → Grant access
   - Select `TommoHCIO/Automod`
4. Configure the service:

```
Name:                 discord-automod-bot
Region:               Oregon (US West) or closest to you
Branch:               main
Runtime:              Python 3

Build Command:        pip install -r requirements.txt
Start Command:        python bot.py
```

5. **DO NOT click "Create Background Worker" yet!** Scroll down...

---

### 2.3 Set Environment Variables

Still on the same page, scroll to **Environment Variables** section.

Click **Add Environment Variable** and add these ONE BY ONE:

| Key | Value | Where to Get |
|-----|-------|--------------|
| `DISCORD_TOKEN` | Your Discord bot token | Section 1.1 |
| `OPENAI_API_KEY` | Your OpenAI API key | Section 1.2 |
| `MONGODB_URI` | Your MongoDB connection string | Section 1.3 |
| `REDIS_URL` | Your Upstash Redis URL | Section 1.4 |
| `LOG_LEVEL` | `INFO` | Type this manually |
| `ENVIRONMENT` | `production` | Type this manually |

**Example:**

```
DISCORD_TOKEN=MTExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
MONGODB_URI=mongodb+srv://automodbot:yourpass@cluster.mongodb.net/automod?retryWrites=true&w=majority
REDIS_URL=redis://default:xxxxxxxx@us1-xxxxx.upstash.io:6379
LOG_LEVEL=INFO
ENVIRONMENT=production
```

⚠️ **Double-check:**
- No extra spaces
- No quotes around values
- MongoDB URI has `/automod` database name
- DISCORD_TOKEN is complete

---

### 2.4 Deploy!

1. After adding all environment variables, scroll to bottom
2. Select **Free** plan
3. Click **Create Background Worker**
4. Wait for deployment (2-5 minutes)

**Watch the logs:**
- You'll see real-time deployment logs
- Look for these success indicators:

```
==> Building...
==> Installing dependencies from requirements.txt
==> Build succeeded!
==> Starting service...
✅ Connected to MongoDB
✅ Connected to Redis cache
✅ Embeddings model loaded: all-MiniLM-L6-v2
✅ OpenAI client initialized
✅ All cogs loaded
✅ Bot is ready!
   Logged in as: YourBotName#1234
   User ID: 1234567890
   Servers: 0
```

---

### 2.5 Check Bot Status

If deployment succeeds but bot isn't working:

1. **Check Logs** for errors:
   - Click your service → **Logs** tab
   - Look for red errors
   
2. **Common Issues:**

   **Error:** `DISCORD_TOKEN not found`
   - **Fix:** Add DISCORD_TOKEN to environment variables

   **Error:** `Failed to connect to MongoDB`
   - **Fix:** Check MongoDB URI is correct
   - Verify IP whitelist includes `0.0.0.0/0`

   **Error:** `No AI API keys provided`
   - **Fix:** Add at least OPENAI_API_KEY

   **Error:** `Missing permissions`
   - **Fix:** Re-invite bot with correct permissions

---

## Part 3️⃣: Invite Bot to Your Server

1. Use the OAuth2 URL from Section 1.1
2. Or create new one:
   ```
   https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=1376674154502&scope=bot%20applications.commands
   ```
   Replace `YOUR_CLIENT_ID` with your Application ID from Discord Developer Portal

3. Open URL → Select your server → **Authorize**
4. Complete captcha
5. Bot should appear **ONLINE** in your server! 🟢

---

## Part 4️⃣: Configure Bot

### 4.1 Set Up Logging Channel

1. Create a private channel in your Discord server (e.g., `#mod-logs`)
2. In Discord, right-click the channel → **Copy Channel ID**
   - If you don't see this, enable Developer Mode:
     - User Settings → App Settings → Advanced → Developer Mode ✅
3. Run this command in Discord:
   ```
   /automod config
   ```
4. You'll see the bot is enabled but no log channel set
5. Manually update the database (or modify `guild_config` in MongoDB) to set `log_channel_id`

**OR** wait for a violation to occur, and the bot will log to system channel

---

### 4.2 Test the Bot

**Method 1: Manual Check**
```
/automod status
```
You should see statistics and configuration

**Method 2: Test Detection** (in a test channel)
```
!check this is a test message
```
Bot will analyze it and show results

**Method 3: Test Moderation** (be careful!)
Post a message with hate speech in a test channel. Bot should:
- Delete the message
- Send you a warning DM
- Log to mod channel

---

## Part 5️⃣: Render.com Settings & Optimization

### 5.1 Auto-Deploy from GitHub

1. In Render Dashboard → Your service
2. Go to **Settings** tab
3. Scroll to **Build & Deploy**
4. **Auto-Deploy:** Set to **Yes**

Now every time you push to GitHub `main` branch, Render will automatically redeploy!

---

### 5.2 Keep Bot Running 24/7 (FREE TIER)

⚠️ **Render Free Tier Limitation:**
Background Workers on free tier may idle after 15 minutes of inactivity.

**Solutions:**

**Option A: Upgrade to Starter Plan ($7/month)**
- Guaranteed 24/7 uptime
- No idle timeout
- Best for production bots

**Option B: External Ping Service (FREE but not ideal)**
1. Sign up at [UptimeRobot](https://uptimerobot.com/)
2. Create a monitor:
   - Type: HTTP(s)
   - URL: Your Render service URL
   - Interval: Every 5 minutes
3. This pings your service to keep it awake

**Note:** For Background Workers, pinging doesn't help much. Consider upgrading if you need 24/7.

**Option C: Switch to Oracle Cloud (FREE 24/7)**
- Oracle Cloud offers always-free ARM instances
- No idle timeout
- See: [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/)

---

### 5.3 Monitor Your Bot

**Render Dashboard:**
1. Go to your service
2. **Metrics** tab shows:
   - Memory usage
   - CPU usage
   - Restart history

**Check Logs:**
```
Dashboard → Your Service → Logs
```

**Discord Bot Status:**
- Bot should show 🟢 Online in your server
- Test with `/automod status`

---

## 🎯 Quick Troubleshooting

### Bot Shows Offline

1. Check Render logs for errors
2. Verify all environment variables are set
3. Check Discord token is valid
4. Restart service: Render Dashboard → Manual Deploy → Deploy latest commit

### Messages Not Being Moderated

1. Check bot has **Manage Messages** permission
2. Verify **Message Content Intent** is enabled in Discord portal
3. Check channel isn't in ignored_channel_ids
4. Test with `!check <message>`

### Database Errors

1. Verify MongoDB IP whitelist: `0.0.0.0/0`
2. Check connection string format
3. Test connection in MongoDB Atlas → Connect → Connect with MongoDB Compass

### Redis Cache Not Working

1. Bot will work without Redis (just slower)
2. Check Upstash dashboard for errors
3. Verify REDIS_URL format

---

## 📊 Expected Performance

After successful deployment:

- ✅ Bot online 24/7 (with paid plan or Oracle Cloud)
- ✅ Response time: <500ms average
- ✅ Detection accuracy: 95%+
- ✅ Cache hit rate: 60-70%
- ✅ Memory usage: ~200-300MB
- ✅ CPU usage: <5% idle, 20-40% during moderation

---

## 🔄 Updating Your Bot

1. Make changes to code locally
2. Commit and push to GitHub:
   ```bash
   git add .
   git commit -m "Update feature X"
   git push
   ```
3. If Auto-Deploy is enabled, Render will automatically redeploy
4. Otherwise, go to Render Dashboard → Manual Deploy → Deploy latest commit

---

## 💰 Cost Breakdown

| Service | Free Tier | Paid Option |
|---------|-----------|-------------|
| **Render.com** | Background Worker (may idle) | $7/mo (24/7 uptime) |
| **MongoDB Atlas** | 512MB storage | Starts at $9/mo |
| **Upstash Redis** | 10k commands/day | Starts at $0.20/100k |
| **OpenAI Moderation API** | **FREE unlimited** | N/A |
| **Discord** | FREE | N/A |

**Total for FREE tier:** $0/month (with limitations)
**Total for basic paid:** ~$7/month (Render only)

---

## 🎉 Success!

Your Discord Automod Bot is now deployed and running 24/7!

**Next Steps:**
1. Invite bot to more servers
2. Monitor logs for first few days
3. Adjust punishment tiers in `config/punishment_tiers.json`
4. Add more allowed words to `config/allowed_words.json`
5. Check `/automod status` regularly

---

## 🆘 Need Help?

- **Render Community:** https://community.render.com/
- **Discord.py Docs:** https://discordpy.readthedocs.io/
- **GitHub Issues:** https://github.com/TommoHCIO/Automod/issues

**Common Support Resources:**
- Render Status: https://status.render.com/
- MongoDB Atlas Status: https://status.cloud.mongodb.com/
- Discord API Status: https://discordstatus.com/

---

**Built with ❤️ using Render.com**

Good luck with your bot! 🚀
