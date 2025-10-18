# 🗄️ Redis Setup Guide for Upstash

Quick guide to get your Redis URL for the bot.

---

## Option 1: Upstash (Recommended - FREE)

### Step 1: Create Account
1. Go to [Upstash Console](https://console.upstash.com/)
2. Sign up with GitHub (easiest)
3. Verify your email

### Step 2: Create Redis Database
1. Click **Create Database** (green button, top right)
2. Configure:
   - **Name:** `automod-cache` (or any name you like)
   - **Type:** Select **Regional**
   - **Region:** Choose closest to your Render.com region:
     - If Render is in **Oregon (US West)** → Choose **US-West-1**
     - If Render is in **Ohio (US East)** → Choose **US-East-1**
     - If Render is in **Frankfurt** → Choose **EU-West-1**
   - **Eviction:** Leave as **LRU** (recommended)
   - **TLS:** Enable (default)
3. Click **Create**

### Step 3: Get Redis URL

After creation, you'll see your database dashboard. Look for the **REST API** section.

**Two options to copy:**

#### Option A: Using redis-cli (Traditional Format)
Scroll down to "Connect your database" → **Redis Clients** tab

You'll see something like:
```bash
redis-cli --tls -u redis://default:YOUR_PASSWORD@YOUR_ENDPOINT.upstash.io:PORT
```

Your **REDIS_URL** is:
```
redis://default:YOUR_PASSWORD@YOUR_ENDPOINT.upstash.io:PORT
```

**Example:**
```
redis://default:AaBbCc123XxYyZz@us1-complete-bass-12345.upstash.io:6379
```

#### Option B: Using REST API URL
In the **REST API** section, you'll see:

- **UPSTASH_REDIS_REST_URL:** `https://us1-complete-bass-12345.upstash.io`
- **UPSTASH_REDIS_REST_TOKEN:** `AaBbCc123XxYyZz`

For Python apps with `redis-py`, use the **redis://** format from Option A.

### Step 4: Test Connection (Optional)

If you have `redis-cli` installed:

```bash
redis-cli --tls -u redis://default:YOUR_PASSWORD@YOUR_ENDPOINT.upstash.io:PORT

# Test commands
> PING
PONG
> SET test "hello"
OK
> GET test
"hello"
```

---

## Option 2: Redis Cloud (Alternative FREE option)

### Step 1: Create Account
1. Go to [Redis Cloud](https://redis.com/try-free/)
2. Sign up with Google/GitHub
3. Verify email

### Step 2: Create Database
1. Click **New database**
2. Select **Free** plan
3. Choose cloud provider: **AWS** (recommended)
4. Choose region closest to Render deployment
5. Database name: `automod-cache`
6. Click **Activate**

### Step 3: Get Connection Details
1. Click on your database
2. Look for **Public endpoint**
3. Format is: `redis-XXXXX.c123.us-east-1-1.ec2.cloud.redislabs.com:12345`
4. Get password from **Security** → **Default user password**

Your **REDIS_URL** is:
```
redis://default:YOUR_PASSWORD@redis-XXXXX.c123.us-east-1-1.ec2.cloud.redislabs.com:12345
```

---

## Option 3: Local Redis (Development Only)

For local testing only (NOT for production/Render):

### Install Redis Locally

**Windows (via WSL):**
```bash
wsl
sudo apt update
sudo apt install redis-server
redis-server
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Your REDIS_URL:**
```
redis://localhost:6379
```

⚠️ **Note:** Local Redis won't work on Render.com - you need Upstash or Redis Cloud!

---

## 🔑 Add to Your .env File

Once you have your Redis URL, add it to `.env`:

```env
REDIS_URL=redis://default:YOUR_PASSWORD@YOUR_ENDPOINT.upstash.io:6379
```

**Examples of valid formats:**

✅ **Upstash:**
```
REDIS_URL=redis://default:AbCd1234@us1-bass-12345.upstash.io:6379
```

✅ **Redis Cloud:**
```
REDIS_URL=redis://default:xyz789@redis-12345.c1.us-east-1.cloud.redislabs.com:16379
```

✅ **Local (dev only):**
```
REDIS_URL=redis://localhost:6379
```

❌ **WRONG - missing redis:// prefix:**
```
REDIS_URL=default:password@host.upstash.io:6379
```

❌ **WRONG - using REST API URL:**
```
REDIS_URL=https://us1-bass-12345.upstash.io
```

---

## 🧪 Test Your Redis Connection

Create a test file `test_redis.py`:

```python
import redis
from dotenv import load_dotenv
import os

load_dotenv()

redis_url = os.getenv('REDIS_URL')
print(f"Connecting to: {redis_url}")

try:
    r = redis.from_url(redis_url, decode_responses=True)
    r.ping()
    print("✅ Redis connection successful!")
    
    # Test set/get
    r.set('test_key', 'Hello from Python!')
    value = r.get('test_key')
    print(f"✅ Test value: {value}")
    
except Exception as e:
    print(f"❌ Redis connection failed: {e}")
```

Run it:
```bash
python test_redis.py
```

Should output:
```
Connecting to: redis://default:****@us1-bass-12345.upstash.io:6379
✅ Redis connection successful!
✅ Test value: Hello from Python!
```

---

## 📊 Upstash Free Tier Limits

- ✅ **10,000 commands per day** (plenty for Discord bot)
- ✅ **256 MB storage**
- ✅ **Unlimited databases**
- ✅ **TLS encryption included**
- ✅ **No credit card required**

**For Discord bot usage:**
- Average bot: ~1,000-5,000 commands/day
- Busy bot (1,000 users): ~8,000-10,000 commands/day
- If you exceed, upgrade to **Pay as You Go** ($0.20 per 100k commands)

---

## 🔧 Troubleshooting

### Error: "Connection refused"
- ✅ Check Redis URL format is correct
- ✅ Verify you copied the full password (no spaces)
- ✅ Check you're using **redis://** prefix (not https://)

### Error: "WRONGPASS invalid username-password pair"
- ✅ Password might be incorrect
- ✅ In Upstash, regenerate password and update `.env`

### Error: "Connection timeout"
- ✅ Check your internet connection
- ✅ Verify Upstash database is **Active** (not Paused)
- ✅ Try recreating the database

### Bot works but slow
- ℹ️ This is normal if Redis isn't connected
- ✅ Bot will function without Redis (just slower)
- ✅ Add Redis URL to speed up by 60-70%

---

## ✅ For Render.com Deployment

In Render dashboard environment variables, add:

```
Key:    REDIS_URL
Value:  redis://default:YOUR_PASSWORD@YOUR_ENDPOINT.upstash.io:6379
```

⚠️ **Make sure there are:**
- No extra spaces
- No quotes around the URL
- The full password is included

---

**Done! Redis is now configured for caching 🚀**

Your bot will now cache AI responses for 5 minutes, reducing API calls by 60-70%!
