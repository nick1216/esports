import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager


class Database:
    """Database manager for esports betting data."""
    
    def __init__(self, db_path: str = None):
        # Use environment variable for Railway, default for local
        import os
        if db_path is None:
            db_path = os.getenv("DATABASE_PATH", "esports_betting.db")
        self.db_path = db_path
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Pinnacle markets table (sharp odds with de-vigged fair odds)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pinnacle_markets (
                    id TEXT PRIMARY KEY,
                    event TEXT NOT NULL,
                    sport TEXT,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    home_fair_odds REAL NOT NULL,
                    away_fair_odds REAL NOT NULL,
                    home_mult_odds REAL,
                    away_mult_odds REAL,
                    home_fair_prob REAL,
                    away_fair_prob REAL,
                    home_mult_prob REAL,
                    away_mult_prob REAL,
                    home_closing_odds REAL,
                    away_closing_odds REAL,
                    closing_captured_at TIMESTAMP,
                    start_time TEXT,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                )
            """)
            
            # Add mult odds columns if they don't exist (for existing databases)
            try:
                cursor.execute("ALTER TABLE pinnacle_markets ADD COLUMN home_mult_odds REAL")
            except:
                pass  # Column already exists
            try:
                cursor.execute("ALTER TABLE pinnacle_markets ADD COLUMN away_mult_odds REAL")
            except:
                pass  # Column already exists
            
            # Add closing line columns if they don't exist
            try:
                cursor.execute("ALTER TABLE pinnacle_markets ADD COLUMN home_closing_odds REAL")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE pinnacle_markets ADD COLUMN away_closing_odds REAL")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE pinnacle_markets ADD COLUMN closing_captured_at TIMESTAMP")
            except:
                pass
            
            # Add probability columns if they don't exist (for existing databases)
            try:
                cursor.execute("ALTER TABLE pinnacle_markets ADD COLUMN home_fair_prob REAL")
            except:
                pass  # Column already exists
            try:
                cursor.execute("ALTER TABLE pinnacle_markets ADD COLUMN away_fair_prob REAL")
            except:
                pass  # Column already exists
            try:
                cursor.execute("ALTER TABLE pinnacle_markets ADD COLUMN home_mult_prob REAL")
            except:
                pass  # Column already exists
            try:
                cursor.execute("ALTER TABLE pinnacle_markets ADD COLUMN away_mult_prob REAL")
            except:
                pass  # Column already exists
            
            # CS500 markets table (soft book odds)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cs500_markets (
                    match_id TEXT PRIMARY KEY,
                    event_name TEXT NOT NULL,
                    sport TEXT,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    home_odds REAL NOT NULL,
                    away_odds REAL NOT NULL,
                    start_time TEXT,
                    status TEXT,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                )
            """)
            
            # Match mappings between Pinnacle and CS500
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS match_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pinnacle_id TEXT NOT NULL,
                    cs500_match_id TEXT NOT NULL,
                    confidence_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (pinnacle_id) REFERENCES pinnacle_markets(id),
                    FOREIGN KEY (cs500_match_id) REFERENCES cs500_markets(match_id),
                    UNIQUE(pinnacle_id, cs500_match_id)
                )
            """)
            
            # CS500 temporary match IDs storage
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cs500_match_ids (
                    match_id TEXT PRIMARY KEY,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Bets tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pinnacle_id TEXT NOT NULL,
                    event TEXT NOT NULL,
                    sport TEXT,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    bet_side TEXT NOT NULL,
                    bet_team TEXT NOT NULL,
                    odds REAL NOT NULL,
                    stake REAL NOT NULL,
                    expected_value REAL NOT NULL,
                    ev_percentage REAL NOT NULL,
                    fair_odds REAL NOT NULL,
                    potential_return REAL NOT NULL,
                    potential_profit REAL NOT NULL,
                    closing_odds REAL,
                    clv REAL,
                    clv_percentage REAL,
                    start_time TEXT,
                    placed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    result TEXT,
                    actual_return REAL,
                    notes TEXT,
                    FOREIGN KEY (pinnacle_id) REFERENCES pinnacle_markets(id)
                )
            """)
            
            # Add CLV columns to bets table if they don't exist
            try:
                cursor.execute("ALTER TABLE bets ADD COLUMN closing_odds REAL")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE bets ADD COLUMN clv REAL")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE bets ADD COLUMN clv_percentage REAL")
            except:
                pass
            
            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_pinnacle_active 
                ON pinnacle_markets(is_active)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_cs500_active 
                ON cs500_markets(is_active)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_mappings_pinnacle 
                ON match_mappings(pinnacle_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_bets_pinnacle 
                ON bets(pinnacle_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_bets_placed_at 
                ON bets(placed_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_pinnacle_start_time
                ON pinnacle_markets(start_time)
            """)
            
            conn.commit()
    
    def store_cs500_match_ids(self, match_ids: List[str]):
        """Store CS500 match IDs."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for match_id in match_ids:
                cursor.execute("""
                    INSERT OR IGNORE INTO cs500_match_ids (match_id)
                    VALUES (?)
                """, (match_id,))
    
    def get_cs500_match_ids(self) -> List[str]:
        """Get all stored CS500 match IDs."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT match_id FROM cs500_match_ids ORDER BY added_at DESC")
            return [row[0] for row in cursor.fetchall()]
    
    def clear_cs500_match_ids(self):
        """Clear all CS500 match IDs."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cs500_match_ids")
    
    def store_pinnacle_markets(self, markets: List[Dict[str, Any]]):
        """Store Pinnacle markets with fair odds."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Mark all existing as inactive first
            cursor.execute("UPDATE pinnacle_markets SET is_active = 0")
            
            for market in markets:
                # Infer sport from event name
                sport = self._infer_sport(market.get('event', ''))
                
                cursor.execute("""
                    INSERT OR REPLACE INTO pinnacle_markets 
                    (id, event, sport, home_team, away_team, home_fair_odds, away_fair_odds, home_mult_odds, away_mult_odds, 
                     home_fair_prob, away_fair_prob, home_mult_prob, away_mult_prob, start_time, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """, (
                    market['id'],
                    market['event'],
                    sport,
                    market['home_team'],
                    market['away_team'],
                    market['home_fair_odds'],
                    market['away_fair_odds'],
                    market.get('home_mult_odds'),
                    market.get('away_mult_odds'),
                    market.get('home_fair_prob'),
                    market.get('away_fair_prob'),
                    market.get('home_mult_prob'),
                    market.get('away_mult_prob'),
                    market.get('start_time')
                ))
    
    def store_cs500_markets(self, markets: List[Dict[str, Any]]):
        """Store CS500 markets."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Mark all existing as inactive first
            cursor.execute("UPDATE cs500_markets SET is_active = 0")
            
            for market in markets:
                # Extract moneyline odds
                moneyline = None
                for m in market.get('markets', []):
                    if m.get('name') == 'moneyline':
                        moneyline = m
                        break
                
                if not moneyline:
                    continue
                
                # Infer sport from event name
                sport = self._infer_sport(market.get('event_name', ''))
                
                cursor.execute("""
                    INSERT OR REPLACE INTO cs500_markets 
                    (match_id, event_name, sport, home_team, away_team, home_odds, away_odds, start_time, status, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """, (
                    market['match_id'],
                    market['event_name'],
                    sport,
                    market['home_team'],
                    market['away_team'],
                    moneyline['home odds'],
                    moneyline['away odds'],
                    market.get('start_time'),
                    market.get('status')
                ))
    
    def _infer_sport(self, event_name: str) -> Optional[str]:
        """Infer sport from event name."""
        if not event_name:
            return None
        s = event_name.lower()
        if "league of legends" in s or "lol" in s:
            return "lol"
        if "cs2" in s or "counter-strike" in s or "counter strike" in s:
            return "cs2"
        return None
    
    def store_match_mapping(self, pinnacle_id: str, cs500_match_id: str, confidence_score: float):
        """Store a match mapping between Pinnacle and CS500."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO match_mappings (pinnacle_id, cs500_match_id, confidence_score)
                VALUES (?, ?, ?)
            """, (pinnacle_id, cs500_match_id, confidence_score))
    
    def get_active_pinnacle_markets(self) -> List[Dict[str, Any]]:
        """Get all active Pinnacle markets."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM pinnacle_markets WHERE is_active = 1
                ORDER BY start_time
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_active_cs500_markets(self) -> List[Dict[str, Any]]:
        """Get all active CS500 markets."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM cs500_markets WHERE is_active = 1
                ORDER BY start_time
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_matched_markets(self) -> List[Dict[str, Any]]:
        """Get markets with matches between Pinnacle and CS500, calculating EV."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    p.id as pinnacle_id,
                    p.event,
                    p.sport,
                    p.home_team as pinnacle_home,
                    p.away_team as pinnacle_away,
                    p.home_fair_odds as home_fair,
                    p.away_fair_odds as away_fair,
                    p.home_mult_odds as home_mult,
                    p.away_mult_odds as away_mult,
                    p.start_time,
                    c.match_id as cs500_id,
                    c.home_team as cs500_home,
                    c.away_team as cs500_away,
                    c.home_odds as cs500_home_odds,
                    c.away_odds as cs500_away_odds,
                    m.confidence_score
                FROM match_mappings m
                JOIN pinnacle_markets p ON m.pinnacle_id = p.id
                JOIN cs500_markets c ON m.cs500_match_id = c.match_id
                WHERE p.is_active = 1 AND c.is_active = 1
                ORDER BY p.start_time
            """)
            
            results = []
            for row in cursor.fetchall():
                data = dict(row)
                
                # Calculate EV using Power method (default)
                home_fair_prob = 1 / data['home_fair']
                away_fair_prob = 1 / data['away_fair']
                
                home_ev = (home_fair_prob * data['cs500_home_odds']) - 1
                away_ev = (away_fair_prob * data['cs500_away_odds']) - 1
                
                home_ev_pct = home_ev * 100
                away_ev_pct = away_ev * 100
                
                data['home_ev'] = round(home_ev, 4)
                data['away_ev'] = round(away_ev, 4)
                data['home_ev_pct'] = round(home_ev_pct, 2)
                data['away_ev_pct'] = round(away_ev_pct, 2)
                
                # Calculate EV using Multiplicative method
                if data.get('home_mult') and data.get('away_mult'):
                    home_mult_prob = 1 / data['home_mult']
                    away_mult_prob = 1 / data['away_mult']
                    
                    home_mult_ev = (home_mult_prob * data['cs500_home_odds']) - 1
                    away_mult_ev = (away_mult_prob * data['cs500_away_odds']) - 1
                    
                    home_mult_ev_pct = home_mult_ev * 100
                    away_mult_ev_pct = away_mult_ev * 100
                    
                    data['home_mult_ev'] = round(home_mult_ev, 4)
                    data['away_mult_ev'] = round(away_mult_ev, 4)
                    data['home_mult_ev_pct'] = round(home_mult_ev_pct, 2)
                    data['away_mult_ev_pct'] = round(away_mult_ev_pct, 2)
                else:
                    # Fallback if mult odds not available
                    data['home_mult_ev'] = data['home_ev']
                    data['away_mult_ev'] = data['away_ev']
                    data['home_mult_ev_pct'] = data['home_ev_pct']
                    data['away_mult_ev_pct'] = data['away_ev_pct']
                
                # Determine best bet (using power method by default)
                if home_ev_pct > 0 or away_ev_pct > 0:
                    if home_ev_pct > away_ev_pct:
                        data['best_bet'] = 'home'
                        data['best_ev_pct'] = home_ev_pct
                    else:
                        data['best_bet'] = 'away'
                        data['best_ev_pct'] = away_ev_pct
                else:
                    data['best_bet'] = None
                    data['best_ev_pct'] = max(home_ev_pct, away_ev_pct)
                
                results.append(data)
            
            return results
    
    def get_positive_ev_markets(self, min_ev: float = 0.0) -> List[Dict[str, Any]]:
        """Get only markets with positive EV."""
        all_markets = self.get_matched_markets()
        return [m for m in all_markets if m['home_ev_pct'] > min_ev or m['away_ev_pct'] > min_ev]
    
    def get_mapped_pinnacle_ids(self) -> set:
        """Get set of all Pinnacle IDs that already have mappings."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT pinnacle_id FROM match_mappings")
            return {row[0] for row in cursor.fetchall()}
    
    def has_mapping(self, pinnacle_id: str) -> bool:
        """Check if a Pinnacle market already has a mapping."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM match_mappings WHERE pinnacle_id = ?",
                (pinnacle_id,)
            )
            count = cursor.fetchone()[0]
            return count > 0
    
    def get_unmatched_markets(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get markets that haven't been matched yet."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get unmatched Pinnacle markets
            cursor.execute("""
                SELECT p.* 
                FROM pinnacle_markets p
                LEFT JOIN match_mappings m ON p.id = m.pinnacle_id
                WHERE p.is_active = 1 AND m.pinnacle_id IS NULL
                ORDER BY p.start_time
            """)
            unmatched_pinnacle = [dict(row) for row in cursor.fetchall()]
            
            # Get unmatched CS500 markets
            cursor.execute("""
                SELECT c.* 
                FROM cs500_markets c
                LEFT JOIN match_mappings m ON c.match_id = m.cs500_match_id
                WHERE c.is_active = 1 AND m.cs500_match_id IS NULL
                ORDER BY c.start_time
            """)
            unmatched_cs500 = [dict(row) for row in cursor.fetchall()]
            
            return {
                "pinnacle": unmatched_pinnacle,
                "cs500": unmatched_cs500,
                "pinnacle_count": len(unmatched_pinnacle),
                "cs500_count": len(unmatched_cs500)
            }
    
    def clear_all_data(self):
        """Clear all data from the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM match_mappings")
            cursor.execute("DELETE FROM pinnacle_markets")
            cursor.execute("DELETE FROM cs500_markets")
            cursor.execute("DELETE FROM cs500_match_ids")
    
    def clear_match_mappings(self):
        """Clear only the match mappings (keeps market data)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM match_mappings")
    
    def clear_archived_matches(self) -> int:
        """Clear all archived matches (past their start time).
        
        Returns the number of matches deleted.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Count matches to be deleted
            cursor.execute("""
                SELECT COUNT(*) FROM pinnacle_markets
                WHERE start_time IS NOT NULL
                AND datetime(start_time) <= datetime('now')
            """)
            count = cursor.fetchone()[0]
            
            # Delete archived pinnacle markets
            cursor.execute("""
                DELETE FROM pinnacle_markets
                WHERE start_time IS NOT NULL
                AND datetime(start_time) <= datetime('now')
            """)
            
            return count
    
    def delete_started_matches_without_ev(self) -> int:
        """Delete matches that have started but don't have EV data (no CS500 match).
        
        This removes matches where:
        - Start time has passed
        - No match mapping exists (no CS500 odds available)
        
        Returns the number of matches deleted.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Find and delete Pinnacle markets that have started but have no CS500 match
            cursor.execute("""
                DELETE FROM pinnacle_markets
                WHERE id IN (
                    SELECT p.id
                    FROM pinnacle_markets p
                    LEFT JOIN match_mappings m ON p.id = m.pinnacle_id
                    WHERE p.start_time IS NOT NULL
                    AND datetime(p.start_time) <= datetime('now')
                    AND m.pinnacle_id IS NULL
                )
            """)
            
            deleted_count = cursor.rowcount
            return deleted_count
    
    def place_bet(self, bet_data: Dict[str, Any]) -> int:
        """Place a bet and store it in the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bets (
                    pinnacle_id, event, sport, home_team, away_team,
                    bet_side, bet_team, odds, stake, expected_value,
                    ev_percentage, fair_odds, potential_return, potential_profit,
                    start_time, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                bet_data['pinnacle_id'],
                bet_data['event'],
                bet_data.get('sport'),
                bet_data['home_team'],
                bet_data['away_team'],
                bet_data['bet_side'],
                bet_data['bet_team'],
                bet_data['odds'],
                bet_data['stake'],
                bet_data['expected_value'],
                bet_data['ev_percentage'],
                bet_data['fair_odds'],
                bet_data['potential_return'],
                bet_data['potential_profit'],
                bet_data.get('start_time'),
                bet_data.get('notes')
            ))
            return cursor.lastrowid
    
    def get_all_bets(self) -> List[Dict[str, Any]]:
        """Get all bets from the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM bets
                ORDER BY placed_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_bet_by_id(self, bet_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific bet by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM bets WHERE id = ?", (bet_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_bet_result(self, bet_id: int, result: str, actual_return: float):
        """Update a bet with its result."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            status = "won" if result == "win" else "lost" if result == "loss" else "void"
            cursor.execute("""
                UPDATE bets
                SET status = ?, result = ?, actual_return = ?
                WHERE id = ?
            """, (status, result, actual_return, bet_id))
    
    def get_bet_stats(self) -> Dict[str, Any]:
        """Get statistics about all bets."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total bets
            cursor.execute("SELECT COUNT(*) FROM bets")
            total_bets = cursor.fetchone()[0]
            
            # Total staked
            cursor.execute("SELECT SUM(stake) FROM bets")
            total_staked = cursor.fetchone()[0] or 0
            
            # Total potential return
            cursor.execute("SELECT SUM(potential_return) FROM bets WHERE status = 'pending'")
            total_potential = cursor.fetchone()[0] or 0
            
            # Settled bets stats
            cursor.execute("SELECT COUNT(*) FROM bets WHERE status IN ('won', 'lost', 'void')")
            settled_bets = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(stake) FROM bets WHERE status = 'won'")
            won_stake = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT SUM(actual_return) FROM bets WHERE status = 'won'")
            won_return = cursor.fetchone()[0] or 0
            
            # Average EV
            cursor.execute("SELECT AVG(ev_percentage) FROM bets")
            avg_ev = cursor.fetchone()[0] or 0
            
            # Total EV in dollars
            cursor.execute("SELECT SUM(expected_value) FROM bets")
            total_ev = cursor.fetchone()[0] or 0
            
            # CLV stats
            cursor.execute("SELECT AVG(clv) FROM bets WHERE clv IS NOT NULL")
            avg_clv = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COUNT(*) FROM bets WHERE clv IS NOT NULL")
            bets_with_clv = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM bets WHERE clv > 0")
            positive_clv_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(stake) FROM bets WHERE clv > 0")
            positive_clv_stake = cursor.fetchone()[0] or 0
            
            return {
                "total_bets": total_bets,
                "total_staked": round(total_staked, 2),
                "total_potential": round(total_potential, 2),
                "settled_bets": settled_bets,
                "pending_bets": total_bets - settled_bets,
                "total_profit": round(won_return - won_stake, 2) if won_return else 0,
                "avg_ev": round(avg_ev, 2),
                "total_ev": round(total_ev, 2),
                "avg_clv": round(avg_clv, 4),
                "bets_with_clv": bets_with_clv,
                "positive_clv_count": positive_clv_count,
                "positive_clv_rate": round((positive_clv_count / bets_with_clv * 100), 2) if bets_with_clv > 0 else 0,
                "positive_clv_stake": round(positive_clv_stake, 2)
            }
    
    def capture_closing_lines(self) -> int:
        """Capture closing lines for markets that have started or are about to start.
        
        This should be called regularly (e.g., every minute) to capture the last available odds
        before match starts as the closing line.
        
        Returns the number of markets where closing lines were captured.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get markets that are starting within the next 5 minutes and don't have closing odds yet
            cursor.execute("""
                SELECT id, home_fair_odds, away_fair_odds, home_mult_odds, away_mult_odds, start_time
                FROM pinnacle_markets
                WHERE is_active = 1
                AND start_time IS NOT NULL
                AND home_closing_odds IS NULL
                AND away_closing_odds IS NULL
                AND datetime(start_time) <= datetime('now', '+5 minutes')
            """)
            
            markets_to_update = cursor.fetchall()
            count = 0
            
            for market in markets_to_update:
                market_id = market[0]
                home_fair = market[1]
                away_fair = market[2]
                
                # Use multiplicative odds if available, otherwise fair odds
                home_closing = market[3] if market[3] else home_fair
                away_closing = market[4] if market[4] else away_fair
                
                cursor.execute("""
                    UPDATE pinnacle_markets
                    SET home_closing_odds = ?,
                        away_closing_odds = ?,
                        closing_captured_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (home_closing, away_closing, market_id))
                
                count += 1
            
            return count
    
    def update_bet_clv(self, bet_id: int) -> bool:
        """Calculate and update CLV for a specific bet using the closing line.
        
        CLV (Closing Line Value) = (Your Odds - Closing Odds) / Closing Odds * 100
        Or in probability terms: (Closing Prob - Your Prob) * 100
        
        Returns True if CLV was calculated, False if closing line not available yet.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get bet details
            cursor.execute("""
                SELECT b.pinnacle_id, b.bet_side, b.odds,
                       p.home_closing_odds, p.away_closing_odds
                FROM bets b
                JOIN pinnacle_markets p ON b.pinnacle_id = p.id
                WHERE b.id = ?
            """, (bet_id,))
            
            bet_data = cursor.fetchone()
            if not bet_data:
                return False
            
            _, bet_side, bet_odds, home_closing, away_closing = bet_data
            
            # Check if closing line is available
            closing_odds = home_closing if bet_side == 'home' else away_closing
            if not closing_odds:
                return False
            
            # Calculate CLV
            # Method 1: Odds difference percentage
            clv_pct = ((bet_odds - closing_odds) / closing_odds) * 100
            
            # Method 2: Implied probability difference (this is more accurate for betting)
            # Positive CLV means you got better odds than closing (better value)
            bet_prob = 1 / bet_odds
            closing_prob = 1 / closing_odds
            clv_prob_diff = (closing_prob - bet_prob) * 100  # In percentage points
            
            # Update bet with CLV
            cursor.execute("""
                UPDATE bets
                SET closing_odds = ?,
                    clv = ?,
                    clv_percentage = ?
                WHERE id = ?
            """, (closing_odds, clv_prob_diff, clv_pct, bet_id))
            
            return True
    
    def update_all_pending_clv(self) -> int:
        """Update CLV for all pending bets that don't have CLV calculated yet.
        
        Returns the number of bets updated.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get all bets without CLV that have closing lines available
            cursor.execute("""
                SELECT b.id
                FROM bets b
                JOIN pinnacle_markets p ON b.pinnacle_id = p.id
                WHERE b.closing_odds IS NULL
                AND ((b.bet_side = 'home' AND p.home_closing_odds IS NOT NULL)
                     OR (b.bet_side = 'away' AND p.away_closing_odds IS NOT NULL))
            """)
            
            bet_ids = [row[0] for row in cursor.fetchall()]
        
        count = 0
        for bet_id in bet_ids:
            if self.update_bet_clv(bet_id):
                count += 1
        
        return count
    
    def get_archived_matches(self, sport: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all matches that have gone live (past their start time) with their closing line data.
        
        Args:
            sport: Optional sport filter ('cs2' or 'lol')
            limit: Optional limit on number of results
            
        Returns:
            List of archived matches with their data including closing lines, bets placed, etc.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    p.id as pinnacle_id,
                    p.event,
                    p.sport,
                    p.home_team,
                    p.away_team,
                    p.home_fair_odds,
                    p.away_fair_odds,
                    p.home_mult_odds,
                    p.away_mult_odds,
                    p.home_closing_odds,
                    p.away_closing_odds,
                    p.start_time,
                    p.closing_captured_at,
                    p.scraped_at,
                    c.match_id as cs500_id,
                    c.home_odds as cs500_home_odds,
                    c.away_odds as cs500_away_odds,
                    m.confidence_score,
                    COUNT(DISTINCT b.id) as bet_count,
                    SUM(CASE WHEN b.status = 'won' THEN 1 ELSE 0 END) as bets_won,
                    SUM(CASE WHEN b.status = 'lost' THEN 1 ELSE 0 END) as bets_lost,
                    SUM(b.stake) as total_staked,
                    AVG(b.clv) as avg_clv
                FROM pinnacle_markets p
                LEFT JOIN match_mappings m ON p.id = m.pinnacle_id
                LEFT JOIN cs500_markets c ON m.cs500_match_id = c.match_id
                LEFT JOIN bets b ON p.id = b.pinnacle_id
                WHERE p.start_time IS NOT NULL
                AND datetime(p.start_time) <= datetime('now')
            """
            
            params = []
            if sport:
                query += " AND p.sport = ?"
                params.append(sport)
            
            query += """
                GROUP BY p.id
                ORDER BY p.start_time DESC
            """
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            results = []
            
            for row in cursor.fetchall():
                data = dict(row)
                
                # Calculate EV for archived matches if we have CS500 data
                if data.get('cs500_home_odds') and data.get('cs500_away_odds'):
                    home_fair_prob = 1 / data['home_fair_odds'] if data['home_fair_odds'] else 0
                    away_fair_prob = 1 / data['away_fair_odds'] if data['away_fair_odds'] else 0
                    
                    home_ev = (home_fair_prob * data['cs500_home_odds']) - 1
                    away_ev = (away_fair_prob * data['cs500_away_odds']) - 1
                    
                    data['home_ev_pct'] = round(home_ev * 100, 2)
                    data['away_ev_pct'] = round(away_ev * 100, 2)
                    data['best_ev_pct'] = max(home_ev * 100, away_ev * 100)
                else:
                    data['home_ev_pct'] = None
                    data['away_ev_pct'] = None
                    data['best_ev_pct'] = None
                
                # Calculate CLV difference (closing vs opening)
                if data.get('home_closing_odds') and data.get('home_fair_odds'):
                    home_clv_move = ((data['home_closing_odds'] - data['home_fair_odds']) / data['home_fair_odds']) * 100
                    data['home_clv_move'] = round(home_clv_move, 2)
                else:
                    data['home_clv_move'] = None
                
                if data.get('away_closing_odds') and data.get('away_fair_odds'):
                    away_clv_move = ((data['away_closing_odds'] - data['away_fair_odds']) / data['away_fair_odds']) * 100
                    data['away_clv_move'] = round(away_clv_move, 2)
                else:
                    data['away_clv_move'] = None
                
                # Format averages
                if data['avg_clv'] is not None:
                    data['avg_clv'] = round(data['avg_clv'], 2)
                
                results.append(data)
            
            return results
    
    def get_archived_match_details(self, pinnacle_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific archived match including all bets placed on it.
        
        Args:
            pinnacle_id: The Pinnacle market ID
            
        Returns:
            Dictionary with match details and list of bets placed on it
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get match details
            cursor.execute("""
                SELECT 
                    p.*,
                    c.match_id as cs500_id,
                    c.home_odds as cs500_home_odds,
                    c.away_odds as cs500_away_odds,
                    c.event_name as cs500_event,
                    m.confidence_score
                FROM pinnacle_markets p
                LEFT JOIN match_mappings m ON p.id = m.pinnacle_id
                LEFT JOIN cs500_markets c ON m.cs500_match_id = c.match_id
                WHERE p.id = ?
                AND p.start_time IS NOT NULL
                AND datetime(p.start_time) <= datetime('now')
            """, (pinnacle_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            match_data = dict(row)
            
            # Get all bets placed on this match
            cursor.execute("""
                SELECT * FROM bets
                WHERE pinnacle_id = ?
                ORDER BY placed_at ASC
            """, (pinnacle_id,))
            
            bets = [dict(bet_row) for bet_row in cursor.fetchall()]
            match_data['bets'] = bets
            
            return match_data
    
    def get_archive_stats(self) -> Dict[str, Any]:
        """Get statistics about archived matches.
        
        Returns:
            Dictionary with archive statistics
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total archived matches
            cursor.execute("""
                SELECT COUNT(*) FROM pinnacle_markets
                WHERE start_time IS NOT NULL
                AND datetime(start_time) <= datetime('now')
            """)
            total_archived = cursor.fetchone()[0]
            
            # Matches with closing lines captured
            cursor.execute("""
                SELECT COUNT(*) FROM pinnacle_markets
                WHERE start_time IS NOT NULL
                AND datetime(start_time) <= datetime('now')
                AND home_closing_odds IS NOT NULL
                AND away_closing_odds IS NOT NULL
            """)
            with_closing_lines = cursor.fetchone()[0]
            
            # Archived matches by sport
            cursor.execute("""
                SELECT sport, COUNT(*) as count
                FROM pinnacle_markets
                WHERE start_time IS NOT NULL
                AND datetime(start_time) <= datetime('now')
                GROUP BY sport
            """)
            by_sport = {row[0] or 'unknown': row[1] for row in cursor.fetchall()}
            
            # Matches with bets
            cursor.execute("""
                SELECT COUNT(DISTINCT p.id)
                FROM pinnacle_markets p
                JOIN bets b ON p.id = b.pinnacle_id
                WHERE p.start_time IS NOT NULL
                AND datetime(p.start_time) <= datetime('now')
            """)
            with_bets = cursor.fetchone()[0]
            
            return {
                "total_archived": total_archived,
                "with_closing_lines": with_closing_lines,
                "closing_line_capture_rate": round((with_closing_lines / total_archived * 100), 2) if total_archived > 0 else 0,
                "by_sport": by_sport,
                "with_bets": with_bets
            }
    
    def get_match_details(self, pinnacle_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific match including all calculations."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    p.id as pinnacle_id,
                    p.event,
                    p.sport,
                    p.home_team as pinnacle_home,
                    p.away_team as pinnacle_away,
                    p.home_fair_odds as home_fair,
                    p.away_fair_odds as away_fair,
                    p.home_mult_odds as home_mult,
                    p.away_mult_odds as away_mult,
                    p.start_time,
                    p.scraped_at as pinnacle_scraped_at,
                    c.match_id as cs500_id,
                    c.home_team as cs500_home,
                    c.away_team as cs500_away,
                    c.home_odds as cs500_home_odds,
                    c.away_odds as cs500_away_odds,
                    c.event_name as cs500_event,
                    c.status as cs500_status,
                    c.scraped_at as cs500_scraped_at,
                    m.confidence_score
                FROM pinnacle_markets p
                LEFT JOIN match_mappings m ON p.id = m.pinnacle_id
                LEFT JOIN cs500_markets c ON m.cs500_match_id = c.match_id
                WHERE p.id = ?
            """, (pinnacle_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            data = dict(row)
            
            # Use stored probabilities if available (they sum to exactly 100%)
            # Otherwise calculate from odds
            if data.get('home_fair_prob') is not None and data.get('away_fair_prob') is not None:
                # Use stored probabilities (already decimal, need to convert to percentage)
                home_fair_prob = data['home_fair_prob']
                away_fair_prob = data['away_fair_prob']
                data['home_fair_prob'] = round(home_fair_prob * 100, 2)
                data['away_fair_prob'] = round(away_fair_prob * 100, 2)
            else:
                # Fallback: calculate from odds (for old data)
                home_fair_prob = 1 / data['home_fair'] if data['home_fair'] else 0
                away_fair_prob = 1 / data['away_fair'] if data['away_fair'] else 0
                data['home_fair_prob'] = round(home_fair_prob * 100, 2)
                data['away_fair_prob'] = round(away_fair_prob * 100, 2)
            
            # Multiplicative method probabilities
            if data.get('home_mult_prob') is not None and data.get('away_mult_prob') is not None:
                # Use stored probabilities
                home_mult_prob = data['home_mult_prob']
                away_mult_prob = data['away_mult_prob']
                data['home_mult_prob'] = round(home_mult_prob * 100, 2)
                data['away_mult_prob'] = round(away_mult_prob * 100, 2)
            elif data.get('home_mult') and data.get('away_mult'):
                # Fallback: calculate from odds
                home_mult_prob = 1 / data['home_mult']
                away_mult_prob = 1 / data['away_mult']
                data['home_mult_prob'] = round(home_mult_prob * 100, 2)
                data['away_mult_prob'] = round(away_mult_prob * 100, 2)
            else:
                data['home_mult_prob'] = data['home_fair_prob']
                data['away_mult_prob'] = data['away_fair_prob']
                home_mult_prob = home_fair_prob
                away_mult_prob = away_fair_prob
            
            # If CS500 data is available, calculate EV
            if data.get('cs500_home_odds') and data.get('cs500_away_odds'):
                # CS500 implied probabilities
                cs500_home_prob = 1 / data['cs500_home_odds']
                cs500_away_prob = 1 / data['cs500_away_odds']
                
                data['cs500_home_prob'] = round(cs500_home_prob * 100, 2)
                data['cs500_away_prob'] = round(cs500_away_prob * 100, 2)
                data['cs500_total_prob'] = round((cs500_home_prob + cs500_away_prob) * 100, 2)
                data['cs500_vig'] = round((cs500_home_prob + cs500_away_prob - 1) * 100, 2)
                
                # Power method EV
                home_ev = (home_fair_prob * data['cs500_home_odds']) - 1
                away_ev = (away_fair_prob * data['cs500_away_odds']) - 1
                
                data['home_ev'] = round(home_ev, 4)
                data['away_ev'] = round(away_ev, 4)
                data['home_ev_pct'] = round(home_ev * 100, 2)
                data['away_ev_pct'] = round(away_ev * 100, 2)
                
                # Multiplicative method EV
                if data.get('home_mult') and data.get('away_mult'):
                    home_mult_ev = (home_mult_prob * data['cs500_home_odds']) - 1
                    away_mult_ev = (away_mult_prob * data['cs500_away_odds']) - 1
                    
                    data['home_mult_ev'] = round(home_mult_ev, 4)
                    data['away_mult_ev'] = round(away_mult_ev, 4)
                    data['home_mult_ev_pct'] = round(home_mult_ev * 100, 2)
                    data['away_mult_ev_pct'] = round(away_mult_ev * 100, 2)
                else:
                    data['home_mult_ev'] = data['home_ev']
                    data['away_mult_ev'] = data['away_ev']
                    data['home_mult_ev_pct'] = data['home_ev_pct']
                    data['away_mult_ev_pct'] = data['away_ev_pct']
                
                # Best bet determination for both methods
                if data['home_ev_pct'] > data['away_ev_pct']:
                    data['best_bet_power'] = 'home'
                    data['best_ev_power'] = data['home_ev_pct']
                else:
                    data['best_bet_power'] = 'away'
                    data['best_ev_power'] = data['away_ev_pct']
                
                if data['home_mult_ev_pct'] > data['away_mult_ev_pct']:
                    data['best_bet_mult'] = 'home'
                    data['best_ev_mult'] = data['home_mult_ev_pct']
                else:
                    data['best_bet_mult'] = 'away'
                    data['best_ev_mult'] = data['away_mult_ev_pct']
            
            return data