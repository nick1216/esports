"""
CS500 Match ID Scraper using Playwright (supports proxy authentication!)
This scraper ONLY collects match IDs via browser automation.
Use the original CS500Scraper.get_markets() to fetch market data via API.
"""

import asyncio
import os
from playwright.async_api import async_playwright
from typing import List, Set, Optional

class CS500ScraperPlaywright:
    """
    CS500 Match ID scraper using Playwright with proxy authentication support.
    
    This scraper handles browser automation ONLY to collect match IDs.
    For fetching market data, use the original CS500Scraper.get_markets() method.
    """
    
    def __init__(self, proxy_server: Optional[str] = None):
        """Initialize scraper with optional proxy."""
        self.lol_path = "https://csgo500.com/sports?bt-path=%2Fleague-of-legends-110"
        self.cs2_path = "https://csgo500.com/sports?bt-path=%2Fcounter-strike-109"
        self.match_ids: Set[str] = set()
        
        # Get proxy from parameter or environment
        self.proxy_server = proxy_server or os.getenv('PROXY_SERVER')
        if self.proxy_server:
            print(f"🌐 Using proxy: {self.proxy_server[:50]}...")
    
    def add_match_id_to_set(self, href: str) -> bool:
        """Add match ID from href to the set. Returns True if successful."""
        match_id = self.extract_match_id_from_href(href)
        if match_id:
            self.match_ids.add(match_id)
            return True
        return False

    def extract_match_id_from_href(self, href: str) -> Optional[str]:
        """Extract match ID from href URL (numbers at the end)."""
        # Example: /league-of-legends/.../colossal-gaming-unicorns-of-love-sexy-edition-2585283198569295915
        # Match ID is the trailing numbers: 2585283198569295915
        try:
            # Split by '/' and get the last part
            last_part = href.rstrip('/').split('/')[-1]
            
            # Extract trailing numbers
            # The match ID is typically at the end after the last hyphen
            match_id = ''
            for char in reversed(last_part):
                if char.isdigit():
                    match_id = char + match_id
                else:
                    break  # Stop when we hit a non-digit
            
            if match_id and len(match_id) > 10:  # Match IDs are long numbers
                return match_id
            return None
        except:
            return None

    def get_all_match_ids(self) -> Set[str]:
        """Return all collected match IDs."""
        return self.match_ids

    async def get_matchids(self):
        """Scrape match IDs for LoL and CS2 together. Returns a set of IDs."""
        games = ["lol", "cs2"]
        
        # Parse proxy for Playwright
        proxy_config = None
        if self.proxy_server:
            try:
                # Parse: http://username:password@host:port
                if '@' in self.proxy_server:
                    proto_and_auth = self.proxy_server.split('://')
                    protocol = proto_and_auth[0] if len(proto_and_auth) > 1 else 'http'
                    auth_and_server = proto_and_auth[1] if len(proto_and_auth) > 1 else proto_and_auth[0]
                    
                    auth_part, server_part = auth_and_server.split('@')
                    username, password = auth_part.split(':', 1)
                    
                    proxy_config = {
                        "server": f"{protocol}://{server_part}",
                        "username": username,
                        "password": password
                    }
                    print(f"✅ Proxy configured: {protocol}://{server_part} with auth")
                else:
                    proxy_config = {"server": self.proxy_server}
                    print(f"✅ Proxy configured: {self.proxy_server}")
            except Exception as e:
                print(f"⚠️ Proxy parsing failed: {e}")
        
        async with async_playwright() as playwright:
            try:
                # Choose browser engine
                # Options: chromium, firefox, webkit
                browser_type = os.getenv('PLAYWRIGHT_BROWSER', 'chromium').lower()
                
                print(f"🌐 Using browser: {browser_type}")
                
                if browser_type == 'firefox':
                    # Firefox - often faster and lighter than Chromium
                    browser = await playwright.firefox.launch(
                        headless=True,  # Headless for server environment
                        proxy=proxy_config,
                        firefox_user_prefs={
                            'media.peerconnection.enabled': False,  # Disable WebRTC
                            'media.navigator.enabled': False,
                            'geo.enabled': False,
                            'dom.webdriver.enabled': False,
                        }
                    )
                elif browser_type == 'webkit':
                    # WebKit (Safari engine) - lightest option
                    browser = await playwright.webkit.launch(
                        headless=True,  # Headless for server environment
                        proxy=proxy_config
                    )
                else:  # chromium (default fallback)
                    # Chromium - most compatible but slower
                    browser = await playwright.chromium.launch(
                        headless=True,  # Headless for server environment
                        proxy=proxy_config,
                        args=[
                            "--no-sandbox",
                            "--disable-setuid-sandbox",
                            "--disable-dev-shm-usage",
                            "--disable-gpu",
                            "--disable-software-rasterizer",
                            "--disable-extensions",
                            "--window-size=1920,1080",
                            "--disable-blink-features=AutomationControlled",
                            "--disable-features=IsolateOrigins,site-per-process",
                            "--disable-web-security",
                        ]
                    )
                
                print(f"✅ Playwright browser launched (proxy={bool(proxy_config)})")
                
                # Create context
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                
                page = await context.new_page()
                
                for game in games:
                    path = self.lol_path if game == "lol" else self.cs2_path
                    
                    try:
                        print(f"\n🌐 [{game}] Navigating to: {path}")
                        await page.goto(path, wait_until="domcontentloaded", timeout=120000)
                        print(f"✅ [{game}] Page navigation started")
                        
                        # Give page time to start loading (slow proxy)
                        print(f"⏳ [{game}] Waiting for page to load (proxy is slow)...")
                        await asyncio.sleep(10)
                        
                    except Exception as e:
                        print(f"❌ [{game}] Failed to navigate: {e}")
                        continue
                    
                    # Check for unavailable page
                    try:
                        unavailable = await page.query_selector('div.unavailable')
                        if unavailable:
                            print(f"⚠️ [{game}] Page is unavailable")
                            continue
                    except Exception as e:
                        print(f"⚠️ [{game}] Error checking for unavailable element: {e}")
                    
                    # Retry logic for main scraping
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            print(f"🔍 [{game}] Attempt {attempt + 1}/{max_retries}: Waiting for page to load...")
                            
                            # Wait for page to fully render (slow proxy)
                            await asyncio.sleep(15)
                            
                            # Check if #betby element exists
                            try:
                                await page.wait_for_selector('#betby', timeout=120000)
                                print(f"✅ [{game}] #betby element found, looking for host...")
                            except Exception as e:
                                print(f"⚠️ [{game}] #betby not found: {e}")
                                # Continue anyway
                            
                            # Find the host element with shadow DOM
                            host = await page.query_selector('div[style*="background-color: rgb(30, 28, 37)"]')
                            
                            if not host:
                                print(f"⚠️ [{game}] Host element not found, attempt {attempt + 1}/{max_retries}")
                                if attempt < max_retries - 1:
                                    print(f"⏳ [{game}] Waiting 15 seconds before retry...")
                                    await asyncio.sleep(15)
                                    # Re-navigate
                                    print(f"🔄 [{game}] Re-navigating to page...")
                                    await page.goto(path, wait_until="domcontentloaded", timeout=120000)
                                    continue
                                else:
                                    print(f"❌ [{game}] Failed to find host element after all retries")
                                    print(f"💡 [{game}] CS500 page structure may have changed")
                                    break
                            
                            print(f"✅ [{game}] Host element found, accessing shadow DOM...")
                            
                            # Access shadow root using Playwright's evaluate
                            shadow_root = await host.evaluate_handle('element => element.shadowRoot')
                            
                            if not shadow_root:
                                print(f"⚠️ [{game}] No shadow root found")
                                continue
                            
                            print(f"✅ [{game}] Shadow root accessed")
                            
                            # Query for match links inside shadow DOM
                            links = await shadow_root.query_selector_all('[data-editor-id="eventCardContent"]')
                            print(f"🎯 [{game}] Found {len(links)} match links")
                            
                            if len(links) == 0:
                                print(f"⚠️ [{game}] No match links found - CS500 may have no events")
                                break
                            
                            # Extract match IDs from links (first page)
                            for link in links:
                                try:
                                    href = await link.evaluate('element => element.getAttribute("href")')
                                    if href:
                                        if self.add_match_id_to_set(href):
                                            match_id = self.extract_match_id_from_href(href)
                                            print(f"   ✅ Added match ID: {match_id}")
                                except Exception as e:
                                    print(f"   ⚠️ Error extracting href: {e}")
                                    continue
                            
                            # Check for pagination (exactly like original)
                            pagination_buttons = await shadow_root.query_selector_all('[data-editor-id="eventCardPaginatorArrow"]')
                            if pagination_buttons:
                                continue_pagination = True
                            else:
                                print("No additional pages available")
                                continue_pagination = False
                            
                            # Pagination loop (exactly like original)
                            while continue_pagination:
                                pagination_buttons = await shadow_root.query_selector_all('[data-editor-id="eventCardPaginatorArrow"]')
                                
                                if len(pagination_buttons) >= 2:
                                    # Check if the next button (index 1) is enabled by checking its class
                                    button_class = await pagination_buttons[1].get_attribute('class')
                                    
                                    # The enabled state has class 'sc-abe19l-0 eoRqPp'
                                    if button_class == 'sc-abe19l-0 eoRqPp':
                                        print("Clicking button")
                                        
                                        # Get current count of links before clicking
                                        current_link_count = len(links)
                                        
                                        await pagination_buttons[1].click()
                                        
                                        # Wait for content to update (wait for selector with longer timeout)
                                        print("⏳ Waiting for next page to load...")
                                        try:
                                            # Wait for the DOM to update by waiting for a short moment, then checking if content changed
                                            await asyncio.sleep(2)  # Brief wait for click to register
                                            
                                            # Now wait for new content to load (check multiple times)
                                            max_wait_attempts = 15  # 15 attempts * 1 second = 15 seconds max
                                            for wait_attempt in range(max_wait_attempts):
                                                links = await shadow_root.query_selector_all('[data-editor-id="eventCardContent"]')
                                                new_link_count = len(links)
                                                
                                                # Check if content has updated (links available)
                                                if new_link_count > 0:
                                                    print(f"✅ Page loaded! Found {new_link_count} match links")
                                                    break
                                                
                                                # Wait a bit more
                                                await asyncio.sleep(1)
                                            else:
                                                print(f"⚠️ Timeout waiting for new content")
                                        except Exception as e:
                                            print(f"⚠️ Error waiting for page load: {e}")
                                        
                                        # Re-fetch links after pagination
                                        links = await shadow_root.query_selector_all('[data-editor-id="eventCardContent"]')
                                        print(f"🎯 Processing {len(links)} match links on new page")
                                        
                                        # Extract match IDs from new page
                                        for link in links:
                                            try:
                                                href = await link.evaluate('element => element.getAttribute("href")')
                                                if href:
                                                    if self.add_match_id_to_set(href):
                                                        match_id = self.extract_match_id_from_href(href)
                                                        print(f"   ✅ Added match ID: {match_id}")
                                            except Exception as e:
                                                continue
                                        
                                        print(f"Successfully scraped page")
                                    else:
                                        print("No more pages available - pagination complete")
                                        continue_pagination = False
                                        break
                                else:
                                    print("No more pages available - pagination complete")
                                    continue_pagination = False
                                    break
                            
                            # Completed this game path
                            break  # Success, exit retry loop for this path
                            
                        except Exception as e:
                            print(f"❌ [{game}] Attempt {attempt + 1}/{max_retries} failed: {e}")
                            if attempt < max_retries - 1:
                                print(f"⏳ [{game}] Waiting 15 seconds before retry...")
                                await asyncio.sleep(15)
                                try:
                                    await page.goto(path, wait_until="domcontentloaded", timeout=120000)
                                except:
                                    pass
                            else:
                                print(f"💀 [{game}] All attempts failed")
                                break
                
                await browser.close()
                
                # Print all collected match IDs
                all_ids = self.get_all_match_ids()
                print(f"\n✅ Collected {len(all_ids)} total match IDs: {all_ids}")
                
                return all_ids
                
            except Exception as e:
                print(f"❌ Browser error: {e}")
                return set()


# Test function
async def test_playwright_scraper():
    """Test the Playwright scraper - collects match IDs only."""
    proxy = "http://m23vsbl33lpjnkv-odds-5+100-country-at:7utf02325mih5xj@rp.scrapegw.com:6060"
    
    # Check which browser is being used
    browser_type = os.getenv('PLAYWRIGHT_BROWSER', 'chromium')
    print(f"\n{'='*60}")
    print(f"🧪 Testing CS500 Scraper with Playwright")
    print(f"🌐 Browser: {browser_type.upper()}")
    print(f"🔐 Proxy: Enabled (Canadian residential)")
    print(f"{'='*60}\n")
    
    scraper = CS500ScraperPlaywright(proxy_server=proxy)
    
    # Run match ID collection only
    match_ids = await scraper.get_matchids()
    
    if match_ids:
        print(f"\n{'='*60}")
        print(f"🎉 SUCCESS! Collected {len(match_ids)} match IDs:")
        for match_id in match_ids:
            print(f"   - {match_id}")
        print(f"{'='*60}\n")
        print("ℹ️  Use the original CS500Scraper.get_markets() to fetch market data")
        return match_ids
    else:
        print("\n⚠️ No match IDs found")
        print("This could mean:")
        print("  - CS500 has no events currently")
        print("  - Page is still loading (try increasing timeouts)")
        print("  - Geo-blocking is active")
        return set()


if __name__ == "__main__":
    print("\n💡 TIP: To test different browsers, set PLAYWRIGHT_BROWSER environment variable:")
    print("   Windows: $env:PLAYWRIGHT_BROWSER='firefox'")
    print("   Options: chromium (default), firefox, webkit\n")
    
    asyncio.run(test_playwright_scraper())

