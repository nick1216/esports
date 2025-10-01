import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager


class Database:
    """Database manager for esports betting data."""
    
    def __init__(self, db_path: str = "esports_betting.db"):
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
                    start_time TEXT,
                    placed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    result TEXT,
                    actual_return REAL,
                    notes TEXT,
                    FOREIGN KEY (pinnacle_id) REFERENCES pinnacle_markets(id)
                )
            """)
            
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
                    (id, event, sport, home_team, away_team, home_fair_odds, away_fair_odds, home_mult_odds, away_mult_odds, start_time, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
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
            
            return {
                "total_bets": total_bets,
                "total_staked": round(total_staked, 2),
                "total_potential": round(total_potential, 2),
                "settled_bets": settled_bets,
                "pending_bets": total_bets - settled_bets,
                "total_profit": round(won_return - won_stake, 2) if won_return else 0,
                "avg_ev": round(avg_ev, 2)
            }
