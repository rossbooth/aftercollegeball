#!/usr/bin/env python3
"""
Generate player table data for the website's "View All Player Data" component.
Outputs JSON to website/public/data/player-table.json
"""

import sqlite3
import json
import os
from collections import defaultdict

DB_PATH = "/Users/rjb/Desktop/Hoop Research/d1-basketball-outcomes/data/d1_basketball.db"
OUTPUT_DIR = "/Users/rjb/Desktop/Hoop Research/d1-basketball-outcomes/website/public/data/"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "player-table.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# European team keywords (same list as generate-sankey-data.py)
# ---------------------------------------------------------------------------
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
    "Rosa", "Asseco", "Turow", "Enea", "Spojnia", "Dekorglass", "Lublin",
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


def has_real_nba_season(section_types):
    return "NBA Season Stats" in section_types


def season_sort_key(s):
    return int(s.split("-")[0])


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
print("Loading data from database...")

db = sqlite3.connect(DB_PATH)
db.row_factory = sqlite3.Row
cur = db.cursor()

cur.execute("""
    SELECT t.realgm_id, t.season, t.level, t.section_types, t.teams,
           p.name, p.school
    FROM realgm_timeline t
    JOIN realgm_players p ON t.realgm_id = p.realgm_id
    ORDER BY t.realgm_id, t.season
""")

players = defaultdict(lambda: {"seasons": [], "name": "", "school": ""})
for row in cur:
    pid = row["realgm_id"]
    players[pid]["name"] = row["name"]
    players[pid]["school"] = row["school"]
    section_types = json.loads(row["section_types"]) if row["section_types"] else []
    teams = json.loads(row["teams"]) if row["teams"] else []
    players[pid]["seasons"].append({
        "season": row["season"],
        "level": row["level"],
        "section_types": section_types,
        "teams": teams,
    })

db.close()
print(f"Loaded {len(players)} players from DB")

# ---------------------------------------------------------------------------
# Classify each player
# ---------------------------------------------------------------------------
MIN_LAST_NCAA = "2014-2015"
MAX_LAST_NCAA = "2024-2025"
STILL_IN_COLLEGE = "2025-2026"

result_players = []

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

    # lastCollegeSeason = the ending year of the last NCAA season (e.g. "2019-2020" -> 2020)
    last_college_season = int(last_ncaa_season.split("-")[1])

    last_ncaa_year = season_sort_key(last_ncaa_season)
    post_college = sorted(
        [s for s in pdata["seasons"] if season_sort_key(s["season"]) > last_ncaa_year],
        key=lambda s: season_sort_key(s["season"])
    )

    pro_levels = {"nba", "g_league", "international"}
    pro_seasons = [s for s in post_college if s["level"] in pro_levels]

    # Determine first pro destination
    first_pro = None
    first_pro_team = None
    for s in pro_seasons:
        if s["level"] == "nba":
            if has_real_nba_season(s["section_types"]):
                first_pro = "nba"
                first_pro_team = s["teams"][0] if s["teams"] else None
                break
            continue
        elif s["level"] == "g_league":
            first_pro = "gleague"
            first_pro_team = s["teams"][0] if s["teams"] else None
            break
        elif s["level"] == "international":
            # Determine if europe or other_intl
            is_europe = False
            for team in s["teams"]:
                if isinstance(team, str) and is_european_team(team):
                    is_europe = True
                    break
            first_pro = "europe" if is_europe else "other_intl"
            first_pro_team = s["teams"][0] if s["teams"] else None
            break

    if first_pro is None:
        first_pro = "none"

    # Count pro years — only completed seasons (exclude current 2025-2026)
    completed_pro = [s for s in pro_seasons if s["season"] != "2025-2026"]
    pro_years = len(completed_pro)

    # Find last pro season year
    last_pro_season = None
    if pro_seasons:
        last_pro_season = max(season_sort_key(s["season"]) for s in pro_seasons)

    # Find current team — only if still active (played in 2024-2025 or 2025-2026)
    # If their last pro season was before 2024, they're out of basketball
    current_team = None
    still_active = last_pro_season is not None and last_pro_season >= 2024
    if still_active and pro_seasons:
        for s in reversed(pro_seasons):
            if s["teams"]:
                current_team = s["teams"][0] if s["teams"][0] != "N/A" else None
                break

    # For inactive players, show their last team
    last_team = None
    if not still_active and pro_seasons:
        for s in reversed(pro_seasons):
            if s["teams"]:
                last_team = s["teams"][0] if s["teams"][0] != "N/A" else None
                break

    # Determine current level (where they are NOW)
    current_level = "none"
    if still_active and pro_seasons:
        most_recent = pro_seasons[-1]
        lvl = most_recent["level"]
        if lvl == "nba":
            current_level = "nba"
        elif lvl == "g_league":
            current_level = "gleague"
        elif lvl == "international":
            # Check if European
            is_eu = False
            for t in most_recent["teams"]:
                if isinstance(t, str) and is_european_team(t):
                    is_eu = True
                    break
            current_level = "europe" if is_eu else "other_intl"
    elif not still_active and pro_seasons:
        current_level = "out"  # left basketball

    # Build compact career timeline (post-college only)
    timeline = []
    for s in pdata["seasons"]:
        yr = season_sort_key(s["season"])
        if yr <= last_ncaa_year:
            continue
        lvl = s["level"]
        if lvl not in ("nba", "g_league", "international", "national_team"):
            continue
        # Classify international
        display_level = lvl
        if lvl == "international":
            is_eu = any(isinstance(t, str) and is_european_team(t) for t in s["teams"])
            display_level = "europe" if is_eu else "intl"
        elif lvl == "g_league":
            display_level = "gleague"
        elif lvl == "national_team":
            display_level = "natl"
        team = s["teams"][0] if s["teams"] and s["teams"][0] != "N/A" else None
        season_label = s["season"].split("-")[0]  # e.g. "2019"
        timeline.append({"yr": season_label, "lvl": display_level, "tm": team})

    result_players.append({
        "name": pdata["name"],
        "school": pdata["school"] or "Unknown",
        "lastCollegeSeason": last_college_season,
        "firstProDest": first_pro,
        "firstProTeam": first_pro_team,
        "proYears": pro_years,
        "currentTeam": current_team,
        "lastTeam": last_team,
        "active": still_active,
        "currentLevel": current_level,
        "timeline": timeline,
    })

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
print(f"Classified {len(result_players)} players")

# Sort: NBA first, then G-League, then Europe, then Other Intl, then None
dest_order = {"nba": 0, "gleague": 1, "europe": 2, "other_intl": 3, "none": 4}
result_players.sort(key=lambda p: (dest_order.get(p["firstProDest"], 5), p["name"]))

output = {"players": result_players}

with open(OUTPUT_FILE, "w") as f:
    json.dump(output, f, separators=(",", ":"))

file_size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
print(f"Wrote {OUTPUT_FILE} ({file_size_mb:.1f} MB, {len(result_players)} players)")

# Print summary
from collections import Counter
dest_counts = Counter(p["firstProDest"] for p in result_players)
print("\nBreakdown by first pro destination:")
for dest, count in sorted(dest_counts.items(), key=lambda x: dest_order.get(x[0], 5)):
    print(f"  {dest}: {count}")

season_counts = Counter(p["lastCollegeSeason"] for p in result_players)
print("\nBreakdown by last college season:")
for season, count in sorted(season_counts.items()):
    print(f"  {season}: {count}")
