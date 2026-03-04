
from scraper import PropertyScraper
from notifier import send_discord_notify, format_property_message
import os
import sys
from dotenv import load_dotenv

# Load env vars from .env file if present
load_dotenv()

# Force UTF-8 output for Windows console to handle emojis
sys.stdout.reconfigure(encoding='utf-8')

def main():
    print("Starting daily property scan...")
    
    # 1. Scrape
    scraper = PropertyScraper()
    scraper.fetch_suumo()
    # Add other scrapers here
    
    # 2. Analyze & Notify
    print(f"Analyzing {len(scraper.properties)} properties...")
    
    msg_buffer_embeds = []
    
    for prop in scraper.properties:
        # Mocking description fetch for now
        description = prop.get('parking_comment', '') + " " + prop.get('title', '')
        
        # Analyze
        parking_score, parking_reason = scraper.analyze_parking(description)
        evils = scraper.analyze_three_evils(description)
        
        # Check Price Drop
        is_drop, drop_amount, old_price = scraper.check_price_drop(prop)
        prop['is_drop'] = is_drop
        prop['drop_amount'] = drop_amount
        prop['old_price'] = old_price
        
        # Check New
        # If link not in history, it's new.
        # Note: history is loaded at init.
        is_new = prop['link'] not in scraper.price_history
        prop['is_new'] = is_new

        # Filter: Only show if parking score >= 2 (User requirement)
        if parking_score == 0: 
            continue

        # NOTIFICATION FILTER:
        # Only notify if:
        # 1. Matches parking criteria (filtered above)
        # We send all matching properties as requested by the user.
        content, embed = format_property_message(prop, evils, parking_score)
        msg_buffer_embeds.append(embed)
    
    # Save current prices to history for next run
    scraper.save_history()

        
    # Send Summary
    # Discord allows up to 10 embeds per message.
    # We will send them in batches of 10.
    
    if msg_buffer_embeds:
        print(f"Found {len(msg_buffer_embeds)} updates (New/Drop). Sending notifications...")
        
        # Batch sending
        batch_size = 10
        for i in range(0, len(msg_buffer_embeds), batch_size):
            batch = msg_buffer_embeds[i:i+batch_size]
            if send_discord_notify(f"**【{len(msg_buffer_embeds)}件の更新があります】** (Part {i//batch_size + 1})", batch):
                pass
            else:
                print(f">> FAILED to send batch {i//batch_size + 1}")
                
    else:
        print("No new properties or price drops found.")


if __name__ == "__main__":
    main()
