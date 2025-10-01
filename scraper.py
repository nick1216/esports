import requests
import time
import asyncio
import aiohttp
import nodriver as uc
import re
import os
from typing import Dict, Any, List, Optional
from datetime import datetime


class PinnacleScraper:
    """
    A class to scrape esports betting data from Pinnacle Sports API.
    Supports CS2 and League of Legends matchups and markets.
    """
    
    def __init__(self):
        """Initialize the scraper."""
        self.api_key = None
        
    @staticmethod
    def american_to_decimal(american_odds: float) -> float:
        """
        Convert American odds to decimal odds.
        Positive odds: decimal = (american_odds / 100) + 1
        Negative odds: decimal = (100 / abs(american_odds)) + 1
        """
        if american_odds > 0:
            return round((american_odds / 100) + 1, 2)
        else:
            return round((100 / abs(american_odds)) + 1, 2)
    
    def get_pinnacle_api_key(self, pinnacle_api_url: str) -> str:
        """Fetch the API key from Pinnacle's config endpoint."""
        res = requests.get(pinnacle_api_url)
        return res.json()["api"]["haywire"]["apiKey"]
    
    def _setup_headers(self, pinnacle_api_url: str, base_headers: Dict[str, str]) -> Dict[str, str]:
        """Setup headers for API requests."""
        if not self.api_key:
            self.api_key = self.get_pinnacle_api_key(pinnacle_api_url)
            
        # Create a copy of base headers and add the API key
        headers = base_headers.copy()
        headers["x-api-key"] = self.api_key
        return headers

    def get_event_name(self, matchup):
        return matchup.get('league', {}).get('name', '')

    def get_start_time(self, matchup):
        start_time = matchup.get('startTime')
        return datetime.fromisoformat(start_time.replace('Z', '+00:00')).timestamp()
    
    def get_matchups(self, matchups_url: str, pinnacle_api_url: str, base_headers: Dict[str, str]) -> Dict[str, Any]:
        """Fetch and process matchups for CS2 and League of Legends."""
        headers = self._setup_headers(pinnacle_api_url, base_headers)
        res = requests.get(matchups_url, headers=headers)

        matchups = []
        seen_matchups = set()  # Track unique matchups to avoid duplicates
        
        for matchup in res.json():
            start_time = self.get_start_time(matchup)
            if matchup.get('isLive') == 'true' or start_time < time.time():
                continue

            # Filter by game name - only include CS2 and League of Legends
            league_name = self.get_event_name(matchup)
            if 'CS2' not in league_name and 'League of Legends' not in league_name:
                continue
                
            matchup_id = None
            participants = None
            
            # Case 1: Match has parent with participants
            if matchup.get('parent') is not None and 'participants' in matchup['parent']:
                matchup_id = matchup['parentId']
                participants = matchup['parent']['participants']
            
            # Case 2: Match has participants directly
            elif matchup.get('participants') is not None and matchup.get('parent') is None:
                matchup_id = matchup['id']
                participants = matchup['participants']
            
            # Process the match if we found valid participants
            if matchup_id and participants:
                matchup_data = {
                    'id': matchup_id,
                    'event': league_name,
                    'isLive': matchup.get('isLive'),
                    'start_time': matchup.get('startTime'),
                    'home_team': None,
                    'away_team': None
                }
                
                for team in participants:
                    if team.get('alignment') == 'home':
                        matchup_data['home_team'] = team['name']
                    else:
                        matchup_data['away_team'] = team['name']
                
                # Only add if we have both teams and it's not a duplicate
                if matchup_data['home_team'] and matchup_data['away_team']:
                    # Create a unique key for deduplication
                    matchup_key = f"{matchup_data['home_team']} vs {matchup_data['away_team']} ({matchup_data['event']})"
                    
                    if matchup_key not in seen_matchups:
                        seen_matchups.add(matchup_key)
                        matchups.append(matchup_data)
        
        return {
            'count': len(matchups),
            'matchups': matchups
        }
    
    def multiplicative_devig(self, home_odds: float, away_odds: float) -> tuple[float, float]:
        """
        Multiplicative (proportional) method for de-vigging odds.
        This is the traditional/standard way to remove vig.
        Fair probabilities: p1* = p1 / (p1 + p2)
        Fair odds = 1 / fair_probability
        """
        # Convert odds to implied probabilities
        p1 = 1.0 / home_odds  # home probability
        p2 = 1.0 / away_odds  # away probability
        
        # Total overround (should be > 1 due to vig)
        total = p1 + p2
        
        # Remove vig proportionally
        fair_p1 = p1 / total
        fair_p2 = p2 / total
        
        # Convert back to fair odds
        fair_home = 1.0 / fair_p1
        fair_away = 1.0 / fair_p2
        
        return fair_home, fair_away
    
    def power_method_devig(self, home_odds: float, away_odds: float, k: float = 1.07) -> tuple[float, float]:
        """
        Power method for de-vigging odds.
        Fair probabilities: p1* = p1^k / (p1^k + p2^k)
        Fair odds = 1 / fair_probability
        """
        # Convert odds to probabilities
        p1 = 1.0 / home_odds  # home probability
        p2 = 1.0 / away_odds   # away probability
        
        # Apply power method
        p1_k = p1 ** k
        p2_k = p2 ** k
        sum_pk = p1_k + p2_k
        
        # Fair probabilities
        fair_p1 = p1_k / sum_pk
        fair_p2 = p2_k / sum_pk
        
        # Convert back to fair odds
        fair_home = 1.0 / fair_p1
        fair_away = 1.0 / fair_p2
        
        return fair_home, fair_away

    def get_markets(self, markets_url: str, matchups: List[Dict[str, Any]], pinnacle_api_url: str, base_headers: Dict[str, str]) -> Dict[str, Any]:
        """Fetch and process markets for the given matchups."""
        headers = self._setup_headers(pinnacle_api_url, base_headers)
        res = requests.get(markets_url, headers=headers)

        # Create a lookup dictionary for matchup data by ID
        matchup_lookup = {matchup['id']: matchup for matchup in matchups['matchups']}
        markets = []
        
        found_market_ids = set()

        for market in res.json():
            matchup_id = market['matchupId']
            
            # Skip if not a valid matchup or not a main match market
            if matchup_id not in matchup_lookup or '0' not in market['key']:
                continue
            
            matchup_data = matchup_lookup[matchup_id]
            
            # Extract raw odds from prices
            home_odds_raw = None
            away_odds_raw = None
            
            for price in market['prices']:
                if price.get('designation') == 'home':
                    home_odds_raw = self.american_to_decimal(price['price'])
                else:
                    away_odds_raw = self.american_to_decimal(price['price'])
            
            # Only process if we have both odds
            if home_odds_raw and away_odds_raw:
                # Apply both de-vigging methods
                mult_home, mult_away = self.multiplicative_devig(home_odds_raw, away_odds_raw)
                power_home, power_away = self.power_method_devig(home_odds_raw, away_odds_raw)
                
                # Calculate the actual fair probabilities (these will sum to exactly 100%)
                power_home_prob = 1.0 / power_home
                power_away_prob = 1.0 / power_away
                mult_home_prob = 1.0 / mult_home
                mult_away_prob = 1.0 / mult_away
                
                market_data = {
                    'id': matchup_id,
                    'event': matchup_data['event'],
                    'home_team': matchup_data['home_team'],
                    'away_team': matchup_data['away_team'],
                    'home_fair_odds': round(power_home, 2),  # Power method (default)
                    'away_fair_odds': round(power_away, 2),  # Power method (default)
                    'home_mult_odds': round(mult_home, 2),  # Multiplicative method
                    'away_mult_odds': round(mult_away, 2),  # Multiplicative method
                    'home_fair_prob': round(power_home_prob, 6),  # Store exact probability
                    'away_fair_prob': round(power_away_prob, 6),  # Store exact probability
                    'home_mult_prob': round(mult_home_prob, 6),  # Store exact probability
                    'away_mult_prob': round(mult_away_prob, 6),  # Store exact probability
                    'start_time': matchup_data.get('start_time')
                }
                
                found_market_ids.add(matchup_id)
                markets.append(market_data)
        
        return {
            'count': len(markets),
            'markets': markets
        }
    
    def scrape_data(self, pinnacle_api_url: str, matchups_url: str, markets_url: str, base_headers: Dict[str, str]) -> List[Dict[str, Any]]:
        """Main method to scrape all data - matchups and markets."""
        matchups = self.get_matchups(matchups_url, pinnacle_api_url, base_headers)
        markets = self.get_markets(markets_url, matchups, pinnacle_api_url, base_headers)
        return markets

class CS500Scraper:

    def __init__(self, proxy_server: Optional[str] = None):
        """
        Initialize CS500 scraper.
        
        Args:
            proxy_server: Optional proxy server URL (e.g., 'http://proxy:port' or 'socks5://proxy:port')
                         Can also be set via PROXY_SERVER environment variable
        """
        self.brand_id = "2195256717934206976"
        self.base_url = f"https://api-h-c7818b61-608.sptpub.com/api/v3/prematch/brand/{self.brand_id}/event/en"
        self.lol_path = "https://csgo500.com/sports?bt-path=%2Fleague-of-legends-110"
        self.cs2_path = "https://csgo500.com/sports?bt-path=%2Fcounter-strike-109"
        self.match_ids = set()  # Set to store extracted match IDs
        
        # Get proxy from parameter or environment variable
        self.proxy_server = proxy_server or os.getenv('PROXY_SERVER')
        if self.proxy_server:
            print(f"🌐 Using proxy: {self.proxy_server}")
            self._test_proxy()
    
    def _test_proxy(self):
        """Test if proxy is accessible."""
        try:
            print(f"🧪 Testing proxy connection...")
            import urllib.request
            
            proxy_handler = urllib.request.ProxyHandler({
                'http': self.proxy_server,
                'https': self.proxy_server
            })
            opener = urllib.request.build_opener(proxy_handler)
            opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
            
            # Try to get IP info through proxy
            response = opener.open('https://api.ipify.org?format=json', timeout=10)
            ip_data = response.read().decode('utf-8')
            print(f"✅ Proxy working! Your IP through proxy: {ip_data}")
            
        except Exception as e:
            print(f"⚠️ Proxy test failed: {e}")
            print(f"⚠️ This may cause issues with CS500 scraping")

    def extract_match_id_from_href(self, href: str) -> Optional[str]:
        """
        Extract the numeric ID from the end of an href URL.
        
        Args:
            href: The href URL string (e.g., '/league-of-legends/league-of-legends/a--lck-cl-2025-season-playoffs/t1-esports-academy-fearx-youth-2583358020624977922')
            
        Returns:
            The extracted numeric ID as a string, or None if no match found
        """
        # Use regex to find the numeric ID at the end of the href
        # Pattern matches digits at the end of the string after a dash or at the end
        match = re.search(r'-(\d+)$', href)
        if match:
            return match.group(1)
        return None

    def add_match_id_to_set(self, href: str) -> bool:
        """
        Extract match ID from href and add it to the set.
        
        Args:
            href: The href URL string
            
        Returns:
            True if a match ID was found and added, False otherwise
        """
        match_id = self.extract_match_id_from_href(href)
        if match_id:
            self.match_ids.add(match_id)
            return True
        return False

    def get_all_match_ids(self) -> set:
        """
        Get all collected match IDs.
        
        Returns:
            Set of all collected match IDs
        """
        return self.match_ids.copy()

    def clear_match_ids(self):
        """Clear all collected match IDs."""
        self.match_ids.clear()

    async def fetch_matchids(self, links):
        for link in links:
            href = link.attrs['href']
            if self.add_match_id_to_set(href):
                match_id = self.extract_match_id_from_href(href)
                print(f"Added match ID: {match_id}")
            else:
                print(f"No match ID found in href: {href}")

    async def get_matchids(self):
        """Scrape match IDs for LoL and CS2 together. Returns a set of IDs."""
        games: List[str] = ["lol", "cs2"]

        try:
            # Try headless mode with stealth configurations
            # nodriver has built-in anti-detection that works in headless
            
            # Browser arguments for stealth in Docker/Railway
            browser_args = [
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
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ]
            
            # Add proxy configuration if provided
            if self.proxy_server:
                # Parse proxy URL to extract host:port (Chrome doesn't support auth in --proxy-server)
                # Format: http://user:pass@host:port or socks5://user:pass@host:port
                try:
                    if '@' in self.proxy_server:
                        # Extract just the host:port part for Chrome
                        proxy_parts = self.proxy_server.split('@')
                        host_port = proxy_parts[1] if len(proxy_parts) > 1 else self.proxy_server
                        
                        # Try SOCKS5 protocol (often more reliable)
                        browser_args.append(f"--proxy-server=socks5://{host_port}")
                        print(f"🌐 Browser configured with SOCKS5 proxy: socks5://{host_port}")
                    else:
                        browser_args.append(f"--proxy-server={self.proxy_server}")
                        print(f"🌐 Browser configured with proxy: {self.proxy_server}")
                except Exception as e:
                    print(f"⚠️ Proxy configuration failed: {e}")
                    print(f"⚠️ Continuing without proxy...")
            
            browser_config = {
                "headless": False,  # Headless with stealth
                "browser_args": browser_args,
            }
            
            print(f"🔧 Browser config: headless=True (with stealth), proxy={bool(self.proxy_server)}")
            
            browser = await uc.start(**browser_config)
        except Exception as e:
            print(f"Failed to start browser: {e}")
            print("This might be due to running in a server environment without display support")
            return set()
        try:
            for g in games:
                path = self.lol_path if g == "lol" else self.cs2_path
                try:
                    print(f"🌐 [{g}] Navigating to: {path}")
                    page = await browser.get(path)
                    print(f"✅ [{g}] Page navigation started")
                    
                    # Give page time to start loading
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    print(f"❌ [{g}] Failed to navigate: {e}")
                    continue

                # Check for unavailable page with proper error handling
                try:
                    unavailable_element = await page.select('div.unavailable')
                    if unavailable_element:
                        print(f"⚠️ [{g}] Page is unavailable")
                        continue
                except Exception as e:
                    print(f"⚠️ [{g}] Error checking for unavailable element: {e}")

                # Add retry logic for the main scraping
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        print(f"🔍 [{g}] Attempt {attempt + 1}/{max_retries}: Waiting for page to load...")
                        
                        # Wait for page to fully render
                        await asyncio.sleep(8)
                        
                        # Check if #betby element exists
                        try:
                            await page.wait_for('#betby', timeout=15)
                            print(f"✅ [{g}] #betby element found, looking for host...")
                        except Exception as e:
                            print(f"⚠️ [{g}] #betby not found: {e}")
                            # Try to continue anyway - element might not be required
                        
                        # Try to find the host element with shadow DOM
                        host = await page.select('div[style*="background-color: rgb(30, 28, 37)"]')
                        
                        if not host:
                            print(f"⚠️ [{g}] Host element not found, attempt {attempt + 1}/{max_retries}")
                            if attempt < max_retries - 1:
                                print(f"⏳ [{g}] Waiting 10 seconds before retry...")
                                await asyncio.sleep(10)
                                # Try navigating to the page again
                                print(f"🔄 [{g}] Re-navigating to page...")
                                await page.get(path)
                                continue
                            else:
                                print(f"❌ [{g}] Failed to find host element after all retries")
                                print(f"💡 [{g}] CS500 page structure may have changed")
                                break
                        
                        print(f"✅ [{g}] Host element found, accessing shadow DOM...")
                        
                        try:
                            await host.update()
                            if not host.shadow_children or len(host.shadow_children) == 0:
                                print(f"⚠️ [{g}] No shadow children found")
                                continue
                            
                            root = host.shadow_children[0]
                            print(f"✅ [{g}] Shadow root accessed")
                        except Exception as e:
                            print(f"❌ [{g}] Shadow DOM access failed: {e}")
                            continue

                        links = await root.query_selector_all('[data-editor-id="eventCardContent"]')
                        print(f"🎯 [{g}] Found {len(links)} match links")
                        
                        if len(links) == 0:
                            print(f"⚠️ [{g}] No match links found - CS500 may have no events")
                            break
                        
                        await self.fetch_matchids(links)


                        pagination_button = await root.query_selector_all('[data-editor-id="eventCardPaginatorArrow"]')
                        if pagination_button:
                            continue_pagination = True
                        else:
                            print("No additional pages available")
                            continue_pagination = False
                        
                        while continue_pagination:
                            pagination_button = await root.query_selector_all('[data-editor-id="eventCardPaginatorArrow"]')

                            if pagination_button[1].attrs['class_'] == 'sc-abe19l-0 eoRqPp':
                                print("Clicking button")
                                await pagination_button[1].click()

                                links = await root.query_selector_all('[data-editor-id="eventCardContent"]')
                                await self.fetch_matchids(links)
                                print(f"Successfully scraped page")
                            else:
                                print("No more pages available - pagination complete")
                                continue_pagination = False
                                break
                        
                        # Completed this game path
                        break  # Success, exit retry loop for this path
                        
                    except Exception as e:
                        print(f"❌ [{g}] Attempt {attempt + 1}/{max_retries} failed: {e}")
                        if attempt < max_retries - 1:
                            print(f"⏳ [{g}] Waiting 5 seconds before retry...")
                            await asyncio.sleep(5)  # Longer wait for proxy
                            # Try navigating to the page again
                            try:
                                print(f"🔄 [{g}] Reloading page...")
                                await page.reload()
                            except:
                                pass
                        else:
                            print(f"💀 [{g}] All attempts failed. Possible causes:")
                            print(f"   - Proxy is too slow or blocked")
                            print(f"   - CS500 is down or changed layout")
                            print(f"   - Page requires longer load time")
                            break

            # Print and return all collected match IDs
            all_ids = self.get_all_match_ids()
            print(f"\n✅ Collected {len(all_ids)} total match IDs: {all_ids}")
            
            # Note: Match IDs are stored in database by the API endpoint, not sent here
            # The calling function (in api.py) handles database storage
            
            return all_ids

        finally:
            browser.stop()

    async def get_markets(self, match_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Asynchronously fetch markets for all match IDs.
        
        Args:
            match_ids: List of match IDs to fetch markets for
            game: Optional game filter (not used in current implementation)
            
        Returns:
            List of market data dictionaries sorted by start_time
        """
        if not match_ids:
            return []
        
        # Define headers for API requests
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Host": "api-h-c7818b61-608.sptpub.com",
            "Origin": "https://csgo500.com",
            "Pragma": "no-cache",
            "Referer": "https://csgo500.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"'
        }
        
        async def fetch_single_market(session: aiohttp.ClientSession, match_id: str) -> Optional[Dict[str, Any]]:
            """Fetch market data for a single match ID (no proxy)."""
            try:
                url = f"{self.base_url}/{match_id}"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_market_data(data, match_id)
                    else:
                        print(f"Failed to fetch market for match {match_id}: HTTP {response.status}")
                        return None
            except Exception as e:
                print(f"Error fetching market for match {match_id}: {e}")
                return None
        
        async def fetch_single_market_with_proxy(session: aiohttp.ClientSession, match_id: str, proxy: str) -> Optional[Dict[str, Any]]:
            """Fetch market data for a single match ID through proxy."""
            try:
                url = f"{self.base_url}/{match_id}"
                async with session.get(url, headers=headers, proxy=proxy) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_market_data(data, match_id)
                    else:
                        print(f"⚠️ Failed to fetch market {match_id} via proxy: HTTP {response.status}")
                        return None
            except Exception as e:
                print(f"❌ Error fetching market {match_id} via proxy: {e}")
                return None
        
        # Create session with timeout and proxy
        timeout = aiohttp.ClientTimeout(total=30)
        
        # Configure proxy for aiohttp if available
        connector = None
        if self.proxy_server:
            print(f"🌐 Using proxy for market API calls: {self.proxy_server}")
            # aiohttp uses a different proxy format
            connector = aiohttp.TCPConnector()
        
        session_kwargs = {"timeout": timeout}
        if connector:
            session_kwargs["connector"] = connector
        
        async with aiohttp.ClientSession(**session_kwargs) as session:
            # Create tasks for all match IDs
            # Pass proxy URL to each request
            if self.proxy_server:
                tasks = [fetch_single_market_with_proxy(session, match_id, self.proxy_server) for match_id in match_ids]
            else:
                tasks = [fetch_single_market(session, match_id) for match_id in match_ids]
            
            # Execute all requests concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out None results and exceptions
            markets = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"Exception for match {match_ids[i]}: {result}")
                elif result is not None:
                    markets.append(result)
            
            # Sort by start_time
            markets.sort(key=lambda x: x.get('start_time', 0))
            
            return markets
    
    def _parse_market_data(self, data: Dict[str, Any], match_id: str) -> Dict[str, Any]:
        """
        Parse market data from API response.
        
        Args:
            data: Raw API response data
            match_id: The match ID for this market
            
        Returns:
            Parsed market data dictionary
        """
        try:
            root = data['events'][match_id]
            tournament = root['desc']['tournament']
            market_info = {
                'match_id': match_id,
                'event_name': data['tournaments'][tournament]['name'],
                'start_time': root['desc']['scheduled'],
                'home_team': root['desc']['competitors'][0]['name'],
                'away_team': root['desc']['competitors'][1]['name'],
                'status': root['state']['status'],
                'markets': []
            }
            
            if 'markets' in root:
                for market in root['markets']:
                    if market == '186':
                         moneyline_data = {
                             'name': 'moneyline',
                             'home odds': root['markets'][market]['']['4']['k'],
                             'away odds': root['markets'][market]['']['5']['k']
                         }
                         market_info['markets'].append(moneyline_data)
            
            return market_info
            
        except Exception as e:
            print(f"Error parsing market data for match {match_id}: {e}")
            return None

    async def scrape_all_data(self) -> List[Dict[str, Any]]:
        """
        Complete workflow: scrape match IDs and then fetch all markets asynchronously.
        
        Returns:
            List of market data for all found matches
        """
        try:
            await self.get_matchids()
        except Exception as e:
            print(f"Failed to get match IDs: {e}")
            return []

        # Get the collected match IDs
        match_ids = list(self.get_all_match_ids())
        print(f"Found {len(match_ids)} match IDs")
        
        if not match_ids:
            print("No match IDs found to fetch markets for.")
            return []
        
        # Now fetch markets for all match IDs asynchronously
        print("Fetching markets for all matches...")
        markets = await self.get_markets(match_ids)
        
        print(f"Successfully fetched markets for {len(markets)} matches")
        return markets


# def main():
#     """Main function to demonstrate the PinnacleScraper class usage."""
#     # Define URLs
#     pinnacle_api_url = "https://www.pinnacle.com/config/app.json?app=esports-hub"
#     matchups_url = "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups?withSpecials=true&withThreeWaySpecials=true&brandId=0"
#     markets_url = "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/markets/straight?primaryOnly=false&withSpecials=true&withThreeWaySpecials=true&moneylineOnly=true"
    
#     # Define base headers
#     base_headers = {
#         "Accept": "application/json",
#         "Accept-Encoding": "gzip, deflate, br, zstd",
#         "Cache-Control": "no-cache",
#         "Connection": "keep-alive",
#         "Content-Type": "application/json",
#         "Pragma": "no-cache",
#         "Host": "guest.api.arcadia.pinnacle.com",
#         "Origin": "https://www.pinnacle.com",
#         "Referer": "https://www.pinnacle.com/",
#         "sec-ch-ua-platform": "Windows",
#         "Sec-Fetch-Dest": "empty",
#         "Sec-Fetch-Mode": "cors",
#         "Sec-Fetch-Site": "same-origin",
#         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
#         "x-device-uuid": "d82e8138-c9f6c8ae-bfc66d9f-a7c69c7c"
#     }
    
#     scraper = PinnacleScraper()
#     markets = scraper.scrape_data(pinnacle_api_url, matchups_url, markets_url, base_headers)
    
#     print(markets)

# if __name__ == "__main__":
#     main()