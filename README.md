# VertoVoice Slack Bot

LinkedIn post draft generator in Zoran's voice. Share a URL or PDF in Slack → get 2 post drafts back.

## Setup Instructions

### 1. Create GitHub Repository

```bash
# In Claude Code, navigate to the project folder and run:
git init
git add .
git commit -m "Initial commit - VertoVoice bot"

# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/vertovoice-bot.git
git push -u origin main
```

### 2. Deploy to Railway

1. Go to [railway.app](https://railway.app) and sign in with GitHub
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your `vertovoice-bot` repository
4. Railway will auto-detect Python and start building

### 3. Add Environment Variables in Railway

In Railway dashboard → Your project → Variables tab:

| Variable | Value |
|----------|-------|
| `SLACK_BOT_TOKEN` | Your bot token (xoxb-...) |
| `CLAUDE_API_KEY` | Your Claude API key (sk-ant-...) |

### 4. Get Your Railway URL

After deployment, go to Settings → Domains → Generate Domain

You'll get something like: `vertovoice-bot-production.up.railway.app`

### 5. Configure Slack Event Subscriptions

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → Your app
2. **Event Subscriptions** → Enable Events → ON
3. **Request URL**: `https://YOUR-RAILWAY-URL/slack/events`
   - Wait for verification ✓
4. **Subscribe to bot events** → Add:
   - `link_shared`
   - `message.channels`
   - `message.groups`
   - `message.im`
5. Click "Save Changes"

### 6. Configure Link Unfurling (for URL detection)

1. Go to **Event Subscriptions** → **App Unfurl Domains**
2. Add domains you want to trigger drafts (or leave empty for all links)

### 7. Reinstall App

After changing permissions:
1. Go to **OAuth & Permissions**
2. Click "Reinstall to Workspace"

## Usage

In any Slack channel where the bot is added:

**Share a URL:**
```
https://example.com/interesting-article
```

**Upload a PDF:**
Just drag and drop a PDF file

The bot will reply with 2 LinkedIn post drafts:
- **Version A**: Insight-focused
- **Version B**: Engagement-focused (ends with question)

## Files

- `app.py` - Main Flask application
- `prompts.py` - Zoran's voice profile and social proof library
- `extractors.py` - URL and PDF content extraction
- `requirements.txt` - Python dependencies
- `Procfile` - Railway deployment config

## Troubleshooting

**Bot not responding?**
- Check Railway logs for errors
- Verify environment variables are set
- Make sure bot is added to the channel

**"Couldn't extract content" error?**
- Some sites block scraping
- Try sharing a different source
- PDFs must have extractable text (not scanned images)

**Duplicate responses?**
- This is handled by event deduplication in the code
- If persists, check Slack retry settings
