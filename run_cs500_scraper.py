"""
CS500 Match ID Scraper Runner

This script runs the CS500 scraper to collect match IDs and send them to the API.
It must be run before you can scrape CS500 markets in the web interface.

Usage:
    python run_cs500_scraper.py

Note: This will open a browser window and may take 1-2 minutes to complete.
"""

import asyncio
from scraper import CS500Scraper
import sys

async def main():
    print("=" * 60)
    print("🎮 CS500 Match ID Scraper")
    print("=" * 60)
    print("\nThis will:")
    print("  1. Open a browser window")
    print("  2. Navigate to CS500's CS2 and LoL pages")
    print("  3. Extract all match IDs")
    print("  4. Send them to the API at http://localhost:8000")
    print("\nNote: Make sure the main server is running (python main.py)")
    print("=" * 60)
    print("\nStarting scraper...\n")
    
    scraper = CS500Scraper()
    
    try:
        match_ids = await scraper.get_matchids()
        
        if match_ids and len(match_ids) > 0:
            print("\n" + "=" * 60)
            print(f"✓ Success! Collected {len(match_ids)} match IDs")
            print("=" * 60)
            print("\nNext steps:")
            print("  1. Go to http://localhost:8000")
            print("  2. Click 'Scrape CS500' or 'Scrape All & Match'")
            print("=" * 60)
            return 0
        else:
            print("\n" + "=" * 60)
            print("⚠ Warning: No match IDs were collected")
            print("=" * 60)
            print("\nPossible reasons:")
            print("  - CS500 website is down or changed")
            print("  - No matches available for CS2/LoL")
            print("  - Browser automation failed")
            print("=" * 60)
            return 1
            
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"✗ Error: {e}")
        print("=" * 60)
        print("\nMake sure:")
        print("  1. The main server is running (python main.py)")
        print("  2. You have a display (browser automation requires GUI)")
        print("  3. No other browser instances are interfering")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
