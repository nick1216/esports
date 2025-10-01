import re
from typing import Dict, Any, Optional

def _norm_team(name: str) -> str:
    if not name:
        return ""
    s = name.lower()
    s = re.sub(r'[^a-z0-9]+', ' ', s).strip()
    return s

def _moneyline_from_cs500(item: Dict[str, Any]) -> Optional[Dict[str, float]]:
    if not item or "markets" not in item:
        return None
    for m in item["markets"]:
        if m.get("name") == "moneyline":
            try:
                return {
                    "home": float(m["home odds"]),
                    "away": float(m["away odds"]),
                }
            except Exception:
                return None
    return None

# --- Team-only matching helpers ---

# Map normalized aliases to a canonical normalized name.
# Extend as you discover naming differences between books.
TEAM_ALIASES: Dict[str, str] = {
    # examples (normalized -> canonical). Extend as needed.
    # CS2 common
    "g2 esports": "g2",
    "team vitality": "vitality",
    "faze clan": "faze",
    "team spirit": "spirit",
    "ninjas in pyjamas": "nip",
    "natus vincere": "navi",
    "na vi": "navi",
    "virtus pro": "vp",
    "mouz": "mouz",
    "astralis": "astralis",
    "complexity": "complexity",
    "og": "og",
    "fnatic": "fnatic",
    "ence": "ence",
    "big": "big",
    "mibr": "mibr",
    "9z team": "9z",
    "9z": "9z",
    "gamerlegion": "gamerlegion",
    "cloud9": "c9",
    "cloud 9": "c9",
    "team liquid": "liquid",
    "evil geniuses": "eg",
    "pain gaming": "pain",
    "virtuoso pro": "vp", 
    "furia esports": "furia", # occasional typo handling

    # LoL LCK
    "t1 esports": "t1",
    "t1": "t1",
    "gen g": "gen g",
    "gen g esports": "gen g",
    "kt rolster": "kt",
    "dplus kia": "dk",
    "damwon gaming": "dk",
    "hanwha life esports": "hle",
    "drx": "drx",
    "kwangdong freecs": "kdf",
    "fredit brion": "brion",
    "brion": "brion",
    "nongshim redforce": "ns",
    "liiv sandbox": "lsb",
    "sandbox gaming": "lsb",

    # LoL LPL
    "jd gaming": "jdg",
    "jingdong gaming": "jdg",
    "jdg": "jdg",
    "top esports": "tes",
    "funplus phoenix": "fpx",
    "bilibili gaming": "blg",
    "weibo gaming": "weibo",
    "edward gaming": "edg",
    "invictus gaming": "ig",
    "lgd gaming": "lgd",
    "oh my god": "omg",
    "royal never give up": "rng",
    "team we": "we",
    "victory five": "v5",
    "thunder talk gaming": "tt",
    "ultra prime": "up",
    "rare atom": "ra",
    "anyones legend": "al",

    # LoL LCS/LEC
    "100 thieves": "100t",
    "golden guardians": "gg",
    "team solo mid": "tsm",
    "immortals": "imt",
    "counter logic gaming": "clg",
    "mad lions": "mad",
    "sk gaming": "sk",
    "team bds": "bds",
    "koi": "koi",
}

def canonical_team(name: str) -> str:
    """Normalize and map a team name to a canonical token using TEAM_ALIASES."""
    norm = _norm_team(name)
    return TEAM_ALIASES.get(norm, norm)

def infer_sport_from_pinnacle_event(event_name: str) -> Optional[str]:
    """Infer sport code ('lol' or 'cs2') from Pinnacle league/event name."""
    if not event_name:
        return None
    s = event_name.lower()
    if "league of legends" in s or "lol" in s:
        return "lol"
    if "cs2" in s or "counter-strike" in s or "counter strike" in s:
        return "cs2"
    return None

def infer_sport_from_cs500_event(event_name: str) -> Optional[str]:
    """Infer sport code ('lol' or 'cs2') from CS500 event name."""
    if not event_name:
        return None
    s = event_name.lower()
    if "league of legends" in s or "lol" in s:
        return "lol"
    if "cs2" in s or "counter-strike" in s or "counter strike" in s:
        return "cs2"
    return None

# --- AI-powered matching ---
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    from datetime import datetime
    
    # Load model (cached after first use)
    _model = None
    def get_model():
        global _model
        if _model is None:
            _model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        return _model
    
    def team_similarity(team1: str, team2: str) -> float:
        """Get semantic similarity between team names using embeddings."""
        if not team1 or not team2:
            return 0.0
        
        model = get_model()
        embeddings = model.encode([team1, team2])
        similarity = np.dot(embeddings[0], embeddings[1]) / (
            np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
        )
        return float(similarity)
    
    def ai_match_score(pinnacle_game: dict, cs500_game: dict) -> float:
        """AI-powered match confidence score."""
        
        # Team name similarities
        home_sim = team_similarity(
            pinnacle_game.get("home_team", ""), 
            cs500_game.get("home_team", "")
        )
        away_sim = team_similarity(
            pinnacle_game.get("away_team", ""), 
            cs500_game.get("away_team", "")
        )
        
        # Time proximity (if available)
        time_score = 0.0
        if "start_time" in pinnacle_game and "start_time" in cs500_game:
            try:
                p_time = datetime.fromisoformat(pinnacle_game["start_time"].replace('Z', '+00:00'))
                c_time = datetime.fromisoformat(cs500_game["start_time"].replace('Z', '+00:00'))
                time_diff = abs((p_time - c_time).total_seconds())
                
                if time_diff < 3600:  # Within 1 hour
                    time_score = 0.2
                elif time_diff < 7200:  # Within 2 hours
                    time_score = 0.1
            except:
                pass
        
        # Sport consistency
        sport_score = 0.0
        p_sport = infer_sport_from_pinnacle_event(pinnacle_game.get("event", ""))
        c_sport = infer_sport_from_cs500_event(cs500_game.get("event_name", ""))
        if p_sport == c_sport:
            sport_score = 0.1
        
        # Combined score
        team_score = (home_sim + away_sim) / 2
        total_score = team_score + time_score + sport_score
        
        return min(1.0, total_score)
    
    def find_best_match(pinnacle_game: dict, cs500_games: list) -> tuple[Optional[dict], float]:
        """Find the best CS500 match for a Pinnacle game using AI."""
        
        best_match = None
        best_score = 0.0
        
        for cs500_game in cs500_games:
            score = ai_match_score(pinnacle_game, cs500_game)
            
            if score > best_score and score > 0.6:  # Threshold for "good enough"
                best_match = cs500_game
                best_score = score
        
        return best_match, best_score

except ImportError:
    # Fallback if sentence-transformers not installed
    from difflib import SequenceMatcher
    
    def team_similarity(team1: str, team2: str) -> float:
        """Fallback: simple string similarity."""
        return SequenceMatcher(None, team1.lower(), team2.lower()).ratio()
    
    def ai_match_score(pinnacle_game: dict, cs500_game: dict) -> float:
        """Fallback: basic matching."""
        home_sim = team_similarity(
            pinnacle_game.get("home_team", ""), 
            cs500_game.get("home_team", "")
        )
        away_sim = team_similarity(
            pinnacle_game.get("away_team", ""), 
            cs500_game.get("away_team", "")
        )
        return (home_sim + away_sim) / 2
    
    def find_best_match(pinnacle_game: dict, cs500_games: list) -> tuple[Optional[dict], float]:
        """Fallback: find best match using basic similarity."""
        best_match = None
        best_score = 0.0
        
        for cs500_game in cs500_games:
            score = ai_match_score(pinnacle_game, cs500_game)
            if score > best_score and score > 0.7:
                best_match = cs500_game
                best_score = score
        
        return best_match, best_score