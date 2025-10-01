from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from database import Database
from scraper import PinnacleScraper, CS500Scraper
from scraper_playwright import CS500ScraperPlaywright
from functions import find_best_match, infer_sport_from_pinnacle_event, infer_sport_from_cs500_event

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Esports Betting EV Finder", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database and scrapers
db = Database()
pinnacle_scraper = PinnacleScraper()
# CS500Scraper for market data (API calls only, no browser)
cs500_scraper = CS500Scraper()
# CS500ScraperPlaywright for match IDs (browser automation with proxy)
# Will automatically use PROXY_SERVER environment variable if set
cs500_playwright_scraper = CS500ScraperPlaywright()

# Pinnacle configuration
PINNACLE_CONFIG = {
    "api_url": "https://www.pinnacle.com/config/app.json?app=esports-hub",
    "matchups_url": "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups?withSpecials=true&withThreeWaySpecials=true&brandId=0",
    "markets_url": "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/markets/straight?primaryOnly=false&withSpecials=true&withThreeWaySpecials=true&moneylineOnly=true",
    "headers": {
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Pragma": "no-cache",
        "Host": "guest.api.arcadia.pinnacle.com",
        "Origin": "https://www.pinnacle.com",
        "Referer": "https://www.pinnacle.com/",
        "sec-ch-ua-platform": "Windows",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "x-device-uuid": "d82e8138-c9f6c8ae-bfc66d9f-a7c69c7c"
    }
}

# Initialize scheduler
scheduler = AsyncIOScheduler()
scheduler_running = False
scheduler_config = {
    "enabled": False,
    "pinnacle_interval": 5,  # minutes
    "cs500_interval": 5,     # minutes
    "last_pinnacle_scrape": None,
    "last_cs500_scrape": None,
    "last_match": None
}


# Scheduled scraping tasks
async def scheduled_scrape_pinnacle():
    """Background task to scrape Pinnacle on schedule."""
    try:
        logger.info("🔄 Scheduled Pinnacle scrape started")
        markets_data = pinnacle_scraper.scrape_data(
            PINNACLE_CONFIG["api_url"],
            PINNACLE_CONFIG["matchups_url"],
            PINNACLE_CONFIG["markets_url"],
            PINNACLE_CONFIG["headers"]
        )
        
        markets = markets_data.get('markets', [])
        db.store_pinnacle_markets(markets)
        
        scheduler_config["last_pinnacle_scrape"] = datetime.now().isoformat()
        logger.info(f"✅ Scheduled Pinnacle scrape completed: {len(markets)} markets")
    except Exception as e:
        logger.error(f"❌ Scheduled Pinnacle scrape failed: {str(e)}")


async def scheduled_scrape_cs500():
    """Background task to scrape CS500 on schedule."""
    try:
        logger.info("🔄 Scheduled CS500 scrape started")
        match_ids = db.get_cs500_match_ids()
        
        if not match_ids:
            logger.warning("⚠️ No CS500 match IDs available for scheduled scrape")
            return
        
        markets = await cs500_scraper.get_markets(match_ids)
        db.store_cs500_markets(markets)
        
        scheduler_config["last_cs500_scrape"] = datetime.now().isoformat()
        logger.info(f"✅ Scheduled CS500 scrape completed: {len(markets)} markets")
    except Exception as e:
        logger.error(f"❌ Scheduled CS500 scrape failed: {str(e)}")


async def scheduled_match_markets():
    """Background task to match markets on schedule."""
    try:
        logger.info("🔄 Scheduled market matching started")
        pinnacle_markets = db.get_active_pinnacle_markets()
        cs500_markets = db.get_active_cs500_markets()
        
        already_mapped_ids = db.get_mapped_pinnacle_ids()
        unmapped_markets = [m for m in pinnacle_markets if m["id"] not in already_mapped_ids]
        
        matched_count = 0
        
        for p_market in unmapped_markets:
            p_game = {
                "home_team": p_market["home_team"],
                "away_team": p_market["away_team"],
                "event": p_market["event"],
                "start_time": p_market.get("start_time")
            }
            
            cs500_games = []
            for c_market in cs500_markets:
                cs500_games.append({
                    "home_team": c_market["home_team"],
                    "away_team": c_market["away_team"],
                    "event_name": c_market["event_name"],
                    "start_time": c_market.get("start_time"),
                    "match_id": c_market["match_id"]
                })
            
            best_match, confidence = find_best_match(p_game, cs500_games)
            
            if best_match and confidence > 0.6:
                db.store_match_mapping(
                    p_market["id"],
                    best_match["match_id"],
                    confidence
                )
                matched_count += 1
        
        scheduler_config["last_match"] = datetime.now().isoformat()
        logger.info(f"✅ Scheduled matching completed: {matched_count} new matches")
    except Exception as e:
        logger.error(f"❌ Scheduled matching failed: {str(e)}")


async def scheduled_capture_closing_lines():
    """Background task to capture closing lines for markets near start time."""
    try:
        logger.info("🔄 Capturing closing lines")
        count = db.capture_closing_lines()
        if count > 0:
            logger.info(f"✅ Captured closing lines for {count} markets")
            # Update CLV for any bets on those markets
            clv_count = db.update_all_pending_clv()
            if clv_count > 0:
                logger.info(f"✅ Updated CLV for {clv_count} bets")
        
        # Delete matches that have started but have no EV data
        deleted = db.delete_started_matches_without_ev()
        if deleted > 0:
            logger.info(f"🗑️ Deleted {deleted} started matches without EV data")
    except Exception as e:
        logger.error(f"❌ Closing line capture failed: {str(e)}")


async def scheduled_scrape_all():
    """Combined scheduled task: scrape both sources and match."""
    await scheduled_scrape_pinnacle()
    await scheduled_scrape_cs500()
    await scheduled_match_markets()
    await scheduled_capture_closing_lines()


@app.on_event("startup")
async def startup_event():
    """Start the scheduler when the app starts."""
    global scheduler_running
    if not scheduler_running:
        scheduler.start()
        scheduler_running = True
        logger.info("📅 Scheduler initialized (not running tasks yet)")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown the scheduler when the app stops."""
    global scheduler_running
    if scheduler_running:
        scheduler.shutdown()
        scheduler_running = False
        logger.info("📅 Scheduler shutdown")


@app.get("/")
async def root():
    """Serve the main HTML page."""
    return FileResponse("static/index.html")


@app.get("/api/check-ip")
async def check_railway_ip():
    """
    Check Railway's outbound IP address by calling ipify.org.
    This is the IP that needs to be whitelisted at ProxyScrape.
    """
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.ipify.org?format=json', timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "success",
                        "railway_ip": data.get("ip"),
                        "message": f"Railway's outbound IP is: {data.get('ip')}",
                        "instruction": "Whitelist this IP address in your ProxyScrape dashboard"
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Failed to check IP: HTTP {response.status}"
                    }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to check IP: {str(e)}"
        }


@app.get("/bets")
async def bets_page():
    """Serve the bet logs page."""
    return FileResponse("static/bets.html")


@app.get("/archive")
async def archive_page():
    """Serve the match archive page."""
    return FileResponse("static/archive.html")


@app.post("/cs500_matchids")
async def receive_cs500_matchids(match_ids: List[str]):
    """Receive CS500 match IDs from the scraper."""
    db.store_cs500_match_ids(match_ids)
    return {"status": "success", "count": len(match_ids), "match_ids": match_ids}


@app.get("/api/cs500_matchids")
async def get_cs500_matchids():
    """Get all stored CS500 match IDs."""
    match_ids = db.get_cs500_match_ids()
    return {"count": len(match_ids), "match_ids": match_ids}


@app.post("/api/scrape/pinnacle")
async def scrape_pinnacle(background_tasks: BackgroundTasks):
    """Scrape Pinnacle markets and store them."""
    try:
        markets_data = pinnacle_scraper.scrape_data(
            PINNACLE_CONFIG["api_url"],
            PINNACLE_CONFIG["matchups_url"],
            PINNACLE_CONFIG["markets_url"],
            PINNACLE_CONFIG["headers"]
        )
        
        markets = markets_data.get('markets', [])
        db.store_pinnacle_markets(markets)
        
        return {
            "status": "success",
            "message": f"Scraped {len(markets)} Pinnacle markets",
            "count": len(markets)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scrape Pinnacle: {str(e)}")


@app.post("/api/scrape/cs500-matchids")
async def scrape_cs500_matchids():
    """
    Scrape CS500 match IDs using browser automation.
    This runs the headless browser to collect match IDs from CS500.
    """
    try:
        logger.info("🎮 Starting CS500 match ID scraper (browser automation)")
        
        # Run browser automation to get match IDs using Playwright
        match_ids = await cs500_playwright_scraper.get_matchids()
        
        if not match_ids or len(match_ids) == 0:
            return {
                "status": "warning",
                "message": "No CS500 match IDs found. CS500 might be down or have no matches.",
                "match_ids_count": 0
            }
        
        # Store match IDs in database
        db.store_cs500_match_ids(list(match_ids))
        
        logger.info(f"✅ Collected {len(match_ids)} CS500 match IDs")
        
        return {
            "status": "success",
            "message": f"Scraped {len(match_ids)} CS500 match IDs successfully",
            "match_ids_count": len(match_ids),
            "match_ids": list(match_ids)
        }
    except Exception as e:
        logger.error(f"❌ CS500 match ID scraping failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to scrape CS500 match IDs: {str(e)}")


@app.post("/api/scrape/cs500")
async def scrape_cs500(background_tasks: BackgroundTasks):
    """Scrape CS500 markets using existing match IDs in database."""
    try:
        # Get match IDs from database
        match_ids = db.get_cs500_match_ids()
        
        if not match_ids:
            return {
                "status": "warning",
                "message": "No CS500 match IDs available. Run /api/scrape/cs500-matchids first.",
                "count": 0
            }
        
        # Fetch markets for the match IDs
        markets = await cs500_scraper.get_markets(match_ids)
        db.store_cs500_markets(markets)
        
        return {
            "status": "success",
            "message": f"Scraped {len(markets)} CS500 markets",
            "count": len(markets)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scrape CS500: {str(e)}")


async def _run_cs500_full_scrape():
    """Background task to run full CS500 scrape."""
    try:
        logger.info("🎮 Starting full CS500 scrape (match IDs + markets)")
        
        # Step 1: Get match IDs via browser automation using Playwright
        logger.info("Step 1: Collecting match IDs...")
        match_ids = await cs500_playwright_scraper.get_matchids()
        
        if not match_ids or len(match_ids) == 0:
            logger.warning("⚠️ No CS500 match IDs found")
            return
        
        # Store match IDs
        db.store_cs500_match_ids(list(match_ids))
        logger.info(f"✅ Collected {len(match_ids)} match IDs")
        
        # Step 2: Scrape markets for those IDs
        logger.info("Step 2: Scraping markets...")
        markets = await cs500_scraper.get_markets(match_ids)
        db.store_cs500_markets(markets)
        logger.info(f"✅ Scraped {len(markets)} markets")
        
    except Exception as e:
        logger.error(f"❌ Full CS500 scrape failed: {str(e)}")


@app.post("/api/scrape/cs500-full")
async def scrape_cs500_full(background_tasks: BackgroundTasks):
    """
    Complete CS500 scraping flow:
    1. Run browser automation to get match IDs
    2. Scrape markets for those match IDs
    3. Store everything in database
    
    This endpoint runs the scraping in the background to avoid timeouts.
    Check the logs to see progress.
    """
    try:
        # Add the scraping task to background tasks
        background_tasks.add_task(_run_cs500_full_scrape)
        
        return {
            "status": "success",
            "message": "CS500 scraping started in background. Check logs for progress.",
            "note": "This may take 1-2 minutes. Refresh the page to see updated data."
        }
    except Exception as e:
        logger.error(f"❌ Failed to start CS500 scrape: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start CS500 scrape: {str(e)}")


@app.post("/api/match_markets")
async def match_markets():
    """Match Pinnacle markets with CS500 markets using AI matching.
    
    Only runs AI matching on markets that don't already have a mapping.
    This avoids re-matching already paired games and saves computation.
    """
    try:
        pinnacle_markets = db.get_active_pinnacle_markets()
        cs500_markets = db.get_active_cs500_markets()
        
        # Get all Pinnacle IDs that already have mappings
        already_mapped_ids = db.get_mapped_pinnacle_ids()
        
        # Filter to only unmapped Pinnacle markets
        unmapped_markets = [m for m in pinnacle_markets if m["id"] not in already_mapped_ids]
        
        matched_count = 0
        skipped_count = len(already_mapped_ids)
        
        # Only run AI matching on unmapped markets
        for p_market in unmapped_markets:
            # Convert Pinnacle market to format expected by matching function
            p_game = {
                "home_team": p_market["home_team"],
                "away_team": p_market["away_team"],
                "event": p_market["event"],
                "start_time": p_market.get("start_time")
            }
            
            # Convert CS500 markets to format expected by matching function
            cs500_games = []
            for c_market in cs500_markets:
                cs500_games.append({
                    "home_team": c_market["home_team"],
                    "away_team": c_market["away_team"],
                    "event_name": c_market["event_name"],
                    "start_time": c_market.get("start_time"),
                    "match_id": c_market["match_id"]
                })
            
            # Find best match using AI
            best_match, confidence = find_best_match(p_game, cs500_games)
            
            if best_match and confidence > 0.6:
                db.store_match_mapping(
                    p_market["id"],
                    best_match["match_id"],
                    confidence
                )
                matched_count += 1
        
        return {
            "status": "success",
            "message": f"Matched {matched_count} new markets (skipped {skipped_count} already mapped)",
            "matched_count": matched_count,
            "skipped_count": skipped_count,
            "total_pinnacle": len(pinnacle_markets),
            "total_cs500": len(cs500_markets),
            "unmapped_markets": len(unmapped_markets)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to match markets: {str(e)}")


@app.get("/api/markets")
async def get_markets(min_ev: float = 0.0, sport: Optional[str] = None):
    """Get all matched markets with EV calculations."""
    try:
        markets = db.get_matched_markets()
        
        # Filter by sport if specified
        if sport:
            markets = [m for m in markets if m.get('sport') == sport]
        
        # Filter by minimum EV
        if min_ev > 0:
            markets = [m for m in markets if m['home_ev_pct'] >= min_ev or m['away_ev_pct'] >= min_ev]
        
        # Sort by best EV descending
        markets.sort(key=lambda x: x.get('best_ev_pct', -100), reverse=True)
        
        return {
            "status": "success",
            "count": len(markets),
            "markets": markets
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get markets: {str(e)}")


@app.get("/api/markets/positive")
async def get_positive_ev_markets(min_ev: float = 0.0, sport: Optional[str] = None):
    """Get only markets with positive EV."""
    try:
        markets = db.get_positive_ev_markets(min_ev)
        
        # Filter by sport if specified
        if sport:
            markets = [m for m in markets if m.get('sport') == sport]
        
        # Sort by best EV descending
        markets.sort(key=lambda x: x.get('best_ev_pct', 0), reverse=True)
        
        return {
            "status": "success",
            "count": len(markets),
            "markets": markets
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get positive EV markets: {str(e)}")


@app.get("/api/markets/unmatched")
async def get_unmatched_markets():
    """Get markets that haven't been matched yet."""
    try:
        unmatched = db.get_unmatched_markets()
        
        return {
            "status": "success",
            "pinnacle": unmatched["pinnacle"],
            "cs500": unmatched["cs500"],
            "pinnacle_count": unmatched["pinnacle_count"],
            "cs500_count": unmatched["cs500_count"],
            "total_unmatched": unmatched["pinnacle_count"] + unmatched["cs500_count"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get unmatched markets: {str(e)}")


@app.get("/api/stats")
async def get_stats():
    """Get statistics about the current data."""
    try:
        pinnacle_markets = db.get_active_pinnacle_markets()
        cs500_markets = db.get_active_cs500_markets()
        matched_markets = db.get_matched_markets()
        positive_ev_markets = db.get_positive_ev_markets()
        unmatched = db.get_unmatched_markets()
        
        return {
            "pinnacle_count": len(pinnacle_markets),
            "cs500_count": len(cs500_markets),
            "matched_count": len(matched_markets),
            "positive_ev_count": len(positive_ev_markets),
            "unmatched_pinnacle_count": unmatched["pinnacle_count"],
            "unmatched_cs500_count": unmatched["cs500_count"],
            "sports": {
                "cs2": len([m for m in matched_markets if m.get('sport') == 'cs2']),
                "lol": len([m for m in matched_markets if m.get('sport') == 'lol'])
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@app.post("/api/scrape/all")
async def scrape_all():
    """Scrape both Pinnacle and CS500, then match markets."""
    results = {}
    
    # Scrape Pinnacle
    try:
        pinnacle_result = await scrape_pinnacle(BackgroundTasks())
        results['pinnacle'] = pinnacle_result
    except Exception as e:
        results['pinnacle'] = {"status": "error", "message": str(e)}
    
    # Scrape CS500
    try:
        cs500_result = await scrape_cs500(BackgroundTasks())
        results['cs500'] = cs500_result
    except Exception as e:
        results['cs500'] = {"status": "error", "message": str(e)}
    
    # Match markets
    try:
        match_result = await match_markets()
        results['matching'] = match_result
    except Exception as e:
        results['matching'] = {"status": "error", "message": str(e)}
    
    return {
        "status": "success",
        "message": "Completed full scrape and match cycle",
        "results": results
    }


@app.delete("/api/data")
async def clear_data():
    """Clear all data from the database."""
    try:
        db.clear_all_data()
        return {
            "status": "success",
            "message": "All data cleared successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear data: {str(e)}")


@app.post("/api/rematch")
async def rematch_markets():
    """Clear existing mappings and re-run matching with improved algorithm."""
    try:
        # Clear existing mappings
        db.clear_match_mappings()
        
        # Re-run matching
        pinnacle_markets = db.get_active_pinnacle_markets()
        cs500_markets = db.get_active_cs500_markets()
        
        matched_count = 0
        
        for p_market in pinnacle_markets:
            p_game = {
                "home_team": p_market["home_team"],
                "away_team": p_market["away_team"],
                "event": p_market["event"],
                "start_time": p_market.get("start_time")
            }
            
            cs500_games = []
            for c_market in cs500_markets:
                cs500_games.append({
                    "home_team": c_market["home_team"],
                    "away_team": c_market["away_team"],
                    "event_name": c_market["event_name"],
                    "start_time": c_market.get("start_time"),
                    "match_id": c_market["match_id"]
                })
            
            best_match, confidence = find_best_match(p_game, cs500_games)
            
            if best_match and confidence > 0.6:
                db.store_match_mapping(
                    p_market["id"],
                    best_match["match_id"],
                    confidence
                )
                matched_count += 1
        
        return {
            "status": "success",
            "message": f"Re-matched markets with improved algorithm",
            "matched_count": matched_count,
            "total_pinnacle": len(pinnacle_markets),
            "total_cs500": len(cs500_markets)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rematch markets: {str(e)}")


# Scheduler Control Endpoints

@app.post("/api/scheduler/start")
async def start_scheduler(interval_minutes: int = 5):
    """Start automatic scraping on a schedule."""
    try:
        # Remove existing jobs if any
        for job in scheduler.get_jobs():
            job.remove()
        
        # Add new job with specified interval
        scheduler.add_job(
            scheduled_scrape_all,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id='auto_scrape',
            replace_existing=True
        )
        
        scheduler_config["enabled"] = True
        scheduler_config["pinnacle_interval"] = interval_minutes
        scheduler_config["cs500_interval"] = interval_minutes
        
        logger.info(f"📅 Auto-scraping started: every {interval_minutes} minutes")
        
        return {
            "status": "success",
            "message": f"Auto-scraping started (every {interval_minutes} minutes)",
            "interval_minutes": interval_minutes,
            "enabled": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start scheduler: {str(e)}")


@app.post("/api/scheduler/stop")
async def stop_scheduler():
    """Stop automatic scraping."""
    try:
        # Remove all jobs
        for job in scheduler.get_jobs():
            job.remove()
        
        scheduler_config["enabled"] = False
        
        logger.info("📅 Auto-scraping stopped")
        
        return {
            "status": "success",
            "message": "Auto-scraping stopped",
            "enabled": False
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop scheduler: {str(e)}")


@app.get("/api/scheduler/status")
async def get_scheduler_status():
    """Get current scheduler status."""
    try:
        jobs = scheduler.get_jobs()
        next_run = None
        
        if jobs:
            next_run_time = jobs[0].next_run_time
            if next_run_time:
                next_run = next_run_time.isoformat()
        
        return {
            "enabled": scheduler_config["enabled"],
            "interval_minutes": scheduler_config["pinnacle_interval"],
            "last_pinnacle_scrape": scheduler_config["last_pinnacle_scrape"],
            "last_cs500_scrape": scheduler_config["last_cs500_scrape"],
            "last_match": scheduler_config["last_match"],
            "next_run": next_run,
            "jobs_count": len(jobs)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scheduler status: {str(e)}")


@app.post("/api/scheduler/update")
async def update_scheduler_interval(interval_minutes: int):
    """Update the scheduler interval."""
    try:
        if scheduler_config["enabled"]:
            # Restart with new interval
            await stop_scheduler()
            await start_scheduler(interval_minutes)
            message = f"Scheduler updated to {interval_minutes} minutes"
        else:
            # Just update config
            scheduler_config["pinnacle_interval"] = interval_minutes
            scheduler_config["cs500_interval"] = interval_minutes
            message = f"Interval updated to {interval_minutes} minutes (scheduler not running)"
        
        return {
            "status": "success",
            "message": message,
            "interval_minutes": interval_minutes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update scheduler: {str(e)}")


# Bet Tracking Endpoints

class BetRequest(BaseModel):
    pinnacle_id: str
    event: str
    sport: Optional[str] = None
    home_team: str
    away_team: str
    bet_side: str  # 'home' or 'away'
    bet_team: str
    odds: float
    stake: float
    expected_value: float
    ev_percentage: float
    fair_odds: float
    potential_return: float
    potential_profit: float
    start_time: Optional[str] = None
    notes: Optional[str] = None


class BetUpdateRequest(BaseModel):
    result: str  # 'win', 'loss', or 'void'
    actual_return: float


@app.post("/api/bets")
async def place_bet(bet: BetRequest):
    """Place a new bet."""
    try:
        bet_id = db.place_bet(bet.model_dump())
        return {
            "status": "success",
            "message": "Bet placed successfully",
            "bet_id": bet_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to place bet: {str(e)}")


@app.get("/api/bets")
async def get_bets():
    """Get all bets."""
    try:
        bets = db.get_all_bets()
        return {
            "status": "success",
            "count": len(bets),
            "bets": bets
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get bets: {str(e)}")


@app.get("/api/bets/{bet_id}")
async def get_bet(bet_id: int):
    """Get a specific bet by ID."""
    try:
        bet = db.get_bet_by_id(bet_id)
        if not bet:
            raise HTTPException(status_code=404, detail="Bet not found")
        return {
            "status": "success",
            "bet": bet
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get bet: {str(e)}")


@app.put("/api/bets/{bet_id}")
async def update_bet(bet_id: int, update: BetUpdateRequest):
    """Update a bet result."""
    try:
        bet = db.get_bet_by_id(bet_id)
        if not bet:
            raise HTTPException(status_code=404, detail="Bet not found")
        
        db.update_bet_result(bet_id, update.result, update.actual_return)
        return {
            "status": "success",
            "message": "Bet updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update bet: {str(e)}")


@app.get("/api/bets/stats/summary")
async def get_bet_stats():
    """Get bet statistics."""
    try:
        stats = db.get_bet_stats()
        return {
            "status": "success",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get bet stats: {str(e)}")


@app.get("/api/match/{pinnacle_id}")
async def get_match_details(pinnacle_id: str):
    """Get detailed information about a specific match."""
    try:
        match_details = db.get_match_details(pinnacle_id)
        if not match_details:
            raise HTTPException(status_code=404, detail="Match not found")
        return {
            "status": "success",
            "match": match_details
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get match details: {str(e)}")


@app.post("/api/closing_lines/capture")
async def capture_closing_lines():
    """Manually trigger capturing of closing lines for markets near start time."""
    try:
        count = db.capture_closing_lines()
        return {
            "status": "success",
            "message": f"Captured closing lines for {count} markets",
            "markets_updated": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to capture closing lines: {str(e)}")


@app.post("/api/clv/update")
async def update_clv():
    """Update CLV for all bets that have closing lines available."""
    try:
        count = db.update_all_pending_clv()
        return {
            "status": "success",
            "message": f"Updated CLV for {count} bets",
            "bets_updated": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update CLV: {str(e)}")


@app.post("/api/clv/update/{bet_id}")
async def update_bet_clv_endpoint(bet_id: int):
    """Update CLV for a specific bet."""
    try:
        success = db.update_bet_clv(bet_id)
        if not success:
            return {
                "status": "warning",
                "message": "Closing line not available yet for this bet",
                "updated": False
            }
        return {
            "status": "success",
            "message": f"CLV updated for bet {bet_id}",
            "updated": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update bet CLV: {str(e)}")


@app.get("/api/archive/matches")
async def get_archived_matches(sport: Optional[str] = None, limit: Optional[int] = None):
    """Get all archived matches (past their start time) with closing line data."""
    try:
        matches = db.get_archived_matches(sport, limit)
        return {
            "status": "success",
            "count": len(matches),
            "matches": matches
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get archived matches: {str(e)}")


@app.get("/api/archive/matches/{pinnacle_id}")
async def get_archived_match_details_endpoint(pinnacle_id: str):
    """Get detailed information about a specific archived match."""
    try:
        match_details = db.get_archived_match_details(pinnacle_id)
        if not match_details:
            raise HTTPException(status_code=404, detail="Archived match not found")
        return {
            "status": "success",
            "match": match_details
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get archived match details: {str(e)}")


@app.get("/api/archive/stats")
async def get_archive_stats_endpoint():
    """Get statistics about the archive."""
    try:
        stats = db.get_archive_stats()
        return {
            "status": "success",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get archive stats: {str(e)}")


@app.delete("/api/archive/clear")
async def clear_archive():
    """Clear all archived matches."""
    try:
        count = db.clear_archived_matches()
        return {
            "status": "success",
            "message": f"Cleared {count} archived matches",
            "deleted_count": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear archive: {str(e)}")


@app.post("/api/archive/cleanup")
async def cleanup_matches_without_ev():
    """Manually trigger cleanup of started matches without EV data."""
    try:
        count = db.delete_started_matches_without_ev()
        return {
            "status": "success",
            "message": f"Deleted {count} matches without EV data",
            "deleted_count": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup matches: {str(e)}")


# Mount static files directory (will serve HTML/CSS/JS)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
