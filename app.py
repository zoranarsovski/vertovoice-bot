"""
VertoVoice Slack Bot
Generates LinkedIn post drafts in Zoran's voice from URLs and PDFs
"""

import os
import re
import json
import logging
from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import anthropic
from extractors import extract_from_url, extract_from_pdf
from prompts import get_system_prompt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize clients
slack_client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))
claude_client = anthropic.Anthropic(api_key=os.environ.get("CLAUDE_API_KEY"))

# Store processed events to avoid duplicates
processed_events = set()


def extract_urls(text):
    """Extract URLs from message text"""
    url_pattern = r'<(https?://[^>|]+)(?:\|[^>]*)?>|(?<![<])(https?://[^\s<>]+)'
    matches = re.findall(url_pattern, text)
    urls = []
    for match in matches:
        url = match[0] if match[0] else match[1]
        if url:
            urls.append(url)
    return urls


def generate_linkedin_drafts(content: str, source_url: str = None) -> dict:
    """Generate 2 LinkedIn post drafts using Claude"""
    
    system_prompt = get_system_prompt()
    
    user_message = f"""Based on this content, create 2 different LinkedIn post drafts in Zoran's voice.

SOURCE CONTENT:
{content[:8000]}  # Truncate if too long

{f"Source URL: {source_url}" if source_url else ""}

---

Create 2 distinct versions:
- **Version A**: More insight-focused (lead with the key learning/observation)
- **Version B**: More engagement-focused (end with a genuine question)

For each version:
1. Keep it under 200 words
2. Use Zoran's actual language patterns
3. Tag relevant team members if their expertise applies
4. Include a relevant social proof quote only if it fits naturally (don't force it)

Format your response as:
## Version A
[post content]

## Version B  
[post content]
"""
    
    try:
        response = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        
        return {
            "success": True,
            "drafts": response.content[0].text
        }
        
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def send_slack_message(channel: str, text: str, thread_ts: str = None):
    """Send a message to Slack"""
    try:
        slack_client.chat_postMessage(
            channel=channel,
            text=text,
            thread_ts=thread_ts
        )
    except SlackApiError as e:
        logger.error(f"Slack API error: {e}")


@app.route("/", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok", "service": "VertoVoice Bot"})


@app.route("/slack/events", methods=["POST"])
def slack_events():
    """Handle Slack events"""
    data = request.json
    
    # Handle Slack URL verification challenge
    if data.get("type") == "url_verification":
        return jsonify({"challenge": data.get("challenge")})
    
    # Handle events
    if data.get("type") == "event_callback":
        event = data.get("event", {})
        event_id = data.get("event_id")
        
        # Avoid processing duplicate events
        if event_id in processed_events:
            return jsonify({"status": "ok"})
        processed_events.add(event_id)
        
        # Limit cache size
        if len(processed_events) > 1000:
            processed_events.clear()
        
        event_type = event.get("type")
        
        # Handle link shares
        if event_type == "link_shared":
            handle_link_shared(event)
        
        # Handle messages with files
        elif event_type == "message":
            # Ignore bot messages
            if event.get("bot_id"):
                return jsonify({"status": "ok"})
            
            # Check for file attachments
            files = event.get("files", [])
            if files:
                handle_file_shared(event, files)
            
            # Check for URLs in message text
            text = event.get("text", "")
            urls = extract_urls(text)
            if urls:
                handle_urls_in_message(event, urls)
    
    return jsonify({"status": "ok"})


def handle_link_shared(event):
    """Handle link_shared events"""
    channel = event.get("channel")
    links = event.get("links", [])
    message_ts = event.get("message_ts")
    
    for link in links:
        url = link.get("url")
        if url:
            process_url(channel, url, message_ts)


def handle_urls_in_message(event, urls):
    """Handle URLs found in regular messages"""
    channel = event.get("channel")
    thread_ts = event.get("ts")
    
    for url in urls:
        process_url(channel, url, thread_ts)


def process_url(channel: str, url: str, thread_ts: str = None):
    """Process a URL and generate drafts"""
    
    # Send "working on it" message
    send_slack_message(
        channel,
        "📝 Got it! Extracting content and generating drafts...",
        thread_ts
    )
    
    # Extract content from URL
    content = extract_from_url(url)
    
    if not content:
        send_slack_message(
            channel,
            "❌ Couldn't extract content from that URL. Try sharing a different link or uploading a PDF.",
            thread_ts
        )
        return
    
    # Generate drafts
    result = generate_linkedin_drafts(content, url)
    
    if result["success"]:
        response_text = f"""✨ *Here are 2 LinkedIn post drafts:*

{result['drafts']}

---
_Source: {url}_
_Edit as needed, then post!_"""
        
        send_slack_message(channel, response_text, thread_ts)
    else:
        send_slack_message(
            channel,
            f"❌ Error generating drafts: {result['error']}",
            thread_ts
        )


def handle_file_shared(event, files):
    """Handle file uploads (PDFs)"""
    channel = event.get("channel")
    thread_ts = event.get("ts")
    
    for file in files:
        filetype = file.get("filetype", "").lower()
        
        if filetype == "pdf":
            # Send "working on it" message
            send_slack_message(
                channel,
                "📝 Got the PDF! Extracting content and generating drafts...",
                thread_ts
            )
            
            # Get file URL and download
            file_url = file.get("url_private_download")
            file_name = file.get("name", "document.pdf")
            
            if file_url:
                content = extract_from_pdf(file_url, slack_client)
                
                if content:
                    result = generate_linkedin_drafts(content)
                    
                    if result["success"]:
                        response_text = f"""✨ *Here are 2 LinkedIn post drafts:*

{result['drafts']}

---
_Source: {file_name}_
_Edit as needed, then post!_"""
                        
                        send_slack_message(channel, response_text, thread_ts)
                    else:
                        send_slack_message(
                            channel,
                            f"❌ Error generating drafts: {result['error']}",
                            thread_ts
                        )
                else:
                    send_slack_message(
                        channel,
                        "❌ Couldn't extract text from that PDF. Make sure it's not a scanned image.",
                        thread_ts
                    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
