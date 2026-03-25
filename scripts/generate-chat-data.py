#!/usr/bin/env python3
"""
Generate comprehensive chat stats data for the D1 basketball outcomes chatbot.
Reads from both the realgm database and the torvik college stats database,
producing a keyword-indexed JSON file for fast chatbot lookups.

Output: website/public/data/chat-stats.json
"""

import sqlite3
import json
import os
import re
from collections import defaultdict, Counter

# ============================================================================
# Config
# ============================================================================
REALGM_DB = "/Users/rjb/Desktop/Hoop Research/d1-basketball-outcomes/data/d1_basketball.db"
TORVIK_DB = "/Users/rjb/Desktop/Hoop Research/d1_basketball.db"
OUTPUT_PATH = "/Users/rjb/Desktop/Hoop Research/d1-basketball-outcomes/website/public/data/chat-stats.json"

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

# ============================================================================
# European keywords (reused from generate-sankey-data.py)
# ============================================================================
EUROPEAN_KEYWORDS = [
    "BC", "KK", "Barca", "Real Madrid", "Zalgiris", "ALBA", "Bayern",
    "Fenerbahce", "Galatasaray", "Olympiacos", "Panathinaikos", "Partizan",
    "CSKA", "Khimki", "Zenit", "Milan", "Bologna", "Cremona", "Varese",
    "Trento", "Sassari", "Trieste", "Leicester", "Sheffield", "Cheshire",
    "London Lions", "Plymouth", "Glasgow", "Caledonia", "MHP Riesen",
    "Towers Hamburg", "Telekom Baskets", "Goettingen", "Bayreuth", "Vechta",
    "Baskets", "Leuven", "Antwerp", "Hapoel", "Maccabi", "Ironi", "Bnei",
    "Nymburk", "Horsens", "FOG", "Naestved", "Lavrio", "Aris", "PAOK",
    "Promitheas", "Kolossos", "Limoges", "Boulogne", "Strasbourg", "Chorale",
    "Nanterre", "Gran Canaria", "Fuenlabrada", "Joventut", "Valencia Basket",
    "Zaragoza", "Badalona", "Turk Telekom", "Besiktas", "Bursaspor", "Banvit",
    "Warszawa", "Wroclaw", "Gdynia", "Bydgoszcz", "Golden Eagle", "Riders",
    "Netherlands", "Germany", "Serbia", "Lithuania", "Spain", "France",
    "Greece", "Great Britain", "Croatia", "Italy", "Turkey", "Israel",
    "Poland", "Czech", "Belgium", "Denmark", "Finland", "Sweden", "Norway",
    "Hungary", "Romania", "Bulgaria", "Slovenia", "Latvia", "Estonia",
    "Montenegro", "Bosnia", "Portugal", "Switzerland", "Austria", "Ukraine",
    "Russia", "Georgia", "Iceland", "Cyprus", "Kosovo", "Albania",
    "North Macedonia", "Slovakia",
    "Ulm", "Bamberg", "Bonn", "Frankfurt", "Berlin", "Wurzburg",
    "Ludwigsburg", "Braunschweig", "Treviso", "Reggio", "Brescia", "Napoli",
    "Pesaro", "Pau", "Roanne", "Dijon", "Nancy", "Orleans",
    "Le Mans", "Gravelines", "Murcia", "Malaga", "Tenerife", "Manresa",
    "Burgos", "Bilbao", "Andorra", "Porto", "Sporting", "Benfica",
    "Oliveirense", "Elan Chalon", "Saint-Quentin", "Fos-sur-Mer", "JDA",
    "Den Bosch", "Leiden", "Groningen", "Donar", "Bakken", "Aarhus",
    "Helsinki", "Korihait", "Kauhajoki", "Svitavy", "Opava", "USK Praha",
    "Cibona", "Cedevita", "Split", "FMP", "Mega", "Buducnost",
    "SC Rasta", "Phoenix Hagen", "Mitteldeutscher", "Fraport", "Skyliners",
    "Artland", "Brose", "EWE", "BBC Bayreuth", "Walter Tigers", "Crailsheim",
    "Giessen", "Gottingen", "Oettinger Rockets", "s.Oliver", "Eisbaren",
    "ratiopharm", "MBC", "Niners", "Hamburg", "Rostock", "Ehingen", "Trier",
    "Jena", "Tubingen", "Legia", "Trefl", "Anwil", "Stelmet", "Czarni",
    "Rosa", "Asseco", "Turów", "Enea", "Spojnia", "Dekorglass", "Lublin",
    "Grodno", "Minsk", "Rilski", "Levski", "Lukoil", "Beroe", "Yambol",
    "Lokomotiv", "Primorska", "Krka", "Rogaska", "Helios", "Olimpija",
    "Sigal", "Rahoveci", "Trepca", "Kalaja", "Peja", "Shkupi", "MZT",
    "Pelister", "Mornar", "Sutjeska", "Igokea", "Borac", "Sloga", "Brno",
    "Decin", "Pardubice", "Prosek", "Prostejov", "Olomouc", "Sluneta",
    "Sokolov", "Kolin", "Hradec", "Chartres", "Fos",
    "Rouen", "Blois", "Vichy", "Poitiers", "Denain", "Aix", "Le Portel",
    "Antibes", "Quimper", "Hyeres", "Challans", "Nantes", "Bourg", "Evreux",
    "Prienai", "Lietkabelis", "Neptunas", "Juventus", "Pieno", "Rytas",
    "Siauliai", "BC Wolves", "Kalev", "Ventspils", "VEF",
    "Ogre", "Tartu", "Rapla", "Parnu", "Valga", "Bisons", "Szolnok",
    "Falco", "Koermend", "Sopron", "Szeged", "Alba Fehervar", "Paks",
    "Debrecen", "Alytus", "Nevezis", "Carolo", "Le Havre", "Saint-Chamond",
    "Aix-Maurienne", "Union Tarbes", "Champagne", "Caen",
]
EUROPEAN_KEYWORDS_LOWER = [kw.lower() for kw in EUROPEAN_KEYWORDS]


def is_european_team(team_name):
    team_lower = team_name.lower()
    for kw in EUROPEAN_KEYWORDS_LOWER:
        if kw in team_lower:
            return True
    return False


def classify_international_player(intl_seasons):
    if not intl_seasons:
        return "other_intl"
    first_intl = intl_seasons[0]
    teams = first_intl.get("teams", [])
    for team in teams:
        if isinstance(team, str) and is_european_team(team):
            return "europe"
    return "other_intl"


def season_sort_key(s):
    return int(s.split("-")[0])


def has_real_nba_season(section_types):
    return "NBA Season Stats" in section_types


def parse_height_inches(ht_str):
    """Parse '6-10' to 82 inches."""
    if not ht_str:
        return None
    m = re.match(r"(\d+)-(\d+)", str(ht_str))
    if m:
        return int(m.group(1)) * 12 + int(m.group(2))
    return None


def inches_to_str(inches):
    """Convert 78 inches to '6-6'."""
    if inches is None:
        return "N/A"
    ft = int(inches) // 12
    inch = round(inches) % 12
    return f"{ft}-{inch}"


def avg(lst):
    return round(sum(lst) / len(lst), 1) if lst else 0


def safe_pct(n, d):
    return round(n / d * 100, 1) if d else 0


# ============================================================================
# Step 1: Load and classify all players from realgm
# ============================================================================
print("Loading realgm data...")
db = sqlite3.connect(REALGM_DB)
db.row_factory = sqlite3.Row

cur = db.cursor()
cur.execute("""
    SELECT t.realgm_id, t.season, t.level, t.section_types, t.stats, t.teams,
           p.name, p.ht, p.school, p.pos, p.class_year
    FROM realgm_timeline t
    JOIN realgm_players p ON t.realgm_id = p.realgm_id
    ORDER BY t.realgm_id, t.season
""")

players = defaultdict(lambda: {"seasons": [], "name": "", "ht": "", "school": "", "pos": "", "class_year": ""})
for row in cur:
    pid = row["realgm_id"]
    players[pid]["name"] = row["name"]
    players[pid]["ht"] = row["ht"]
    players[pid]["school"] = row["school"]
    players[pid]["pos"] = row["pos"]
    players[pid]["class_year"] = row["class_year"] or ""
    section_types = json.loads(row["section_types"]) if row["section_types"] else []
    stats = json.loads(row["stats"]) if row["stats"] else {}
    teams = json.loads(row["teams"]) if row["teams"] else []
    players[pid]["seasons"].append({
        "season": row["season"],
        "level": row["level"],
        "section_types": section_types,
        "stats": stats,
        "teams": teams,
    })

print(f"  Total players loaded: {len(players)}")

# Classify players
MIN_LAST_NCAA = "2014-2015"
MAX_LAST_NCAA = "2024-2025"
STILL_IN_COLLEGE = "2025-2026"

classified = []
for pid, pdata in players.items():
    ncaa_seasons = [s for s in pdata["seasons"] if s["level"] == "ncaa"]
    if not ncaa_seasons:
        continue
    last_ncaa = max(ncaa_seasons, key=lambda s: season_sort_key(s["season"]))
    last_ncaa_season = last_ncaa["season"]
    if last_ncaa_season == STILL_IN_COLLEGE:
        continue
    if season_sort_key(last_ncaa_season) < season_sort_key(MIN_LAST_NCAA):
        continue
    if season_sort_key(last_ncaa_season) > season_sort_key(MAX_LAST_NCAA):
        continue

    last_ncaa_year = season_sort_key(last_ncaa_season)
    post_college = sorted(
        [s for s in pdata["seasons"] if season_sort_key(s["season"]) > last_ncaa_year],
        key=lambda s: season_sort_key(s["season"])
    )
    pro_levels = {"nba", "g_league", "international"}
    pro_seasons = [s for s in post_college if s["level"] in pro_levels]

    def is_real_nba(s):
        return s["level"] == "nba" and has_real_nba_season(s["section_types"])

    first_pro = None
    for s in pro_seasons:
        if s["level"] == "nba":
            if has_real_nba_season(s["section_types"]):
                first_pro = "nba"
                break
            continue
        elif s["level"] == "g_league":
            first_pro = "g_league"
            break
        elif s["level"] == "international":
            first_pro = "international"
            break
    if first_pro is None:
        first_pro = "no_pro"

    last_ncaa_stats = last_ncaa.get("stats", {}).get("NCAA Season Stats", {})

    nba_real_seasons = [s for s in pro_seasons if is_real_nba(s)]
    gleague_seasons = [s for s in pro_seasons if s["level"] == "g_league"]
    intl_seasons = sorted(
        [s for s in pro_seasons if s["level"] == "international"],
        key=lambda s: season_sort_key(s["season"])
    )

    intl_subtype = None
    if first_pro == "international":
        intl_subtype = classify_international_player(intl_seasons)

    # Determine the destination key
    if first_pro == "international":
        dest = intl_subtype
    else:
        dest = first_pro

    total_pro_seasons = len(pro_seasons)

    # Determine all levels reached
    level_set = set()
    for s in pro_seasons:
        if s["level"] == "nba" and has_real_nba_season(s["section_types"]):
            level_set.add("nba")
        elif s["level"] == "g_league":
            level_set.add("g_league")
        elif s["level"] == "international":
            level_set.add("international")

    # Extract all international teams for country analysis
    all_intl_teams = []
    for s in intl_seasons:
        all_intl_teams.extend(s.get("teams", []))

    classified.append({
        "pid": pid,
        "name": pdata["name"],
        "ht": pdata["ht"],
        "school": pdata["school"],
        "pos": pdata["pos"],
        "class_year": pdata["class_year"],
        "last_ncaa_season": last_ncaa_season,
        "last_ncaa_year": last_ncaa_year,
        "last_ncaa_stats": last_ncaa_stats,
        "first_pro": first_pro,
        "dest": dest,  # nba, g_league, europe, other_intl, no_pro
        "pro_seasons": pro_seasons,
        "total_pro_seasons": total_pro_seasons,
        "nba_real_count": len(nba_real_seasons),
        "gleague_count": len(gleague_seasons),
        "intl_count": len(intl_seasons),
        "level_set": level_set,
        "all_intl_teams": all_intl_teams,
        "ncaa_season_count": len(ncaa_seasons),
    })

db.close()

print(f"  Classified players: {len(classified)}")

# ============================================================================
# Step 2: Load torvik college stats
# ============================================================================
print("Loading torvik college stats...")
torvik_db = sqlite3.connect(TORVIK_DB)
torvik_db.row_factory = sqlite3.Row
tcur = torvik_db.cursor()

# Build a name->player_id lookup, then load stints
tcur.execute("SELECT player_id, full_name, height FROM PLAYERS")
torvik_players = {}
torvik_name_lookup = defaultdict(list)
for row in tcur:
    torvik_players[row["player_id"]] = {"name": row["full_name"], "height": row["height"]}
    torvik_name_lookup[row["full_name"].lower()].append(row["player_id"])

# Load all college stints
tcur.execute("""
    SELECT cs.player_id, cs.school, cs.conference, cs.season, cs.class_year,
           cs.ppg, cs.rpg, cs.apg, cs.spg, cs.bpg, cs.min_pct,
           cs.efg_pct, cs.ts_pct, cs.threep_pct, cs.games_played,
           cs.bpm, cs.obpm, cs.dbpm
    FROM COLLEGE_STINTS cs
    ORDER BY cs.player_id, cs.season
""")

torvik_stints = defaultdict(list)
for row in tcur:
    torvik_stints[row["player_id"]].append(dict(row))

torvik_db.close()
print(f"  Torvik players: {len(torvik_players)}, stints: {sum(len(v) for v in torvik_stints.values())}")

# ============================================================================
# Step 3: Link realgm players to torvik data
# ============================================================================
print("Linking realgm to torvik...")
linked_count = 0
for p in classified:
    name_lower = p["name"].lower()
    candidates = torvik_name_lookup.get(name_lower, [])
    if not candidates:
        p["torvik_stints"] = []
        continue
    # If multiple matches, prefer the one at the same school
    best = None
    for pid in candidates:
        stints = torvik_stints.get(pid, [])
        for st in stints:
            if st["school"] and p["school"] and st["school"].lower() in p["school"].lower():
                best = pid
                break
            if st["school"] and p["school"] and p["school"].lower() in st["school"].lower():
                best = pid
                break
        if best:
            break
    if best is None:
        best = candidates[0]
    p["torvik_stints"] = torvik_stints.get(best, [])
    if p["torvik_stints"]:
        linked_count += 1

    # Get final college year stint from torvik
    if p["torvik_stints"]:
        final_stints = [s for s in p["torvik_stints"] if s["season"] == p["last_ncaa_year"] + 1]
        if not final_stints:
            final_stints = [s for s in p["torvik_stints"]]
        if final_stints:
            final = max(final_stints, key=lambda s: s["season"])
            p["torvik_final"] = final
        else:
            p["torvik_final"] = None
    else:
        p["torvik_final"] = None

print(f"  Linked: {linked_count}")

# ============================================================================
# Step 4: Build buckets by destination
# ============================================================================
DEST_LABELS = {
    "nba": "NBA",
    "g_league": "G-League",
    "europe": "Europe",
    "other_intl": "Other International",
    "no_pro": "No Pro Career",
}
DEST_KEYS = ["nba", "g_league", "europe", "other_intl", "no_pro"]

buckets = defaultdict(list)
for p in classified:
    buckets[p["dest"]].append(p)

total = len(classified)
counts = {d: len(buckets[d]) for d in DEST_KEYS}
pcts = {d: safe_pct(counts[d], total) for d in DEST_KEYS}

print(f"\n{'Destination Breakdown':=^60}")
for d in DEST_KEYS:
    print(f"  {DEST_LABELS[d]:25s}: {counts[d]:>6}  ({pcts[d]:.1f}%)")
print(f"  {'TOTAL':25s}: {total:>6}")

# ============================================================================
# Helper: get stat from last NCAA season
# ============================================================================
def get_ncaa_stat(p, key):
    val = p["last_ncaa_stats"].get(key)
    if val is not None:
        try:
            return float(val)
        except (TypeError, ValueError):
            return None
    return None


def dest_avg_stat(stat_key):
    """Average a realgm NCAA stat across destinations."""
    result = {}
    for d in DEST_KEYS:
        vals = [get_ncaa_stat(p, stat_key) for p in buckets[d]]
        vals = [v for v in vals if v is not None]
        result[d] = avg(vals)
    return result


def dest_avg_torvik(field):
    """Average a torvik field across destinations."""
    result = {}
    for d in DEST_KEYS:
        vals = []
        for p in buckets[d]:
            tf = p.get("torvik_final")
            if tf and tf.get(field) is not None:
                try:
                    vals.append(float(tf[field]))
                except (TypeError, ValueError):
                    pass
        result[d] = avg(vals)
    return result


def dest_avg_height():
    """Average height in inches across destinations."""
    result = {}
    result_str = {}
    for d in DEST_KEYS:
        vals = [parse_height_inches(p["ht"]) for p in buckets[d]]
        vals = [v for v in vals if v is not None]
        avg_in = sum(vals) / len(vals) if vals else 0
        result[d] = round(avg_in, 1)
        result_str[d] = inches_to_str(avg_in)
    return result, result_str

# ============================================================================
# Step 5: Compute all stats
# ============================================================================
print("\nComputing stats...")

topics = {}

# ---------------------------------------------------------------------------
# 1. College PPG by destination
# ---------------------------------------------------------------------------
ppg_data = dest_avg_stat("PPG")
topics["ppg_by_destination"] = {
    "keywords": ["ppg", "points", "scoring", "average", "ppg by destination", "college points"],
    "question": "What was the average college PPG for players by pro destination?",
    "data": ppg_data,
    "template": (
        "Average final-year college PPG by pro destination: "
        f"NBA players averaged {ppg_data['nba']} PPG, "
        f"G-League {ppg_data['g_league']} PPG, "
        f"Europe {ppg_data['europe']} PPG, "
        f"Other International {ppg_data['other_intl']} PPG, "
        f"and No Pro Career players averaged {ppg_data['no_pro']} PPG."
    ),
}

# ---------------------------------------------------------------------------
# 2. College RPG by destination
# ---------------------------------------------------------------------------
rpg_data = dest_avg_stat("RPG")
topics["rpg_by_destination"] = {
    "keywords": ["rpg", "rebounds", "rebounding", "boards", "rpg by destination"],
    "question": "What was the average college RPG for players by pro destination?",
    "data": rpg_data,
    "template": (
        "Average final-year college RPG by pro destination: "
        f"NBA {rpg_data['nba']}, G-League {rpg_data['g_league']}, "
        f"Europe {rpg_data['europe']}, Other International {rpg_data['other_intl']}, "
        f"No Pro Career {rpg_data['no_pro']}."
    ),
}

# ---------------------------------------------------------------------------
# 3. College APG by destination
# ---------------------------------------------------------------------------
apg_data = dest_avg_stat("APG")
topics["apg_by_destination"] = {
    "keywords": ["apg", "assists", "passing", "apg by destination"],
    "question": "What was the average college APG for players by pro destination?",
    "data": apg_data,
    "template": (
        "Average final-year college APG by pro destination: "
        f"NBA {apg_data['nba']}, G-League {apg_data['g_league']}, "
        f"Europe {apg_data['europe']}, Other International {apg_data['other_intl']}, "
        f"No Pro Career {apg_data['no_pro']}."
    ),
}

# ---------------------------------------------------------------------------
# 4. College SPG by destination
# ---------------------------------------------------------------------------
spg_data = dest_avg_stat("SPG")
topics["spg_by_destination"] = {
    "keywords": ["spg", "steals", "steal", "defensive steals"],
    "question": "What were the average steals per game in college by pro destination?",
    "data": spg_data,
    "template": (
        "Average final-year college SPG by pro destination: "
        f"NBA {spg_data['nba']}, G-League {spg_data['g_league']}, "
        f"Europe {spg_data['europe']}, Other International {spg_data['other_intl']}, "
        f"No Pro Career {spg_data['no_pro']}."
    ),
}

# ---------------------------------------------------------------------------
# 5. College BPG by destination
# ---------------------------------------------------------------------------
bpg_data = dest_avg_stat("BPG")
topics["bpg_by_destination"] = {
    "keywords": ["bpg", "blocks", "block", "shot blocking"],
    "question": "What were the average blocks per game in college by pro destination?",
    "data": bpg_data,
    "template": (
        "Average final-year college BPG by pro destination: "
        f"NBA {bpg_data['nba']}, G-League {bpg_data['g_league']}, "
        f"Europe {bpg_data['europe']}, Other International {bpg_data['other_intl']}, "
        f"No Pro Career {bpg_data['no_pro']}."
    ),
}

# ---------------------------------------------------------------------------
# 6. Average height by destination
# ---------------------------------------------------------------------------
ht_data, ht_str = dest_avg_height()
topics["height_by_destination"] = {
    "keywords": ["height", "tall", "size", "inches", "how tall"],
    "question": "What is the average height for each pro destination?",
    "data": ht_str,
    "template": (
        "Average height by pro destination: "
        f"NBA {ht_str['nba']}, G-League {ht_str['g_league']}, "
        f"Europe {ht_str['europe']}, Other International {ht_str['other_intl']}, "
        f"No Pro Career {ht_str['no_pro']}."
    ),
}

# ---------------------------------------------------------------------------
# 7. EFG% by destination (torvik)
# ---------------------------------------------------------------------------
efg_data = dest_avg_torvik("efg_pct")
topics["efg_by_destination"] = {
    "keywords": ["efg", "effective field goal", "shooting efficiency", "efg%"],
    "question": "What was the average college EFG% by pro destination?",
    "data": efg_data,
    "template": (
        "Average final-year college EFG% by pro destination: "
        f"NBA {efg_data['nba']}%, G-League {efg_data['g_league']}%, "
        f"Europe {efg_data['europe']}%, Other International {efg_data['other_intl']}%, "
        f"No Pro Career {efg_data['no_pro']}%."
    ),
}

# ---------------------------------------------------------------------------
# 8. TS% by destination (torvik)
# ---------------------------------------------------------------------------
ts_data = dest_avg_torvik("ts_pct")
topics["ts_by_destination"] = {
    "keywords": ["ts%", "true shooting", "ts pct", "true shooting percentage"],
    "question": "What was the average college TS% by pro destination?",
    "data": ts_data,
    "template": (
        "Average final-year college TS% by pro destination: "
        f"NBA {ts_data['nba']}%, G-League {ts_data['g_league']}%, "
        f"Europe {ts_data['europe']}%, Other International {ts_data['other_intl']}%, "
        f"No Pro Career {ts_data['no_pro']}%."
    ),
}

# ---------------------------------------------------------------------------
# 9. Three-point % by destination (torvik)
# ---------------------------------------------------------------------------
threep_data = dest_avg_torvik("threep_pct")
topics["threep_by_destination"] = {
    "keywords": ["three point", "3pt", "three pointer", "3 point", "threep", "three%", "3pt%"],
    "question": "What was the average college 3PT% by pro destination?",
    "data": threep_data,
    "template": (
        "Average final-year college 3PT% by pro destination: "
        f"NBA {threep_data['nba']}%, G-League {threep_data['g_league']}%, "
        f"Europe {threep_data['europe']}%, Other International {threep_data['other_intl']}%, "
        f"No Pro Career {threep_data['no_pro']}%."
    ),
}

# ---------------------------------------------------------------------------
# 10. BPM by destination (torvik)
# ---------------------------------------------------------------------------
bpm_data = dest_avg_torvik("bpm")
topics["bpm_by_destination"] = {
    "keywords": ["bpm", "box plus minus", "plus minus", "advanced stats"],
    "question": "What was the average college BPM (Box Plus/Minus) by pro destination?",
    "data": bpm_data,
    "template": (
        "Average final-year college BPM by pro destination: "
        f"NBA {bpm_data['nba']}, G-League {bpm_data['g_league']}, "
        f"Europe {bpm_data['europe']}, Other International {bpm_data['other_intl']}, "
        f"No Pro Career {bpm_data['no_pro']}."
    ),
}

# ---------------------------------------------------------------------------
# 11. Minutes % by destination (torvik)
# ---------------------------------------------------------------------------
minpct_data = dest_avg_torvik("min_pct")
topics["minutes_by_destination"] = {
    "keywords": ["minutes", "playing time", "min pct", "minutes percentage", "usage"],
    "question": "What was the average college minutes share by pro destination?",
    "data": minpct_data,
    "template": (
        "Average final-year college minutes percentage by pro destination: "
        f"NBA {minpct_data['nba']}%, G-League {minpct_data['g_league']}%, "
        f"Europe {minpct_data['europe']}%, Other International {minpct_data['other_intl']}%, "
        f"No Pro Career {minpct_data['no_pro']}%."
    ),
}

# ---------------------------------------------------------------------------
# 12. Total player counts and percentages
# ---------------------------------------------------------------------------
topics["total_players"] = {
    "keywords": ["how many", "total", "count", "number", "players", "dataset", "sample size", "analyzed"],
    "question": "How many D1 players were analyzed?",
    "data": {"total": total, "counts": counts, "pcts": pcts},
    "template": (
        f"We analyzed {total:,} D1 players whose last college season was between 2014-15 and 2024-25. "
        f"Of these, {counts['nba']:,} ({pcts['nba']}%) reached the NBA, "
        f"{counts['g_league']:,} ({pcts['g_league']}%) went to the G-League, "
        f"{counts['europe']:,} ({pcts['europe']}%) played in Europe, "
        f"{counts['other_intl']:,} ({pcts['other_intl']}%) played in other international leagues, "
        f"and {counts['no_pro']:,} ({pcts['no_pro']}%) had no recorded pro career."
    ),
}

# ---------------------------------------------------------------------------
# 13. Percentage who go pro
# ---------------------------------------------------------------------------
pro_pct = safe_pct(total - counts["no_pro"], total)
topics["pro_percentage"] = {
    "keywords": ["percent", "chance", "odds", "probability", "likelihood", "go pro", "make it"],
    "question": "What percentage of D1 players go pro?",
    "data": {"pro_pct": pro_pct, "nba_pct": pcts["nba"]},
    "template": (
        f"{pro_pct}% of D1 players in our dataset went on to play some form of professional basketball. "
        f"Only {pcts['nba']}% made the NBA with real regular-season playing time. "
        f"{pcts['g_league']}% went to the G-League, {pcts['europe']}% to Europe, "
        f"and {pcts['other_intl']}% to other international leagues."
    ),
}

# ---------------------------------------------------------------------------
# 14-17. Top 20 schools by destination
# ---------------------------------------------------------------------------
for dest_key, label in [("nba", "NBA"), ("g_league", "G-League"), ("europe", "Europe"), ("other_intl", "Other International")]:
    school_counter = Counter(p["school"] for p in buckets[dest_key] if p["school"])
    top20 = school_counter.most_common(20)
    top20_data = [{"school": s, "count": c} for s, c in top20]
    top5_str = ", ".join(f"{s} ({c})" for s, c in top20[:5])
    kw_base = label.lower().replace("-", " ").replace(" ", "_")

    topics[f"top_schools_{dest_key}"] = {
        "keywords": ["school", "college", "university", "produce", "most " + label.lower(),
                      label.lower() + " school", "top school", "top program", label.lower() + " program"],
        "question": f"Which schools produce the most {label} players?",
        "data": top20_data,
        "template": (
            f"Top {label}-producing schools (2015-2025): {top5_str}. "
            f"The top 20 also includes: {', '.join(f'{s} ({c})' for s, c in top20[5:10])}."
        ),
    }

# ---------------------------------------------------------------------------
# 18. Top schools by total pro players
# ---------------------------------------------------------------------------
school_pro_counter = Counter()
for d in ["nba", "g_league", "europe", "other_intl"]:
    for p in buckets[d]:
        if p["school"]:
            school_pro_counter[p["school"]] += 1
top20_pro = school_pro_counter.most_common(20)
top20_pro_data = [{"school": s, "count": c} for s, c in top20_pro]
topics["top_schools_total_pro"] = {
    "keywords": ["most pro", "total pro", "pro players school", "most professional", "best schools",
                  "top programs", "all pro"],
    "question": "Which schools produce the most total pro players?",
    "data": top20_pro_data,
    "template": (
        f"Top schools by total pro players (any destination, 2015-2025): "
        f"{', '.join(f'{s} ({c})' for s, c in top20_pro[:10])}."
    ),
}

# ---------------------------------------------------------------------------
# 19-20. Top conferences by NBA and total pro production
# ---------------------------------------------------------------------------
# Need conference data from torvik
conf_nba = Counter()
conf_pro = Counter()
conf_total = Counter()
for p in classified:
    tf = p.get("torvik_final")
    conf = tf["conference"] if tf and tf.get("conference") else None
    if not conf:
        continue
    conf_total[conf] += 1
    if p["dest"] != "no_pro":
        conf_pro[conf] += 1
    if p["dest"] == "nba":
        conf_nba[conf] += 1

top_conf_nba = conf_nba.most_common(15)
topics["top_conferences_nba"] = {
    "keywords": ["conference nba", "best conference", "nba conference", "conference produce nba",
                  "acc", "sec", "big ten", "big 12", "pac 12", "conference ranking"],
    "question": "Which conferences produce the most NBA players?",
    "data": [{"conference": c, "count": n} for c, n in top_conf_nba],
    "template": (
        f"Top conferences by NBA production: "
        f"{', '.join(f'{c} ({n})' for c, n in top_conf_nba[:10])}."
    ),
}

top_conf_pro = conf_pro.most_common(15)
# Compute pro rate per conference
conf_pro_rate = []
for c, n in conf_pro.most_common(40):
    t = conf_total[c]
    if t >= 50:
        conf_pro_rate.append({"conference": c, "pro_count": n, "total": t, "rate": safe_pct(n, t)})
conf_pro_rate.sort(key=lambda x: x["rate"], reverse=True)

topics["top_conferences_pro"] = {
    "keywords": ["conference pro", "conference total", "pro conference", "conference professional",
                  "conference production"],
    "question": "Which conferences produce the most total pro players?",
    "data": [{"conference": c, "count": n} for c, n in top_conf_pro],
    "template": (
        f"Top conferences by total pro production: "
        f"{', '.join(f'{c} ({n})' for c, n in top_conf_pro[:10])}."
    ),
}

topics["conference_pro_rate"] = {
    "keywords": ["conference rate", "conference percentage", "pro rate conference",
                  "conference efficiency", "best rate"],
    "question": "Which conferences have the highest pro player rate?",
    "data": conf_pro_rate[:15],
    "template": (
        f"Top conferences by pro player rate (min 50 players): "
        f"{', '.join(f'{r['conference']} ({r['rate']}%)' for r in conf_pro_rate[:8])}."
    ),
}

# ---------------------------------------------------------------------------
# 21-26. Career transitions
# ---------------------------------------------------------------------------
transitions = {
    "nba_to_intl": 0, "nba_to_gleague": 0,
    "gleague_to_nba": 0, "gleague_to_intl": 0,
    "europe_to_nba": 0, "europe_to_gleague": 0, "europe_to_other_intl": 0,
    "other_intl_to_nba": 0, "other_intl_to_gleague": 0, "other_intl_to_europe": 0,
}
transition_years = defaultdict(list)  # time before transition

for p in classified:
    dest = p["dest"]
    ls = p["level_set"]
    pro_s = p["pro_seasons"]

    if dest == "nba":
        if "international" in ls:
            transitions["nba_to_intl"] += 1
        if "g_league" in ls and p["gleague_count"] > 0:
            transitions["nba_to_gleague"] += 1
    elif dest == "g_league":
        if "nba" in ls:
            transitions["gleague_to_nba"] += 1
            # Find year of first NBA
            for s in pro_s:
                if s["level"] == "nba" and has_real_nba_season(s["section_types"]):
                    yrs = season_sort_key(s["season"]) - p["last_ncaa_year"]
                    transition_years["gleague_to_nba"].append(yrs)
                    break
        if "international" in ls:
            transitions["gleague_to_intl"] += 1
    elif dest == "europe":
        if "nba" in ls:
            transitions["europe_to_nba"] += 1
            for s in pro_s:
                if s["level"] == "nba" and has_real_nba_season(s["section_types"]):
                    yrs = season_sort_key(s["season"]) - p["last_ncaa_year"]
                    transition_years["europe_to_nba"].append(yrs)
                    break
        if "g_league" in ls:
            transitions["europe_to_gleague"] += 1
    elif dest == "other_intl":
        if "nba" in ls:
            transitions["other_intl_to_nba"] += 1
        if "g_league" in ls:
            transitions["other_intl_to_gleague"] += 1

topics["career_transitions"] = {
    "keywords": ["transition", "switch", "move between", "path", "nba to international",
                  "g league to nba", "gleague to nba", "career path", "pathway"],
    "question": "How many players transitioned between pro levels?",
    "data": transitions,
    "template": (
        f"Career transitions: "
        f"NBA-first players: {transitions['nba_to_intl']} went international, {transitions['nba_to_gleague']} to G-League. "
        f"G-League-first: {transitions['gleague_to_nba']} made the NBA, {transitions['gleague_to_intl']} went international. "
        f"Europe-first: {transitions['europe_to_nba']} made the NBA, {transitions['europe_to_gleague']} came to G-League. "
        f"Other International-first: {transitions['other_intl_to_nba']} made the NBA, {transitions['other_intl_to_gleague']} to G-League."
    ),
}

topics["gleague_to_nba_path"] = {
    "keywords": ["g league to nba", "gleague nba", "g league path", "gleague path nba",
                  "made nba from g league", "g league pipeline"],
    "question": "How many G-League players eventually made the NBA?",
    "data": {
        "count": transitions["gleague_to_nba"],
        "total": counts["g_league"],
        "pct": safe_pct(transitions["gleague_to_nba"], counts["g_league"]),
        "avg_years": avg(transition_years.get("gleague_to_nba", [0])),
    },
    "template": (
        f"Of {counts['g_league']:,} players whose first pro destination was the G-League, "
        f"{transitions['gleague_to_nba']} ({safe_pct(transitions['gleague_to_nba'], counts['g_league'])}%) "
        f"eventually earned real NBA playing time, averaging "
        f"{avg(transition_years.get('gleague_to_nba', [0]))} years after leaving college to reach the NBA."
    ),
}

topics["europe_to_nba_path"] = {
    "keywords": ["europe to nba", "european nba", "europe nba path", "from europe to nba"],
    "question": "How many European players eventually made the NBA?",
    "data": {
        "count": transitions["europe_to_nba"],
        "total": counts["europe"],
        "pct": safe_pct(transitions["europe_to_nba"], counts["europe"]),
    },
    "template": (
        f"Of {counts['europe']:,} players who first went to Europe, "
        f"{transitions['europe_to_nba']} ({safe_pct(transitions['europe_to_nba'], counts['europe'])}%) "
        f"eventually made it to the NBA."
    ),
}

topics["other_intl_to_nba_path"] = {
    "keywords": ["other international nba", "overseas nba", "foreign nba",
                  "international to nba path"],
    "question": "How many Other International players eventually made the NBA?",
    "data": {
        "count": transitions["other_intl_to_nba"],
        "total": counts["other_intl"],
        "pct": safe_pct(transitions["other_intl_to_nba"], counts["other_intl"]),
    },
    "template": (
        f"Of {counts['other_intl']:,} players who first went to other international leagues, "
        f"{transitions['other_intl_to_nba']} ({safe_pct(transitions['other_intl_to_nba'], counts['other_intl'])}%) "
        f"eventually made it to the NBA."
    ),
}

# ---------------------------------------------------------------------------
# 27-28. Career lengths by destination
# ---------------------------------------------------------------------------
career_lengths = {}
for d in ["nba", "g_league", "europe", "other_intl"]:
    lengths = [p["total_pro_seasons"] for p in buckets[d] if p["total_pro_seasons"] > 0]
    career_lengths[d] = {
        "avg": avg(lengths),
        "median": sorted(lengths)[len(lengths)//2] if lengths else 0,
        "count": len(lengths),
    }

topics["career_length_by_destination"] = {
    "keywords": ["career length", "how long", "years pro", "duration", "career duration",
                  "average career", "pro career length", "seasons pro"],
    "question": "What is the average pro career length by first destination?",
    "data": career_lengths,
    "template": (
        f"Average pro career length by first destination: "
        f"NBA-first {career_lengths['nba']['avg']} seasons, "
        f"G-League-first {career_lengths['g_league']['avg']} seasons, "
        f"Europe-first {career_lengths['europe']['avg']} seasons, "
        f"Other International-first {career_lengths['other_intl']['avg']} seasons."
    ),
}

# Career length distributions
for d in ["nba", "g_league", "europe", "other_intl"]:
    lengths = [p["total_pro_seasons"] for p in buckets[d] if p["total_pro_seasons"] > 0]
    dist = Counter()
    for l in lengths:
        if l >= 8:
            dist["8+"] += 1
        else:
            dist[str(l)] += 1
    dist_data = {k: dist.get(k, 0) for k in ["1", "2", "3", "4", "5", "6", "7", "8+"]}

    topics[f"career_length_dist_{d}"] = {
        "keywords": [f"{DEST_LABELS[d].lower()} career distribution", f"{DEST_LABELS[d].lower()} career years",
                     f"how long {DEST_LABELS[d].lower()}", f"{DEST_LABELS[d].lower()} duration",
                     f"{DEST_LABELS[d].lower()} seasons breakdown"],
        "question": f"What is the career length distribution for {DEST_LABELS[d]}-first players?",
        "data": dist_data,
        "template": (
            f"Career length distribution for {DEST_LABELS[d]}-first players: "
            + ", ".join(f"{k} season{'s' if k != '1' else ''}: {v}" for k, v in dist_data.items())
            + f". Average: {career_lengths[d]['avg']} seasons."
        ),
    }

# ---------------------------------------------------------------------------
# 29. Long NBA careers (5+ years)
# ---------------------------------------------------------------------------
nba_long = [p for p in buckets["nba"] if p["total_pro_seasons"] >= 5]
nba_short = [p for p in buckets["nba"] if p["total_pro_seasons"] < 5]
nba_long_ppg = avg([get_ncaa_stat(p, "PPG") for p in nba_long if get_ncaa_stat(p, "PPG") is not None])
nba_short_ppg = avg([get_ncaa_stat(p, "PPG") for p in nba_short if get_ncaa_stat(p, "PPG") is not None])

topics["long_nba_career"] = {
    "keywords": ["long nba", "5 year", "sustained", "lasting nba", "nba career 5",
                  "long career nba", "nba longevity"],
    "question": "What percentage of NBA players have long careers (5+ years)?",
    "data": {
        "long_count": len(nba_long),
        "total": counts["nba"],
        "pct": safe_pct(len(nba_long), counts["nba"]),
        "long_ppg": nba_long_ppg,
        "short_ppg": nba_short_ppg,
    },
    "template": (
        f"Of {counts['nba']} players who reached the NBA, {len(nba_long)} ({safe_pct(len(nba_long), counts['nba'])}%) "
        f"had careers of 5 or more seasons. These long-career players averaged {nba_long_ppg} PPG in their final "
        f"college season, vs {nba_short_ppg} for those with shorter NBA stints."
    ),
}

# ---------------------------------------------------------------------------
# 30. Short NBA career outcomes
# ---------------------------------------------------------------------------
nba_short_to_intl = sum(1 for p in nba_short if "international" in p["level_set"])
nba_short_to_gl = sum(1 for p in nba_short if "g_league" in p["level_set"])
nba_short_out = len(nba_short) - nba_short_to_intl - nba_short_to_gl

topics["short_nba_outcomes"] = {
    "keywords": ["nba left", "short nba", "brief nba", "wash out", "nba bust",
                  "nba flameout", "didn't last nba"],
    "question": "What happens to NBA players who don't last 5 years?",
    "data": {
        "count": len(nba_short),
        "to_intl": nba_short_to_intl,
        "to_gl": nba_short_to_gl,
        "out": nba_short_out,
    },
    "template": (
        f"Of NBA players with shorter careers (<5 years): "
        f"{nba_short_to_intl} transitioned to international basketball, "
        f"{nba_short_to_gl} moved to the G-League, "
        f"and {nba_short_out} left professional basketball entirely."
    ),
}

# ---------------------------------------------------------------------------
# 31-34. Year-over-year trends
# ---------------------------------------------------------------------------
year_buckets = defaultdict(lambda: defaultdict(int))
for p in classified:
    grad_year = p["last_ncaa_year"] + 1  # graduation year
    year_buckets[grad_year][p["dest"]] += 1
    year_buckets[grad_year]["total"] += 1

trend_years = sorted(y for y in year_buckets if 2015 <= y <= 2024)
for dest_key, label in [("nba", "NBA"), ("g_league", "G-League"), ("europe", "Europe"), ("other_intl", "Other International")]:
    trend_data = []
    for y in trend_years:
        t = year_buckets[y]["total"]
        c = year_buckets[y][dest_key]
        trend_data.append({"year": y, "count": c, "total": t, "pct": safe_pct(c, t)})

    trend_str = ", ".join(f"{d['year']}: {d['pct']}%" for d in trend_data)
    topics[f"trend_{dest_key}"] = {
        "keywords": [f"{label.lower()} trend", f"{label.lower()} year", f"{label.lower()} over time",
                     f"{label.lower()} by year", "trend", "year over year", f"{label.lower()} percentage year"],
        "question": f"How has the {label} rate changed year over year?",
        "data": trend_data,
        "template": (
            f"{label} percentage by graduation year: {trend_str}."
        ),
    }

# Overall pro trend
pro_trend = []
for y in trend_years:
    t = year_buckets[y]["total"]
    no_pro = year_buckets[y]["no_pro"]
    pro_c = t - no_pro
    pro_trend.append({"year": y, "pro_pct": safe_pct(pro_c, t), "total": t})
pro_trend_str = ", ".join(f"{d['year']}: {d['pro_pct']}%" for d in pro_trend)
topics["trend_pro_overall"] = {
    "keywords": ["pro trend", "overall trend", "pro rate over time", "going pro trend",
                  "pro percentage year"],
    "question": "How has the overall pro rate changed year over year?",
    "data": pro_trend,
    "template": f"Overall pro rate by graduation year: {pro_trend_str}.",
}

# ---------------------------------------------------------------------------
# 35. Position breakdown by destination
# ---------------------------------------------------------------------------
for d in DEST_KEYS:
    pos_counter = Counter(p["pos"] for p in buckets[d] if p["pos"])
    top_pos = pos_counter.most_common(10)
    total_d = sum(c for _, c in top_pos)
    pos_str = ", ".join(f"{pos}: {c} ({safe_pct(c, total_d)}%)" for pos, c in top_pos)

    topics[f"position_{d}"] = {
        "keywords": ["position", "guard", "forward", "center", f"{DEST_LABELS[d].lower()} position",
                      "pos", "pg", "sg", "sf", "pf"],
        "question": f"What positions are most common among {DEST_LABELS[d]} players?",
        "data": [{"pos": pos, "count": c, "pct": safe_pct(c, total_d)} for pos, c in top_pos],
        "template": f"Position breakdown for {DEST_LABELS[d]} players: {pos_str}.",
    }

# ---------------------------------------------------------------------------
# 36. NCAA seasons before going pro
# ---------------------------------------------------------------------------
ncaa_years_data = {}
for d in DEST_KEYS:
    vals = [p["ncaa_season_count"] for p in buckets[d]]
    ncaa_years_data[d] = avg(vals)

topics["ncaa_seasons_before_pro"] = {
    "keywords": ["college years", "how long college", "ncaa seasons", "years in college",
                  "one and done", "early entry", "college career length"],
    "question": "How many years did players spend in college before going pro?",
    "data": ncaa_years_data,
    "template": (
        f"Average NCAA seasons before turning pro: "
        f"NBA {ncaa_years_data['nba']}, G-League {ncaa_years_data['g_league']}, "
        f"Europe {ncaa_years_data['europe']}, Other International {ncaa_years_data['other_intl']}, "
        f"No Pro Career {ncaa_years_data['no_pro']}."
    ),
}

# ---------------------------------------------------------------------------
# 37. Class year distribution by destination
# ---------------------------------------------------------------------------
for d in ["nba", "g_league", "europe", "other_intl"]:
    class_counter = Counter(p["class_year"] for p in buckets[d] if p["class_year"])
    class_data = class_counter.most_common(6)
    total_d = sum(c for _, c in class_data)
    class_str = ", ".join(f"{cy}: {c} ({safe_pct(c, total_d)}%)" for cy, c in class_data)

    topics[f"class_year_{d}"] = {
        "keywords": [f"{DEST_LABELS[d].lower()} class", "freshman", "sophomore", "junior", "senior",
                     "class year", f"class year {DEST_LABELS[d].lower()}"],
        "question": f"What class year are most {DEST_LABELS[d]} players when they leave college?",
        "data": [{"class_year": cy, "count": c} for cy, c in class_data],
        "template": f"Class year breakdown for {DEST_LABELS[d]} players: {class_str}.",
    }

# ---------------------------------------------------------------------------
# 38. Longest pro careers
# ---------------------------------------------------------------------------
longest_careers = sorted(
    [p for p in classified if p["total_pro_seasons"] > 0],
    key=lambda p: p["total_pro_seasons"],
    reverse=True,
)[:20]
longest_data = [{"name": p["name"], "school": p["school"], "seasons": p["total_pro_seasons"], "dest": p["dest"]}
                for p in longest_careers]
top5_longest = ", ".join(f"{p['name']} ({p['school']}, {p['seasons']} seasons)" for p in longest_data[:5])

topics["longest_careers"] = {
    "keywords": ["longest career", "most seasons", "longest pro", "most pro seasons",
                  "longest playing", "veteran"],
    "question": "Which players had the longest pro careers?",
    "data": longest_data,
    "template": f"Players with the longest pro careers in our dataset: {top5_longest}.",
}

# ---------------------------------------------------------------------------
# 39. Most common international countries/leagues
# ---------------------------------------------------------------------------
country_counter = Counter()
for p in classified:
    for team in p["all_intl_teams"]:
        if isinstance(team, str):
            # Extract country from parentheses or use team name
            m = re.search(r'\(([^)]+)\)', team)
            if m:
                country_counter[m.group(1).strip()] += 1
            else:
                country_counter[team.strip()] += 1

top_countries = country_counter.most_common(20)
top_countries_str = ", ".join(f"{c} ({n})" for c, n in top_countries[:10])
topics["top_international_destinations"] = {
    "keywords": ["international destination", "country", "league", "overseas", "where play",
                  "international league", "foreign league", "most common country"],
    "question": "What are the most common international destinations?",
    "data": [{"destination": c, "count": n} for c, n in top_countries],
    "template": f"Most common international team/league destinations: {top_countries_str}.",
}

# ---------------------------------------------------------------------------
# 40-42. Specific school comparisons (top schools)
# ---------------------------------------------------------------------------
top_compare_schools = ["Kentucky", "Duke", "Kansas", "North Carolina",
                       "Gonzaga", "Virginia", "Villanova", "Arizona",
                       "Michigan State", "UCLA"]

school_compare_data = {}
for school in top_compare_schools:
    school_players = [p for p in classified if p["school"] and school.lower() in p["school"].lower()]
    if not school_players:
        continue
    sc_total = len(school_players)
    sc_dests = Counter(p["dest"] for p in school_players)
    sc_ppg_vals = [get_ncaa_stat(p, "PPG") for p in school_players if get_ncaa_stat(p, "PPG") is not None]
    school_compare_data[school] = {
        "total": sc_total,
        "nba": sc_dests.get("nba", 0),
        "g_league": sc_dests.get("g_league", 0),
        "europe": sc_dests.get("europe", 0),
        "other_intl": sc_dests.get("other_intl", 0),
        "no_pro": sc_dests.get("no_pro", 0),
        "nba_pct": safe_pct(sc_dests.get("nba", 0), sc_total),
        "pro_pct": safe_pct(sc_total - sc_dests.get("no_pro", 0), sc_total),
        "avg_ppg": avg(sc_ppg_vals),
    }

topics["school_comparison"] = {
    "keywords": ["compare school", "duke vs", "kentucky vs", "school comparison", "compare program",
                  "which school better", "school matchup", "head to head"],
    "question": "How do top schools compare in pro production?",
    "data": school_compare_data,
    "template": (
        "Top school comparison (NBA count / total players / NBA rate): "
        + "; ".join(f"{s}: {d['nba']}/{d['total']} ({d['nba_pct']}%)" for s, d in
                    sorted(school_compare_data.items(), key=lambda x: x[1]["nba"], reverse=True))
        + "."
    ),
}

# Individual school topics
for school, sdata in school_compare_data.items():
    school_key = school.lower().replace(" ", "_")
    topics[f"school_{school_key}"] = {
        "keywords": [school.lower(), school_key, f"{school.lower()} players",
                     f"{school.lower()} nba", f"{school.lower()} pro"],
        "question": f"What are the pro outcomes for {school} players?",
        "data": sdata,
        "template": (
            f"{school} pro outcomes (2015-2025): {sdata['total']} players total. "
            f"{sdata['nba']} NBA ({sdata['nba_pct']}%), {sdata['g_league']} G-League, "
            f"{sdata['europe']} Europe, {sdata['other_intl']} Other International, "
            f"{sdata['no_pro']} No Pro. Average final-year PPG: {sdata['avg_ppg']}. "
            f"Overall pro rate: {sdata['pro_pct']}%."
        ),
    }

# ---------------------------------------------------------------------------
# 43. No pro career stats
# ---------------------------------------------------------------------------
nopro_ppg = avg([get_ncaa_stat(p, "PPG") for p in buckets["no_pro"] if get_ncaa_stat(p, "PPG") is not None])
nopro_rpg = avg([get_ncaa_stat(p, "RPG") for p in buckets["no_pro"] if get_ncaa_stat(p, "RPG") is not None])
nopro_apg = avg([get_ncaa_stat(p, "APG") for p in buckets["no_pro"] if get_ncaa_stat(p, "APG") is not None])
topics["no_pro_stats"] = {
    "keywords": ["no pro", "didn't make", "never pro", "end career", "no professional",
                  "undrafted", "not drafted"],
    "question": "What are the stats of players who never went pro?",
    "data": {
        "ppg": nopro_ppg, "rpg": nopro_rpg, "apg": nopro_apg,
        "count": counts["no_pro"], "pct": pcts["no_pro"],
        "height": ht_str["no_pro"],
    },
    "template": (
        f"Players with no recorded pro career averaged {nopro_ppg} PPG, {nopro_rpg} RPG, "
        f"{nopro_apg} APG in their final college season. Average height: {ht_str['no_pro']}. "
        f"This group represents {pcts['no_pro']}% of all D1 players ({counts['no_pro']:,} players)."
    ),
}

# ---------------------------------------------------------------------------
# 44. NBA player profile
# ---------------------------------------------------------------------------
nba_ppg = ppg_data["nba"]
nba_rpg = rpg_data["nba"]
nba_apg = apg_data["nba"]
topics["nba_player_profile"] = {
    "keywords": ["nba player", "nba average", "nba profile", "typical nba", "nba stats",
                  "what does nba player look like", "nba college stats"],
    "question": "What does the typical NBA player's college profile look like?",
    "data": {
        "ppg": nba_ppg, "rpg": nba_rpg, "apg": nba_apg,
        "height": ht_str["nba"], "efg": efg_data["nba"], "ts": ts_data["nba"],
        "ncaa_years": ncaa_years_data["nba"],
    },
    "template": (
        f"The typical NBA player's final college season: {nba_ppg} PPG, {nba_rpg} RPG, "
        f"{nba_apg} APG. Average height: {ht_str['nba']}. EFG%: {efg_data['nba']}%, "
        f"TS%: {ts_data['nba']}%. They spent an average of {ncaa_years_data['nba']} seasons in college."
    ),
}

# ---------------------------------------------------------------------------
# 45. G-League player profile
# ---------------------------------------------------------------------------
topics["gleague_player_profile"] = {
    "keywords": ["g league player", "g league average", "g league profile", "typical g league",
                  "g league stats", "gleague"],
    "question": "What does the typical G-League player's college profile look like?",
    "data": {
        "ppg": ppg_data["g_league"], "rpg": rpg_data["g_league"], "apg": apg_data["g_league"],
        "height": ht_str["g_league"], "efg": efg_data["g_league"],
    },
    "template": (
        f"The typical G-League player's final college season: {ppg_data['g_league']} PPG, "
        f"{rpg_data['g_league']} RPG, {apg_data['g_league']} APG. Average height: {ht_str['g_league']}. "
        f"EFG%: {efg_data['g_league']}%. They spent {ncaa_years_data['g_league']} seasons in college."
    ),
}

# ---------------------------------------------------------------------------
# 46. Europe player profile
# ---------------------------------------------------------------------------
topics["europe_player_profile"] = {
    "keywords": ["europe player", "european player", "europe average", "europe profile",
                  "typical europe", "play in europe", "european basketball"],
    "question": "What does the typical Europe-bound player's college profile look like?",
    "data": {
        "ppg": ppg_data["europe"], "rpg": rpg_data["europe"], "apg": apg_data["europe"],
        "height": ht_str["europe"], "efg": efg_data["europe"],
    },
    "template": (
        f"The typical Europe-bound player's final college season: {ppg_data['europe']} PPG, "
        f"{rpg_data['europe']} RPG, {apg_data['europe']} APG. Average height: {ht_str['europe']}. "
        f"EFG%: {efg_data['europe']}%. They spent {ncaa_years_data['europe']} seasons in college."
    ),
}

# ---------------------------------------------------------------------------
# 47. Other International player profile
# ---------------------------------------------------------------------------
topics["other_intl_player_profile"] = {
    "keywords": ["other international player", "international player", "overseas player",
                  "international profile", "play overseas", "international basketball"],
    "question": "What does the typical Other International player's college profile look like?",
    "data": {
        "ppg": ppg_data["other_intl"], "rpg": rpg_data["other_intl"], "apg": apg_data["other_intl"],
        "height": ht_str["other_intl"], "efg": efg_data["other_intl"],
    },
    "template": (
        f"The typical Other International player's final college season: {ppg_data['other_intl']} PPG, "
        f"{rpg_data['other_intl']} RPG, {apg_data['other_intl']} APG. "
        f"Average height: {ht_str['other_intl']}. EFG%: {efg_data['other_intl']}%."
    ),
}

# ---------------------------------------------------------------------------
# 48. Long Europe careers
# ---------------------------------------------------------------------------
europe_long = [p for p in buckets["europe"] if p["total_pro_seasons"] >= 5]
topics["long_europe_career"] = {
    "keywords": ["europe long", "european career", "europe 5", "long europe",
                  "europe career length"],
    "question": "How many Europe players had long careers (5+ seasons)?",
    "data": {
        "long_count": len(europe_long),
        "total": counts["europe"],
        "pct": safe_pct(len(europe_long), counts["europe"]),
    },
    "template": (
        f"Of {counts['europe']:,} Europe-first players, {len(europe_long)} "
        f"({safe_pct(len(europe_long), counts['europe'])}%) had careers of 5+ pro seasons."
    ),
}

# ---------------------------------------------------------------------------
# 49. Long Other International careers
# ---------------------------------------------------------------------------
ointl_long = [p for p in buckets["other_intl"] if p["total_pro_seasons"] >= 5]
topics["long_other_intl_career"] = {
    "keywords": ["other international long", "overseas career", "international 5",
                  "long international", "other intl career length"],
    "question": "How many Other International players had long careers (5+ seasons)?",
    "data": {
        "long_count": len(ointl_long),
        "total": counts["other_intl"],
        "pct": safe_pct(len(ointl_long), counts["other_intl"]),
    },
    "template": (
        f"Of {counts['other_intl']:,} Other International-first players, {len(ointl_long)} "
        f"({safe_pct(len(ointl_long), counts['other_intl'])}%) had careers of 5+ pro seasons."
    ),
}

# ---------------------------------------------------------------------------
# 50. PPG threshold analysis
# ---------------------------------------------------------------------------
ppg_thresholds = [5, 10, 15, 20]
threshold_data = {}
for thresh in ppg_thresholds:
    above = [p for p in classified if (get_ncaa_stat(p, "PPG") or 0) >= thresh]
    above_pro = [p for p in above if p["dest"] != "no_pro"]
    above_nba = [p for p in above if p["dest"] == "nba"]
    threshold_data[thresh] = {
        "total": len(above),
        "pro_count": len(above_pro),
        "nba_count": len(above_nba),
        "pro_pct": safe_pct(len(above_pro), len(above)),
        "nba_pct": safe_pct(len(above_nba), len(above)),
    }

topics["ppg_threshold"] = {
    "keywords": ["ppg threshold", "scoring threshold", "minimum ppg", "how many points need",
                  "points to go pro", "scoring requirement", "need to score"],
    "question": "How does scoring in college correlate with going pro?",
    "data": threshold_data,
    "template": (
        "Pro rates by college PPG threshold: "
        + "; ".join(f"{t}+ PPG: {d['pro_pct']}% went pro, {d['nba_pct']}% NBA ({d['total']} players)"
                    for t, d in threshold_data.items())
        + "."
    ),
}

# ---------------------------------------------------------------------------
# 51. Height threshold analysis
# ---------------------------------------------------------------------------
ht_thresholds = [(75, "6-3"), (78, "6-6"), (81, "6-9"), (84, "7-0")]
ht_thresh_data = {}
for inches, label in ht_thresholds:
    above = [p for p in classified if (parse_height_inches(p["ht"]) or 0) >= inches]
    above_pro = [p for p in above if p["dest"] != "no_pro"]
    above_nba = [p for p in above if p["dest"] == "nba"]
    ht_thresh_data[label] = {
        "total": len(above),
        "pro_pct": safe_pct(len(above_pro), len(above)),
        "nba_pct": safe_pct(len(above_nba), len(above)),
    }

topics["height_threshold"] = {
    "keywords": ["height threshold", "minimum height", "how tall need", "height requirement",
                  "tall enough", "height to go pro", "height nba"],
    "question": "How does height correlate with going pro?",
    "data": ht_thresh_data,
    "template": (
        "Pro rates by height: "
        + "; ".join(f"{label}+: {d['pro_pct']}% went pro, {d['nba_pct']}% NBA ({d['total']} players)"
                    for label, d in ht_thresh_data.items())
        + "."
    ),
}

# ---------------------------------------------------------------------------
# 52. First-year pro vs multi-year pro
# ---------------------------------------------------------------------------
one_year = [p for p in classified if p["total_pro_seasons"] == 1 and p["dest"] != "no_pro"]
multi_year = [p for p in classified if p["total_pro_seasons"] > 1 and p["dest"] != "no_pro"]
one_year_ppg = avg([get_ncaa_stat(p, "PPG") for p in one_year if get_ncaa_stat(p, "PPG") is not None])
multi_year_ppg = avg([get_ncaa_stat(p, "PPG") for p in multi_year if get_ncaa_stat(p, "PPG") is not None])

topics["one_vs_multi_year"] = {
    "keywords": ["one year pro", "single season", "one and done pro", "flash in pan",
                  "sustained career", "multi year"],
    "question": "How do one-year pro players compare to multi-year?",
    "data": {
        "one_year_count": len(one_year),
        "multi_year_count": len(multi_year),
        "one_year_ppg": one_year_ppg,
        "multi_year_ppg": multi_year_ppg,
    },
    "template": (
        f"Of players who went pro, {len(one_year):,} had just 1 season and {len(multi_year):,} had 2+ seasons. "
        f"One-year pros averaged {one_year_ppg} college PPG vs {multi_year_ppg} for multi-year pros."
    ),
}

# ---------------------------------------------------------------------------
# 53. NBA draft vs undrafted (based on whether they have real NBA seasons)
# ---------------------------------------------------------------------------
topics["nba_overview"] = {
    "keywords": ["nba overview", "nba summary", "nba breakdown", "about nba players"],
    "question": "Give me an overview of NBA outcomes.",
    "data": {
        "count": counts["nba"],
        "pct": pcts["nba"],
        "long_count": len(nba_long),
        "long_pct": safe_pct(len(nba_long), counts["nba"]),
        "to_intl": transitions["nba_to_intl"],
    },
    "template": (
        f"NBA Overview: {counts['nba']} players ({pcts['nba']}% of D1 graduates) reached the NBA. "
        f"{len(nba_long)} ({safe_pct(len(nba_long), counts['nba'])}%) had 5+ year careers. "
        f"{transitions['nba_to_intl']} transitioned to international basketball after the NBA. "
        f"Average career: {career_lengths['nba']['avg']} seasons."
    ),
}

# ---------------------------------------------------------------------------
# 54. G-League overview
# ---------------------------------------------------------------------------
topics["gleague_overview"] = {
    "keywords": ["g league overview", "g league summary", "gleague breakdown", "about g league"],
    "question": "Give me an overview of G-League outcomes.",
    "data": {
        "count": counts["g_league"],
        "pct": pcts["g_league"],
        "to_nba": transitions["gleague_to_nba"],
        "to_intl": transitions["gleague_to_intl"],
    },
    "template": (
        f"G-League Overview: {counts['g_league']} players ({pcts['g_league']}% of D1 graduates). "
        f"{transitions['gleague_to_nba']} ({safe_pct(transitions['gleague_to_nba'], counts['g_league'])}%) "
        f"eventually made the NBA. {transitions['gleague_to_intl']} went international. "
        f"Average career: {career_lengths['g_league']['avg']} seasons."
    ),
}

# ---------------------------------------------------------------------------
# 55. Europe overview
# ---------------------------------------------------------------------------
topics["europe_overview"] = {
    "keywords": ["europe overview", "europe summary", "european breakdown", "about europe",
                  "european basketball overview"],
    "question": "Give me an overview of European basketball outcomes.",
    "data": {
        "count": counts["europe"],
        "pct": pcts["europe"],
        "to_nba": transitions["europe_to_nba"],
    },
    "template": (
        f"Europe Overview: {counts['europe']} players ({pcts['europe']}% of D1 graduates) went to Europe. "
        f"{transitions['europe_to_nba']} ({safe_pct(transitions['europe_to_nba'], counts['europe'])}%) "
        f"eventually made the NBA. Average career: {career_lengths['europe']['avg']} seasons. "
        f"{len(europe_long)} ({safe_pct(len(europe_long), counts['europe'])}%) had 5+ year careers."
    ),
}

# ---------------------------------------------------------------------------
# 56. Other International overview
# ---------------------------------------------------------------------------
topics["other_intl_overview"] = {
    "keywords": ["other international overview", "international summary", "overseas breakdown",
                  "about international", "non-european international"],
    "question": "Give me an overview of Other International outcomes.",
    "data": {
        "count": counts["other_intl"],
        "pct": pcts["other_intl"],
        "to_nba": transitions["other_intl_to_nba"],
    },
    "template": (
        f"Other International Overview: {counts['other_intl']} players ({pcts['other_intl']}% of D1 graduates). "
        f"{transitions['other_intl_to_nba']} ({safe_pct(transitions['other_intl_to_nba'], counts['other_intl'])}%) "
        f"eventually made the NBA. Average career: {career_lengths['other_intl']['avg']} seasons. "
        f"{len(ointl_long)} ({safe_pct(len(ointl_long), counts['other_intl'])}%) had 5+ year careers."
    ),
}

# ---------------------------------------------------------------------------
# 57. Weight by destination
# ---------------------------------------------------------------------------
def parse_weight(wt_str):
    if not wt_str:
        return None
    try:
        return int(re.sub(r'[^\d]', '', str(wt_str)))
    except (ValueError, TypeError):
        return None

# We don't have weight in classified easily, reload from db
wt_db = sqlite3.connect(REALGM_DB)
wt_db.row_factory = sqlite3.Row
wt_cur = wt_db.cursor()
wt_cur.execute("SELECT realgm_id, wt FROM realgm_players")
wt_lookup = {}
for row in wt_cur:
    w = parse_weight(row["wt"])
    if w and 130 <= w <= 400:
        wt_lookup[row["realgm_id"]] = w
wt_db.close()

wt_data = {}
for d in DEST_KEYS:
    vals = [wt_lookup.get(p["pid"]) for p in buckets[d]]
    vals = [v for v in vals if v is not None]
    wt_data[d] = avg(vals)

topics["weight_by_destination"] = {
    "keywords": ["weight", "heavy", "lbs", "pounds", "how much weigh"],
    "question": "What is the average weight for each pro destination?",
    "data": wt_data,
    "template": (
        f"Average weight by pro destination: "
        f"NBA {wt_data['nba']} lbs, G-League {wt_data['g_league']} lbs, "
        f"Europe {wt_data['europe']} lbs, Other International {wt_data['other_intl']} lbs, "
        f"No Pro Career {wt_data['no_pro']} lbs."
    ),
}

# ---------------------------------------------------------------------------
# 58. Torvik PPG by destination (for comparison)
# ---------------------------------------------------------------------------
torvik_ppg = dest_avg_torvik("ppg")
topics["torvik_ppg_by_destination"] = {
    "keywords": ["torvik ppg", "barttorvik", "torvik scoring", "college stats ppg"],
    "question": "What is the Torvik PPG by destination?",
    "data": torvik_ppg,
    "template": (
        f"Barttorvik final-year college PPG by pro destination: "
        f"NBA {torvik_ppg['nba']}, G-League {torvik_ppg['g_league']}, "
        f"Europe {torvik_ppg['europe']}, Other International {torvik_ppg['other_intl']}, "
        f"No Pro Career {torvik_ppg['no_pro']}."
    ),
}

# ---------------------------------------------------------------------------
# 59. Free throw % by destination
# ---------------------------------------------------------------------------
ft_data = dest_avg_torvik("ft_pct")
topics["ft_by_destination"] = {
    "keywords": ["free throw", "ft%", "free throw percentage", "ft pct", "foul shot"],
    "question": "What was the average college FT% by pro destination?",
    "data": ft_data,
    "template": (
        f"Average final-year college FT% by pro destination: "
        f"NBA {ft_data['nba']}%, G-League {ft_data['g_league']}%, "
        f"Europe {ft_data['europe']}%, Other International {ft_data['other_intl']}%, "
        f"No Pro Career {ft_data['no_pro']}%."
    ),
}

# ---------------------------------------------------------------------------
# 60. Games played by destination
# ---------------------------------------------------------------------------
gp_data = dest_avg_torvik("games_played")
topics["games_played_by_destination"] = {
    "keywords": ["games played", "games", "gp", "how many games"],
    "question": "What was the average games played in final college season by destination?",
    "data": gp_data,
    "template": (
        f"Average games played in final college season by pro destination: "
        f"NBA {gp_data['nba']}, G-League {gp_data['g_league']}, "
        f"Europe {gp_data['europe']}, Other International {gp_data['other_intl']}, "
        f"No Pro Career {gp_data['no_pro']}."
    ),
}

# ============================================================================
# Step 6: Output JSON
# ============================================================================
output = {
    "generated": "2026-03-25",
    "total_players": total,
    "counts": counts,
    "percentages": pcts,
    "topics": topics,
}

print(f"\nWriting {len(topics)} topics to {OUTPUT_PATH}...")
with open(OUTPUT_PATH, "w") as f:
    json.dump(output, f, indent=2, default=str)

print(f"Done! Output: {OUTPUT_PATH}")
print(f"File size: {os.path.getsize(OUTPUT_PATH) / 1024:.1f} KB")
