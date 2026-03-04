
import requests
import json
import os

def send_discord_notify(message_content, embeds=None):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("Error: DISCORD_WEBHOOK_URL not found in environment variables.")
        return False
        
    headers = {"Content-Type": "application/json"}
    
    # Discord payload limits: 2000 chars for content.
    # We will use 'embeds' for nicer formatting if possible, 
    # but for simplicity and safety against limits, we can stick to content or simple embeds.
    
    payload = {
        "content": message_content
    }
    if embeds:
        payload["embeds"] = embeds

    try:
        r = requests.post(webhook_url, headers=headers, data=json.dumps(payload))
        r.raise_for_status()
        print("Discord notification sent successfully.")
        return True
    except Exception as e:
        print(f"Failed to send Discord notification: {e}")
        return False

def format_property_message(prop, evils, parking_rank):
    """
    Formats the message for Discord.
    Returns a tuple (text_content, embed_object)
    """
    
    # Parking rank formatting
    parking_icon = "🅿️"
    color = 0x00ff00 # Green
    
    if parking_rank >= 4: 
        parking_icon = "🔥🔥🅿️4台+"
        color = 0xff0000 # Red for Hot
    elif parking_rank == 3: 
        parking_icon = "✨🅿️3台"
        color = 0xffa500 # Orange
    elif parking_rank == 2: 
        parking_icon = "🅿️2台"
    
    # Three Evils
    evil_str = f"雨漏り[{'O' if evils['雨漏り'] else ' '}] シロアリ[{'O' if evils['シロアリ'] else ' '}] 傾き[{'O' if evils['傾き'] else ' '}]"

    # Price Drop Header
    title_prefix = ""
    if prop.get('is_drop'):
        drop_man = prop['drop_amount'] // 10000
        title_prefix = f"🔥 【値下げ】 ▲{drop_man}万円! "
        color = 0xff0000
    elif prop.get('is_new'):
        title_prefix = "🆕 【新着】 "
        color = 0x00bfff # Deep Sky Blue for New

    # Construct Embed
    embed = {
        "title": f"{title_prefix}{parking_icon} {prop['title']}",
        "url": prop['link'],
        "color": color,
        "fields": [
            {"name": "価格", "value": prop['price_str'], "inline": True},
            {"name": "所在地", "value": prop['address'], "inline": True},
            {"name": "駐車場", "value": f"{parking_rank}台判定\n({prop.get('parking_reason', '')})", "inline": False},
            {"name": "三害チェック", "value": evil_str, "inline": False}
        ],
        "footer": {"text": "Chiba Property Bot"}
    }
    
    # Optional: content mention
    content = "" 

    return content, embed
