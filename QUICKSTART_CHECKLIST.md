# ✅ Quick Start Checklist

Use this checklist to track your deployment progress!

---

## 📝 Pre-Deployment Setup

### Discord Bot Setup
- [ ] Create Discord Application at [Discord Developer Portal](https://discord.com/developers/applications)
- [ ] Add Bot to application
- [ ] Enable these Privileged Gateway Intents:
  - [ ] Presence Intent
  - [ ] Server Members Intent
  - [ ] **Message Content Intent** (CRITICAL!)
- [ ] Copy Bot Token → Save securely
- [ ] Generate OAuth2 URL with correct permissions → Save URL
- [ ] Invite bot to your test server (using OAuth2 URL)

### API Keys
- [ ] Create OpenAI account at [OpenAI Platform](https://platform.openai.com/)
- [ ] Generate OpenAI API key → Save securely
- [ ] (Optional) Get Z.ai API key from [Z.ai](https://z.ai/)

### Database Setup
- [ ] Create MongoDB Atlas account at [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
- [ ] Create FREE M0 cluster
- [ ] Create database user (username + password)
- [ ] Set Network Access to `0.0.0.0/0` (allow from anywhere)
- [ ] Get connection string → Replace `<password>` → Add `/automod` database name → Save
- [ ] Test connection (optional: use MongoDB Compass)

### Cache Setup
- [ ] Create Upstash account at [Upstash](https://upstash.com/)
- [ ] Create Redis database (Regional, LRU eviction)
- [ ] Copy Redis URL → Save securely

---

## 🚀 Render.com Deployment

### Account Setup
- [ ] Create Render.com account at [Render.com](https://render.com/)
- [ ] Sign up with GitHub (recommended)
- [ ] Authorize Render to access GitHub repositories

### Service Creation
- [ ] Click **New +** → Select **Background Worker** (NOT Web Service!)
- [ ] Connect GitHub repository: `TommoHCIO/Automod`
- [ ] Configure service:
  - [ ] Name: `discord-automod-bot`
  - [ ] Region: Choose closest to you
  - [ ] Branch: `main`
  - [ ] Runtime: Python 3
  - [ ] Build Command: `pip install -r requirements.txt`
  - [ ] Start Command: `python bot.py`

### Environment Variables
Add these environment variables (click **Add Environment Variable** for each):

- [ ] `DISCORD_TOKEN` = (your Discord bot token from step 1)
- [ ] `OPENAI_API_KEY` = (your OpenAI key from step 2)
- [ ] `MONGODB_URI` = (your MongoDB connection string from step 3)
- [ ] `REDIS_URL` = (your Redis URL from step 4)
- [ ] `LOG_LEVEL` = `INFO`
- [ ] `ENVIRONMENT` = `production`

### Deploy
- [ ] Select **Free** plan
- [ ] Click **Create Background Worker**
- [ ] Wait 2-5 minutes for deployment
- [ ] Watch logs for success messages:
  - [ ] `✅ Connected to MongoDB`
  - [ ] `✅ Connected to Redis cache`
  - [ ] `✅ Bot is ready!`

---

## 🎮 Post-Deployment

### Verify Bot is Online
- [ ] Check Discord server - bot should show 🟢 Online
- [ ] Run `/automod status` in Discord
- [ ] Bot responds with statistics

### Configure Bot
- [ ] Create `#mod-logs` channel in Discord (make it private)
- [ ] Enable Developer Mode in Discord (User Settings → Advanced)
- [ ] Right-click `#mod-logs` → Copy Channel ID
- [ ] Store channel ID (you'll set this via slash commands or MongoDB)

### Test Functionality
- [ ] Test manual check: `!check this is a test message`
- [ ] Test slash commands: `/automod status`
- [ ] Test slash commands: `/automod config`
- [ ] (Carefully) Test detection in a test channel
- [ ] Verify message gets deleted
- [ ] Verify warning DM is sent
- [ ] Verify violation appears in mod logs

### Render Settings (Optional)
- [ ] Enable Auto-Deploy from GitHub (Settings → Build & Deploy)
- [ ] Bookmark Render service logs page
- [ ] Check Metrics tab for resource usage

---

## 🔧 Troubleshooting

If something doesn't work, check these:

### Bot Shows Offline
- [ ] Check Render logs for errors
- [ ] Verify all environment variables are set correctly
- [ ] Verify Discord token is valid (no extra spaces)
- [ ] Manually redeploy: Render Dashboard → Manual Deploy

### Bot Online but Not Responding
- [ ] Check bot has **Manage Messages** permission in Discord
- [ ] Verify **Message Content Intent** is enabled
- [ ] Check Render logs for runtime errors
- [ ] Test with `!check` command first

### Database Connection Issues
- [ ] Verify MongoDB Atlas IP whitelist includes `0.0.0.0/0`
- [ ] Check MongoDB URI format is correct
- [ ] Verify database user credentials
- [ ] Test connection using MongoDB Compass

### No Moderation Happening
- [ ] Verify bot has permissions in the channel
- [ ] Check if channel is in ignored list
- [ ] Review OpenAI API key is valid
- [ ] Check Render logs for AI errors

---

## 📊 Success Indicators

Your deployment is successful when:

✅ Bot shows **Online** in Discord server  
✅ `/automod status` shows statistics  
✅ Render logs show no errors  
✅ Test message gets moderated correctly  
✅ Mod logs receive violation notifications  
✅ Memory usage is stable (~200-300MB)  

---

## 🎯 Next Steps

After successful deployment:

- [ ] Adjust punishment tiers in `config/punishment_tiers.json` (optional)
- [ ] Add/remove words from whitelist in `config/allowed_words.json`
- [ ] Monitor bot for first 24-48 hours
- [ ] Invite bot to additional servers (if desired)
- [ ] Set up UptimeRobot monitoring (optional, free tier)
- [ ] Consider upgrading Render to Starter plan ($7/mo) for 24/7 uptime

---

## 📚 Documentation

- [ ] Read full [README.md](README.md)
- [ ] Read detailed [RENDER_DEPLOYMENT_GUIDE.md](RENDER_DEPLOYMENT_GUIDE.md)
- [ ] Bookmark [Discord.py docs](https://discordpy.readthedocs.io/)
- [ ] Bookmark [Render community](https://community.render.com/)

---

## 💾 Save These URLs

**Your Bot:**
- GitHub Repo: https://github.com/TommoHCIO/Automod
- Render Dashboard: https://dashboard.render.com/
- Discord Bot OAuth2 URL: (save the URL you generated)

**Services:**
- MongoDB Atlas: https://cloud.mongodb.com/
- Upstash Redis: https://console.upstash.com/
- Discord Developer Portal: https://discord.com/developers/applications
- OpenAI Platform: https://platform.openai.com/

---

**Good luck! 🚀**

If you get stuck, check the detailed [RENDER_DEPLOYMENT_GUIDE.md](RENDER_DEPLOYMENT_GUIDE.md) or open an issue on GitHub.
