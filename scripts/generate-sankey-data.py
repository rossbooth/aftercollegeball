#!/usr/bin/env python3
"""
Generate Sankey diagram data and FAQ data from D1 basketball outcomes database.
Outputs JSON files to website/public/data/
"""

import sqlite3
import json
import os
from collections import defaultdict

DB_PATH = "/Users/rjb/Desktop/Hoop Research/d1-basketball-outcomes/data/d1_basketball.db"
OUTPUT_DIR = "/Users/rjb/Desktop/Hoop Research/d1-basketball-outcomes/website/public/data/"

os.makedirs(OUTPUT_DIR, exist_ok=True)

db = sqlite3.connect(DB_PATH)
db.row_factory = sqlite3.Row
cur = db.cursor()

# ===========================================================================
# European team keywords for classification
# ===========================================================================
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

# Lowercase versions for matching
EUROPEAN_KEYWORDS_LOWER = [kw.lower() for kw in EUROPEAN_KEYWORDS]


def is_european_team(team_name):
    """Check if a team name matches any European keyword (case-insensitive substring)."""
    team_lower = team_name.lower()
    for kw in EUROPEAN_KEYWORDS_LOWER:
        if kw in team_lower:
            return True
    return False


def classify_international_player(player_intl_seasons):
    """
    Given a player's international seasons (sorted chronologically),
    check their FIRST international season's teams. If ANY team matches
    a European keyword, classify as 'europe'. Otherwise 'other_intl'.
    """
    if not player_intl_seasons:
        return "other_intl"
    first_intl = player_intl_seasons[0]
    teams = first_intl.get("teams", [])
    for team in teams:
        if isinstance(team, str) and is_european_team(team):
            return "europe"
    return "other_intl"


# ===========================================================================
# Step 1: Load all players who have at least one NCAA season
# ===========================================================================
print("=" * 60)
print("LOADING DATA")
print("=" * 60)

# Get all timeline rows, grouped by player
cur.execute("""
    SELECT t.realgm_id, t.season, t.level, t.section_types, t.stats, t.teams,
           p.name, p.ht, p.school, p.pos
    FROM realgm_timeline t
    JOIN realgm_players p ON t.realgm_id = p.realgm_id
    ORDER BY t.realgm_id, t.season
""")

players = defaultdict(lambda: {"seasons": [], "name": "", "ht": "", "school": "", "pos": ""})
for row in cur:
    pid = row["realgm_id"]
    players[pid]["name"] = row["name"]
    players[pid]["ht"] = row["ht"]
    players[pid]["school"] = row["school"]
    players[pid]["pos"] = row["pos"]
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

print(f"Total players in DB: {len(players)}")

# ===========================================================================
# Step 2: Filter to players with NCAA seasons, find last NCAA season
# ===========================================================================

def season_sort_key(s):
    """Convert '2015-2016' to 2015 for sorting."""
    return int(s.split("-")[0])

def has_real_nba_season(section_types):
    """Check if section_types contains 'NBA Season Stats'."""
    return "NBA Season Stats" in section_types

# Players whose last NCAA season ended between 2014-2015 and 2024-2025
# (i.e., they left college in the window 2015-2025)
MIN_LAST_NCAA = "2014-2015"
MAX_LAST_NCAA = "2024-2025"
STILL_IN_COLLEGE = "2025-2026"

classified = []  # List of dicts with classification info

for pid, pdata in players.items():
    ncaa_seasons = [s for s in pdata["seasons"] if s["level"] == "ncaa"]
    if not ncaa_seasons:
        continue

    # Find last NCAA season
    last_ncaa = max(ncaa_seasons, key=lambda s: season_sort_key(s["season"]))
    last_ncaa_season = last_ncaa["season"]

    # Skip if still in college
    if last_ncaa_season == STILL_IN_COLLEGE:
        continue

    # Filter to our window
    if season_sort_key(last_ncaa_season) < season_sort_key(MIN_LAST_NCAA):
        continue
    if season_sort_key(last_ncaa_season) > season_sort_key(MAX_LAST_NCAA):
        continue

    # Get post-college seasons (after last NCAA season)
    last_ncaa_year = season_sort_key(last_ncaa_season)
    post_college = sorted(
        [s for s in pdata["seasons"] if season_sort_key(s["season"]) > last_ncaa_year],
        key=lambda s: season_sort_key(s["season"])
    )

    # Pro levels we care about
    pro_levels = {"nba", "g_league", "international"}

    # Find all pro seasons
    pro_seasons = [s for s in post_college if s["level"] in pro_levels]

    # For NBA classification: only count seasons with real NBA Season Stats
    def is_real_nba(s):
        return s["level"] == "nba" and has_real_nba_season(s["section_types"])

    # Determine first pro destination
    first_pro = None
    for s in pro_seasons:
        if s["level"] == "nba":
            if has_real_nba_season(s["section_types"]):
                first_pro = "nba"
                break
            # else skip this NBA season (just transactions/preseason/summer league)
            continue
        elif s["level"] == "g_league":
            first_pro = "g_league"
            break
        elif s["level"] == "international":
            first_pro = "international"
            break

    if first_pro is None:
        first_pro = "no_pro"

    # Get last NCAA stats
    last_ncaa_stats = last_ncaa.get("stats", {}).get("NCAA Season Stats", {})

    # Count pro seasons by type
    nba_real_seasons = [s for s in pro_seasons if is_real_nba(s)]
    gleague_seasons = [s for s in pro_seasons if s["level"] == "g_league"]
    intl_seasons = sorted(
        [s for s in pro_seasons if s["level"] == "international"],
        key=lambda s: season_sort_key(s["season"])
    )

    # For international players, sub-classify as europe or other_intl
    intl_subtype = None
    if first_pro == "international":
        intl_subtype = classify_international_player(intl_seasons)

    classified.append({
        "pid": pid,
        "name": pdata["name"],
        "ht": pdata["ht"],
        "school": pdata["school"],
        "pos": pdata["pos"],
        "last_ncaa_season": last_ncaa_season,
        "last_ncaa_stats": last_ncaa_stats,
        "first_pro": first_pro,
        "intl_subtype": intl_subtype,  # "europe" or "other_intl" if first_pro == "international"
        "pro_seasons": pro_seasons,
        "nba_real_count": len(nba_real_seasons),
        "gleague_count": len(gleague_seasons),
        "intl_count": len(intl_seasons),
        "all_post_college": post_college,
        "nba_real_seasons": nba_real_seasons,
        "gleague_seasons": gleague_seasons,
        "intl_seasons": intl_seasons,
    })

print(f"Players with NCAA who left college 2015-2025: {len(classified)}")

# ===========================================================================
# Step 3: Level 1 classification counts
# ===========================================================================
# Split international into europe and other_intl
buckets = defaultdict(list)
for p in classified:
    if p["first_pro"] == "international":
        buckets[p["intl_subtype"]].append(p)
    else:
        buckets[p["first_pro"]].append(p)

total = len(classified)
nba_count = len(buckets["nba"])
gl_count = len(buckets["g_league"])
europe_count = len(buckets["europe"])
other_intl_count = len(buckets["other_intl"])
nopro_count = len(buckets["no_pro"])

print(f"\n{'Level 1 Breakdown':=^60}")
print(f"  NBA:                {nba_count:>6}  ({nba_count/total*100:.1f}%)")
print(f"  NBA G-League:       {gl_count:>6}  ({gl_count/total*100:.1f}%)")
print(f"  Europe:             {europe_count:>6}  ({europe_count/total*100:.1f}%)")
print(f"  Other International:{other_intl_count:>6}  ({other_intl_count/total*100:.1f}%)")
print(f"  No Pro Career:      {nopro_count:>6}  ({nopro_count/total*100:.1f}%)")
print(f"  TOTAL:              {total:>6}")

# ===========================================================================
# Step 4: Generate sankey-level1.json
# ===========================================================================
sankey_level1 = {
    "nodes": [
        {"id": "all", "label": f"All D1 Players (2015-2025)", "count": total},
        {"id": "nba", "label": "NBA", "count": nba_count, "pct": f"{nba_count/total*100:.1f}%"},
        {"id": "gleague", "label": "NBA G-League", "count": gl_count, "pct": f"{gl_count/total*100:.1f}%"},
        {"id": "europe", "label": "Europe", "count": europe_count, "pct": f"{europe_count/total*100:.1f}%"},
        {"id": "other_intl", "label": "Other International", "count": other_intl_count, "pct": f"{other_intl_count/total*100:.1f}%"},
        {"id": "nopro", "label": "No Pro Career", "count": nopro_count, "pct": f"{nopro_count/total*100:.1f}%"},
    ],
    "links": [
        {"source": "all", "target": "nba", "value": nba_count},
        {"source": "all", "target": "gleague", "value": gl_count},
        {"source": "all", "target": "europe", "value": europe_count},
        {"source": "all", "target": "other_intl", "value": other_intl_count},
        {"source": "all", "target": "nopro", "value": nopro_count},
    ],
}

with open(os.path.join(OUTPUT_DIR, "sankey-level1.json"), "w") as f:
    json.dump(sankey_level1, f, indent=2)
print("\nWrote sankey-level1.json")

# ===========================================================================
# Step 5: NBA Level 2 - Sub-classify NBA-first players
# ===========================================================================
print(f"\n{'NBA Level 2':=^60}")

nba_sub = defaultdict(list)
for p in buckets["nba"]:
    nba_years = p["nba_real_count"]

    # Check if they transitioned to international after NBA
    # Find the last NBA real season year
    if p["nba_real_seasons"]:
        last_nba_year = max(season_sort_key(s["season"]) for s in p["nba_real_seasons"])
    else:
        last_nba_year = 0

    has_intl_after = any(
        s["level"] == "international" and season_sort_key(s["season"]) > last_nba_year
        for s in p["pro_seasons"]
    )
    has_gl_after = any(
        s["level"] == "g_league" and season_sort_key(s["season"]) > last_nba_year
        for s in p["pro_seasons"]
    )

    if nba_years >= 5:
        nba_sub["nba_long"].append(p)
    elif has_intl_after:
        nba_sub["nba_to_intl"].append(p)
    elif has_gl_after:
        nba_sub["nba_to_gl"].append(p)
    else:
        nba_sub["nba_left"].append(p)

for k, v in nba_sub.items():
    print(f"  {k}: {len(v)}")

sankey_nba = {
    "nodes": [
        {"id": "nba_all", "label": "NBA Players", "count": nba_count},
        {"id": "nba_long", "label": "Long NBA Career (5+ Years)", "count": len(nba_sub["nba_long"]),
         "pct": f"{len(nba_sub['nba_long'])/nba_count*100:.1f}%"},
        {"id": "nba_to_intl", "label": "Transitioned to International", "count": len(nba_sub["nba_to_intl"]),
         "pct": f"{len(nba_sub['nba_to_intl'])/nba_count*100:.1f}%"},
        {"id": "nba_to_gl", "label": "Transitioned to G-League", "count": len(nba_sub["nba_to_gl"]),
         "pct": f"{len(nba_sub['nba_to_gl'])/nba_count*100:.1f}%"},
        {"id": "nba_left", "label": "Left Pro Basketball (<5 Years)", "count": len(nba_sub["nba_left"]),
         "pct": f"{len(nba_sub['nba_left'])/nba_count*100:.1f}%"},
    ],
    "links": [
        {"source": "nba_all", "target": "nba_long", "value": len(nba_sub["nba_long"])},
        {"source": "nba_all", "target": "nba_to_intl", "value": len(nba_sub["nba_to_intl"])},
        {"source": "nba_all", "target": "nba_to_gl", "value": len(nba_sub["nba_to_gl"])},
        {"source": "nba_all", "target": "nba_left", "value": len(nba_sub["nba_left"])},
    ],
}

with open(os.path.join(OUTPUT_DIR, "sankey-nba.json"), "w") as f:
    json.dump(sankey_nba, f, indent=2)
print("Wrote sankey-nba.json")

# ===========================================================================
# Step 6: G-League Level 2
# ===========================================================================
print(f"\n{'G-League Level 2':=^60}")

gl_sub = defaultdict(list)
for p in buckets["g_league"]:
    first_gl_year = season_sort_key(p["gleague_seasons"][0]["season"]) if p["gleague_seasons"] else 9999

    # Did they later make NBA (real seasons)?
    has_nba_later = any(
        s["level"] == "nba" and has_real_nba_season(s["section_types"])
        for s in p["pro_seasons"]
        if season_sort_key(s["season"]) > first_gl_year
    )
    has_intl_later = any(
        s["level"] == "international"
        for s in p["pro_seasons"]
        if season_sort_key(s["season"]) > first_gl_year
    )

    if has_nba_later:
        gl_sub["gl_to_nba"].append(p)
    elif has_intl_later:
        gl_sub["gl_to_intl"].append(p)
    elif p["gleague_count"] >= 3:
        gl_sub["gl_long"].append(p)
    else:
        gl_sub["gl_left"].append(p)

for k, v in gl_sub.items():
    print(f"  {k}: {len(v)}")

sankey_gleague = {
    "nodes": [
        {"id": "gl_all", "label": "NBA G-League Players", "count": gl_count},
        {"id": "gl_to_nba", "label": "Made it to NBA", "count": len(gl_sub["gl_to_nba"]),
         "pct": f"{len(gl_sub['gl_to_nba'])/gl_count*100:.1f}%" if gl_count > 0 else "0%"},
        {"id": "gl_to_intl", "label": "Went International", "count": len(gl_sub["gl_to_intl"]),
         "pct": f"{len(gl_sub['gl_to_intl'])/gl_count*100:.1f}%" if gl_count > 0 else "0%"},
        {"id": "gl_long", "label": "Long G-League Career (3+ Years)", "count": len(gl_sub["gl_long"]),
         "pct": f"{len(gl_sub['gl_long'])/gl_count*100:.1f}%" if gl_count > 0 else "0%"},
        {"id": "gl_left", "label": "Left Pro Basketball", "count": len(gl_sub["gl_left"]),
         "pct": f"{len(gl_sub['gl_left'])/gl_count*100:.1f}%" if gl_count > 0 else "0%"},
    ],
    "links": [
        {"source": "gl_all", "target": "gl_to_nba", "value": len(gl_sub["gl_to_nba"])},
        {"source": "gl_all", "target": "gl_to_intl", "value": len(gl_sub["gl_to_intl"])},
        {"source": "gl_all", "target": "gl_long", "value": len(gl_sub["gl_long"])},
        {"source": "gl_all", "target": "gl_left", "value": len(gl_sub["gl_left"])},
    ],
}

with open(os.path.join(OUTPUT_DIR, "sankey-gleague.json"), "w") as f:
    json.dump(sankey_gleague, f, indent=2)
print("Wrote sankey-gleague.json")

# ===========================================================================
# Step 7: Europe Level 2
# ===========================================================================
print(f"\n{'Europe Level 2':=^60}")

europe_sub = defaultdict(list)
for p in buckets["europe"]:
    first_intl_year = season_sort_key(p["intl_seasons"][0]["season"]) if p["intl_seasons"] else 9999

    has_nba_later = any(
        s["level"] == "nba" and has_real_nba_season(s["section_types"])
        for s in p["pro_seasons"]
        if season_sort_key(s["season"]) > first_intl_year
    )
    has_gl_later = any(
        s["level"] == "g_league"
        for s in p["pro_seasons"]
        if season_sort_key(s["season"]) > first_intl_year
    )

    # Check if they later played for non-European international teams
    has_other_intl_later = False
    for s in p["intl_seasons"]:
        if season_sort_key(s["season"]) > first_intl_year:
            for team in s.get("teams", []):
                if isinstance(team, str) and not is_european_team(team):
                    has_other_intl_later = True
                    break
        if has_other_intl_later:
            break

    if has_nba_later:
        europe_sub["eu_to_nba"].append(p)
    elif has_gl_later:
        europe_sub["eu_to_gl"].append(p)
    elif has_other_intl_later:
        europe_sub["eu_to_other_intl"].append(p)
    elif p["intl_count"] >= 5:
        europe_sub["eu_long"].append(p)
    else:
        europe_sub["eu_left"].append(p)

for k, v in europe_sub.items():
    print(f"  {k}: {len(v)}")

sankey_europe = {
    "nodes": [
        {"id": "eu_all", "label": "Europe Players", "count": europe_count},
        {"id": "eu_to_nba", "label": "Made it to NBA", "count": len(europe_sub["eu_to_nba"]),
         "pct": f"{len(europe_sub['eu_to_nba'])/europe_count*100:.1f}%" if europe_count > 0 else "0%"},
        {"id": "eu_to_gl", "label": "Came to G-League", "count": len(europe_sub["eu_to_gl"]),
         "pct": f"{len(europe_sub['eu_to_gl'])/europe_count*100:.1f}%" if europe_count > 0 else "0%"},
        {"id": "eu_to_other_intl", "label": "Went to Other International League", "count": len(europe_sub["eu_to_other_intl"]),
         "pct": f"{len(europe_sub['eu_to_other_intl'])/europe_count*100:.1f}%" if europe_count > 0 else "0%"},
        {"id": "eu_long", "label": "Long European Career (5+ Years)", "count": len(europe_sub["eu_long"]),
         "pct": f"{len(europe_sub['eu_long'])/europe_count*100:.1f}%" if europe_count > 0 else "0%"},
        {"id": "eu_left", "label": "Left Pro Basketball", "count": len(europe_sub["eu_left"]),
         "pct": f"{len(europe_sub['eu_left'])/europe_count*100:.1f}%" if europe_count > 0 else "0%"},
    ],
    "links": [
        {"source": "eu_all", "target": "eu_to_nba", "value": len(europe_sub["eu_to_nba"])},
        {"source": "eu_all", "target": "eu_to_gl", "value": len(europe_sub["eu_to_gl"])},
        {"source": "eu_all", "target": "eu_to_other_intl", "value": len(europe_sub["eu_to_other_intl"])},
        {"source": "eu_all", "target": "eu_long", "value": len(europe_sub["eu_long"])},
        {"source": "eu_all", "target": "eu_left", "value": len(europe_sub["eu_left"])},
    ],
}

with open(os.path.join(OUTPUT_DIR, "sankey-europe.json"), "w") as f:
    json.dump(sankey_europe, f, indent=2)
print("Wrote sankey-europe.json")

# ===========================================================================
# Step 8: Other International Level 2
# ===========================================================================
print(f"\n{'Other International Level 2':=^60}")

other_intl_sub = defaultdict(list)
for p in buckets["other_intl"]:
    first_intl_year = season_sort_key(p["intl_seasons"][0]["season"]) if p["intl_seasons"] else 9999

    has_nba_later = any(
        s["level"] == "nba" and has_real_nba_season(s["section_types"])
        for s in p["pro_seasons"]
        if season_sort_key(s["season"]) > first_intl_year
    )
    has_gl_later = any(
        s["level"] == "g_league"
        for s in p["pro_seasons"]
        if season_sort_key(s["season"]) > first_intl_year
    )

    # Check if they later played for European international teams
    has_europe_later = False
    for s in p["intl_seasons"]:
        if season_sort_key(s["season"]) > first_intl_year:
            for team in s.get("teams", []):
                if isinstance(team, str) and is_european_team(team):
                    has_europe_later = True
                    break
        if has_europe_later:
            break

    if has_nba_later:
        other_intl_sub["oi_to_nba"].append(p)
    elif has_gl_later:
        other_intl_sub["oi_to_gl"].append(p)
    elif has_europe_later:
        other_intl_sub["oi_to_europe"].append(p)
    elif p["intl_count"] >= 5:
        other_intl_sub["oi_long"].append(p)
    else:
        other_intl_sub["oi_left"].append(p)

for k, v in other_intl_sub.items():
    print(f"  {k}: {len(v)}")

sankey_other_intl = {
    "nodes": [
        {"id": "oi_all", "label": "Other International Players", "count": other_intl_count},
        {"id": "oi_to_nba", "label": "Made it to NBA", "count": len(other_intl_sub["oi_to_nba"]),
         "pct": f"{len(other_intl_sub['oi_to_nba'])/other_intl_count*100:.1f}%" if other_intl_count > 0 else "0%"},
        {"id": "oi_to_gl", "label": "Came to G-League", "count": len(other_intl_sub["oi_to_gl"]),
         "pct": f"{len(other_intl_sub['oi_to_gl'])/other_intl_count*100:.1f}%" if other_intl_count > 0 else "0%"},
        {"id": "oi_to_europe", "label": "Went to Europe", "count": len(other_intl_sub["oi_to_europe"]),
         "pct": f"{len(other_intl_sub['oi_to_europe'])/other_intl_count*100:.1f}%" if other_intl_count > 0 else "0%"},
        {"id": "oi_long", "label": "Long International Career (5+ Years)", "count": len(other_intl_sub["oi_long"]),
         "pct": f"{len(other_intl_sub['oi_long'])/other_intl_count*100:.1f}%" if other_intl_count > 0 else "0%"},
        {"id": "oi_left", "label": "Left Pro Basketball", "count": len(other_intl_sub["oi_left"]),
         "pct": f"{len(other_intl_sub['oi_left'])/other_intl_count*100:.1f}%" if other_intl_count > 0 else "0%"},
    ],
    "links": [
        {"source": "oi_all", "target": "oi_to_nba", "value": len(other_intl_sub["oi_to_nba"])},
        {"source": "oi_all", "target": "oi_to_gl", "value": len(other_intl_sub["oi_to_gl"])},
        {"source": "oi_all", "target": "oi_to_europe", "value": len(other_intl_sub["oi_to_europe"])},
        {"source": "oi_all", "target": "oi_long", "value": len(other_intl_sub["oi_long"])},
        {"source": "oi_all", "target": "oi_left", "value": len(other_intl_sub["oi_left"])},
    ],
}

with open(os.path.join(OUTPUT_DIR, "sankey-other-intl.json"), "w") as f:
    json.dump(sankey_other_intl, f, indent=2)
print("Wrote sankey-other-intl.json")

# ===========================================================================
# Step 9: Example players
# ===========================================================================
print(f"\n{'Example Players':=^60}")

def pick_examples(player_list, n=5):
    """Pick recognizable players - sort by college PPG descending, prefer known schools."""
    big_schools = {
        "Duke", "Kentucky", "North Carolina", "Kansas", "UCLA", "Michigan State",
        "Gonzaga", "Villanova", "Arizona", "Louisville", "Indiana", "Syracuse",
        "Connecticut", "Florida", "Virginia", "Michigan", "Oregon", "Texas",
        "Baylor", "Tennessee", "Alabama", "Auburn", "Ohio State", "Purdue",
        "Wisconsin", "Iowa", "Creighton", "Marquette", "Georgetown", "Houston",
    }

    def score(p):
        ppg = 0
        try:
            ppg = float(p["last_ncaa_stats"].get("PPG", 0))
        except (ValueError, TypeError):
            pass
        school_bonus = 10 if p["school"] in big_schools else 0
        return ppg + school_bonus

    sorted_players = sorted(player_list, key=score, reverse=True)
    return [p["name"] for p in sorted_players[:n]]

example_players = {
    "nba": pick_examples(buckets["nba"]),
    "gleague": pick_examples(buckets["g_league"]),
    "europe": pick_examples(buckets["europe"]),
    "other_intl": pick_examples(buckets["other_intl"]),
    "nopro": pick_examples(buckets["no_pro"]),
    "nba_long": pick_examples(nba_sub.get("nba_long", [])),
    "nba_to_intl": pick_examples(nba_sub.get("nba_to_intl", [])),
    "nba_to_gl": pick_examples(nba_sub.get("nba_to_gl", [])),
    "nba_left": pick_examples(nba_sub.get("nba_left", [])),
    "gl_to_nba": pick_examples(gl_sub.get("gl_to_nba", [])),
    "gl_to_intl": pick_examples(gl_sub.get("gl_to_intl", [])),
    "gl_long": pick_examples(gl_sub.get("gl_long", [])),
    "gl_left": pick_examples(gl_sub.get("gl_left", [])),
    "eu_to_nba": pick_examples(europe_sub.get("eu_to_nba", [])),
    "eu_to_gl": pick_examples(europe_sub.get("eu_to_gl", [])),
    "eu_to_other_intl": pick_examples(europe_sub.get("eu_to_other_intl", [])),
    "eu_long": pick_examples(europe_sub.get("eu_long", [])),
    "eu_left": pick_examples(europe_sub.get("eu_left", [])),
    "oi_to_nba": pick_examples(other_intl_sub.get("oi_to_nba", [])),
    "oi_to_gl": pick_examples(other_intl_sub.get("oi_to_gl", [])),
    "oi_to_europe": pick_examples(other_intl_sub.get("oi_to_europe", [])),
    "oi_long": pick_examples(other_intl_sub.get("oi_long", [])),
    "oi_left": pick_examples(other_intl_sub.get("oi_left", [])),
}

for k, v in example_players.items():
    print(f"  {k}: {v}")

with open(os.path.join(OUTPUT_DIR, "example-players.json"), "w") as f:
    json.dump(example_players, f, indent=2)
print("Wrote example-players.json")

# ===========================================================================
# Step 10: FAQ data
# ===========================================================================
print(f"\n{'FAQ Data':=^60}")

def avg_stat(player_list, stat_key):
    """Average of a stat from last NCAA season."""
    vals = []
    for p in player_list:
        v = p["last_ncaa_stats"].get(stat_key)
        if v is not None:
            try:
                vals.append(float(v))
            except (ValueError, TypeError):
                pass
    return round(sum(vals) / len(vals), 1) if vals else 0.0

def parse_height_inches(ht_str):
    """Convert '6-10' to 82 inches."""
    if not ht_str or "-" not in ht_str:
        return None
    try:
        parts = ht_str.split("-")
        return int(parts[0]) * 12 + int(parts[1])
    except (ValueError, IndexError):
        return None

def avg_height(player_list):
    """Average height in feet-inches format."""
    vals = []
    for p in player_list:
        inches = parse_height_inches(p["ht"])
        if inches:
            vals.append(inches)
    if not vals:
        return "N/A"
    avg_in = sum(vals) / len(vals)
    ft = int(avg_in // 12)
    remaining = round(avg_in % 12, 1)
    return f"{ft}-{remaining:.0f}"

def avg_pro_career_length(player_list):
    """Average number of pro seasons."""
    vals = []
    for p in player_list:
        pro_count = len(p["pro_seasons"])
        vals.append(pro_count)
    return round(sum(vals) / len(vals), 1) if vals else 0.0

# Compute stats for each bucket
ppg_nba = avg_stat(buckets["nba"], "PPG")
ppg_gl = avg_stat(buckets["g_league"], "PPG")
ppg_europe = avg_stat(buckets["europe"], "PPG")
ppg_other_intl = avg_stat(buckets["other_intl"], "PPG")
ppg_nopro = avg_stat(buckets["no_pro"], "PPG")

rpg_nba = avg_stat(buckets["nba"], "RPG")
rpg_gl = avg_stat(buckets["g_league"], "RPG")
rpg_europe = avg_stat(buckets["europe"], "RPG")
rpg_other_intl = avg_stat(buckets["other_intl"], "RPG")
rpg_nopro = avg_stat(buckets["no_pro"], "RPG")

apg_nba = avg_stat(buckets["nba"], "APG")
apg_gl = avg_stat(buckets["g_league"], "APG")
apg_europe = avg_stat(buckets["europe"], "APG")
apg_other_intl = avg_stat(buckets["other_intl"], "APG")
apg_nopro = avg_stat(buckets["no_pro"], "APG")

ht_nba = avg_height(buckets["nba"])
ht_gl = avg_height(buckets["g_league"])
ht_europe = avg_height(buckets["europe"])
ht_other_intl = avg_height(buckets["other_intl"])
ht_nopro = avg_height(buckets["no_pro"])

career_nba = avg_pro_career_length(buckets["nba"])
career_gl = avg_pro_career_length(buckets["g_league"])
career_europe = avg_pro_career_length(buckets["europe"])
career_other_intl = avg_pro_career_length(buckets["other_intl"])

# Most common schools for NBA
nba_schools = defaultdict(int)
for p in buckets["nba"]:
    if p["school"]:
        nba_schools[p["school"]] += 1
top_nba_schools = sorted(nba_schools.items(), key=lambda x: -x[1])[:10]

# Most common schools for G-League
gl_schools = defaultdict(int)
for p in buckets["g_league"]:
    if p["school"]:
        gl_schools[p["school"]] += 1
top_gl_schools = sorted(gl_schools.items(), key=lambda x: -x[1])[:10]

# Most common schools for Europe
europe_schools = defaultdict(int)
for p in buckets["europe"]:
    if p["school"]:
        europe_schools[p["school"]] += 1
top_europe_schools = sorted(europe_schools.items(), key=lambda x: -x[1])[:10]

# Most common schools for Other International
other_intl_schools = defaultdict(int)
for p in buckets["other_intl"]:
    if p["school"]:
        other_intl_schools[p["school"]] += 1
top_other_intl_schools = sorted(other_intl_schools.items(), key=lambda x: -x[1])[:10]

# Transition counts
nba_to_intl_count = len(nba_sub.get("nba_to_intl", []))
nba_to_gl_count = len(nba_sub.get("nba_to_gl", []))
gl_to_nba_count = len(gl_sub.get("gl_to_nba", []))
gl_to_intl_count = len(gl_sub.get("gl_to_intl", []))
eu_to_nba_count = len(europe_sub.get("eu_to_nba", []))
eu_to_gl_count = len(europe_sub.get("eu_to_gl", []))
eu_to_other_intl_count = len(europe_sub.get("eu_to_other_intl", []))
oi_to_nba_count = len(other_intl_sub.get("oi_to_nba", []))
oi_to_gl_count = len(other_intl_sub.get("oi_to_gl", []))
oi_to_europe_count = len(other_intl_sub.get("oi_to_europe", []))

# Position breakdown for NBA
nba_positions = defaultdict(int)
for p in buckets["nba"]:
    if p["pos"]:
        nba_positions[p["pos"]] += 1
pos_sorted = sorted(nba_positions.items(), key=lambda x: -x[1])

# Average stats for NBA long career vs short
ppg_nba_long = avg_stat(nba_sub.get("nba_long", []), "PPG")
ppg_nba_left = avg_stat(nba_sub.get("nba_left", []), "PPG")

# Class year analysis
def count_ncaa_years(p):
    return len([s for s in players[p["pid"]]["seasons"] if s["level"] == "ncaa"])

ncaa_years_nba = [count_ncaa_years(p) for p in buckets["nba"]]
ncaa_years_nopro = [count_ncaa_years(p) for p in buckets["no_pro"]]
avg_ncaa_nba = round(sum(ncaa_years_nba) / len(ncaa_years_nba), 1) if ncaa_years_nba else 0
avg_ncaa_nopro = round(sum(ncaa_years_nopro) / len(ncaa_years_nopro), 1) if ncaa_years_nopro else 0

# SPG and BPG
spg_nba = avg_stat(buckets["nba"], "SPG")
spg_gl = avg_stat(buckets["g_league"], "SPG")
spg_europe = avg_stat(buckets["europe"], "SPG")
spg_other_intl = avg_stat(buckets["other_intl"], "SPG")
spg_nopro = avg_stat(buckets["no_pro"], "SPG")

bpg_nba = avg_stat(buckets["nba"], "BPG")
bpg_gl = avg_stat(buckets["g_league"], "BPG")
bpg_europe = avg_stat(buckets["europe"], "BPG")
bpg_other_intl = avg_stat(buckets["other_intl"], "BPG")
bpg_nopro = avg_stat(buckets["no_pro"], "BPG")

# Percentage who play any pro
pct_pro = round((nba_count + gl_count + europe_count + other_intl_count) / total * 100, 1)

# NBA long career college PPG vs others
ppg_nba_to_intl = avg_stat(nba_sub.get("nba_to_intl", []), "PPG")

# G-League to NBA college PPG
ppg_gl_to_nba = avg_stat(gl_sub.get("gl_to_nba", []), "PPG")

# Europe to NBA
ppg_eu_to_nba = avg_stat(europe_sub.get("eu_to_nba", []), "PPG")

# Other Intl to NBA
ppg_oi_to_nba = avg_stat(other_intl_sub.get("oi_to_nba", []), "PPG")

faqs = {
    "faqs": [
        {
            "patterns": ["ppg", "points", "scoring", "average.*nba"],
            "question": "What was the average college PPG for players who made the NBA?",
            "answer": f"Players who made the NBA averaged {ppg_nba} PPG in their final college season, compared to {ppg_gl} for NBA G-League players, {ppg_europe} for Europe players, {ppg_other_intl} for Other International players, and {ppg_nopro} for those with no pro career."
        },
        {
            "patterns": ["rebound", "rpg", "boards"],
            "question": "What was the average college RPG for each pro destination?",
            "answer": f"In their final college season, NBA players averaged {rpg_nba} RPG, NBA G-League players {rpg_gl}, Europe players {rpg_europe}, Other International players {rpg_other_intl}, and no-pro players {rpg_nopro}."
        },
        {
            "patterns": ["assist", "apg", "passing"],
            "question": "What was the average college APG for each pro destination?",
            "answer": f"In their final college season, NBA players averaged {apg_nba} APG, NBA G-League players {apg_gl}, Europe players {apg_europe}, Other International players {apg_other_intl}, and no-pro players {apg_nopro}."
        },
        {
            "patterns": ["height", "tall", "size"],
            "question": "What is the average height for each pro destination?",
            "answer": f"NBA players averaged {ht_nba}, NBA G-League players {ht_gl}, Europe players {ht_europe}, Other International players {ht_other_intl}, and no-pro players {ht_nopro}."
        },
        {
            "patterns": ["how many", "total", "count", "number.*players"],
            "question": "How many D1 players were analyzed?",
            "answer": f"We analyzed {total:,} D1 players whose last college season was between 2014-15 and 2023-24. Of these, {nba_count} ({nba_count/total*100:.1f}%) reached the NBA, {gl_count} ({gl_count/total*100:.1f}%) went to the NBA G-League, {europe_count} ({europe_count/total*100:.1f}%) played in Europe, {other_intl_count} ({other_intl_count/total*100:.1f}%) played in other international leagues, and {nopro_count} ({nopro_count/total*100:.1f}%) had no recorded pro career."
        },
        {
            "patterns": ["percent", "chance", "odds", "probability", "likelihood"],
            "question": "What percentage of D1 players go pro?",
            "answer": f"{pct_pro}% of D1 players in our dataset went on to play some form of professional basketball. Only {nba_count/total*100:.1f}% made the NBA with real regular season playing time."
        },
        {
            "patterns": ["transition", "switch", "move.*between", "nba.*international", "g.league.*nba"],
            "question": "How many players transitioned between pro levels?",
            "answer": f"Among NBA-first players: {nba_to_intl_count} transitioned to international leagues and {nba_to_gl_count} moved to the G-League. Among NBA G-League-first players: {gl_to_nba_count} made it to the NBA and {gl_to_intl_count} went international. Among Europe-first players: {eu_to_nba_count} made it to the NBA, {eu_to_gl_count} came to the G-League, and {eu_to_other_intl_count} went to other international leagues. Among Other International-first players: {oi_to_nba_count} made it to the NBA, {oi_to_gl_count} came to the G-League, and {oi_to_europe_count} went to Europe."
        },
        {
            "patterns": ["school", "college", "university", "produce", "most nba"],
            "question": "Which schools produce the most NBA players?",
            "answer": f"The top NBA-producing schools (2015-2025): {', '.join(f'{s} ({c})' for s, c in top_nba_schools[:5])}."
        },
        {
            "patterns": ["career.*length", "how long", "years.*pro", "duration"],
            "question": "What is the average pro career length by destination?",
            "answer": f"NBA-first players averaged {career_nba} pro seasons, NBA G-League-first players averaged {career_gl} pro seasons, Europe-first players averaged {career_europe} pro seasons, and Other International-first players averaged {career_other_intl} pro seasons."
        },
        {
            "patterns": ["long.*nba", "5.*year", "sustained", "lasting"],
            "question": "What percentage of NBA players have long careers (5+ years)?",
            "answer": f"Of {nba_count} players who reached the NBA, {len(nba_sub.get('nba_long', []))} ({len(nba_sub.get('nba_long', []))/nba_count*100:.1f}%) had careers of 5 or more seasons. These long-career players averaged {ppg_nba_long} PPG in their final college season, vs {ppg_nba_left} for those who left the NBA in under 5 years."
        },
        {
            "patterns": ["g.league.*nba", "made.*nba.*g.league", "g.league.*path"],
            "question": "How many NBA G-League players eventually made the NBA?",
            "answer": f"Of {gl_count} players whose first pro destination was the NBA G-League, {gl_to_nba_count} ({gl_to_nba_count/gl_count*100:.1f}% if gl_count > 0 else 0) eventually earned real NBA playing time. These players averaged {ppg_gl_to_nba} PPG in their final college season."
        },
        {
            "patterns": ["europe.*nba", "european.*nba"],
            "question": "How many European players eventually made the NBA?",
            "answer": f"Of {europe_count} players who first went to Europe, {eu_to_nba_count} ({eu_to_nba_count/europe_count*100:.1f}%) eventually made it to the NBA. They averaged {ppg_eu_to_nba} PPG in their final college season."
        },
        {
            "patterns": ["other.*international.*nba", "overseas.*nba", "foreign.*nba"],
            "question": "How many Other International players eventually made the NBA?",
            "answer": f"Of {other_intl_count} players who first went to other international leagues (non-Europe), {oi_to_nba_count} ({oi_to_nba_count/other_intl_count*100:.1f}%) eventually made it to the NBA. They averaged {ppg_oi_to_nba} PPG in their final college season."
        },
        {
            "patterns": ["position", "guard", "forward", "center", "pos"],
            "question": "What positions are most common among NBA players?",
            "answer": f"Position breakdown for NBA players: {', '.join(f'{p}: {c} ({c/nba_count*100:.1f}%)' for p, c in pos_sorted)}."
        },
        {
            "patterns": ["steal", "spg", "defensive"],
            "question": "What were the average steals per game in college by pro destination?",
            "answer": f"NBA players averaged {spg_nba} SPG in their final college season, NBA G-League {spg_gl}, Europe {spg_europe}, Other International {spg_other_intl}, and no-pro {spg_nopro}."
        },
        {
            "patterns": ["block", "bpg", "shot.block"],
            "question": "What were the average blocks per game in college by pro destination?",
            "answer": f"NBA players averaged {bpg_nba} BPG in their final college season, NBA G-League {bpg_gl}, Europe {bpg_europe}, Other International {bpg_other_intl}, and no-pro {bpg_nopro}."
        },
        {
            "patterns": ["college.*years", "how.*long.*college", "ncaa.*seasons"],
            "question": "How many years did NBA players spend in college on average?",
            "answer": f"NBA players averaged {avg_ncaa_nba} NCAA seasons before going pro, compared to {avg_ncaa_nopro} for players with no pro career."
        },
        {
            "patterns": ["school.*g.league", "g.league.*school", "college.*g.league"],
            "question": "Which schools produce the most NBA G-League players?",
            "answer": f"Top NBA G-League-producing schools: {', '.join(f'{s} ({c})' for s, c in top_gl_schools[:5])}."
        },
        {
            "patterns": ["school.*europe", "europe.*school", "college.*europe"],
            "question": "Which schools produce the most Europe-bound players?",
            "answer": f"Top Europe-producing schools: {', '.join(f'{s} ({c})' for s, c in top_europe_schools[:5])}."
        },
        {
            "patterns": ["school.*international", "international.*school", "overseas.*school"],
            "question": "Which schools produce the most Other International players?",
            "answer": f"Top Other International-producing schools: {', '.join(f'{s} ({c})' for s, c in top_other_intl_schools[:5])}."
        },
        {
            "patterns": ["no.*pro", "didn.*make", "never.*pro", "end.*career"],
            "question": "What are the stats of players who never went pro?",
            "answer": f"Players with no recorded pro career averaged {ppg_nopro} PPG, {rpg_nopro} RPG, {apg_nopro} APG in their final college season. Their average height was {ht_nopro}. This group represents {nopro_count/total*100:.1f}% of all D1 players."
        },
        {
            "patterns": ["nba.*left", "short.*nba", "brief.*nba", "wash.*out"],
            "question": "What happens to NBA players who don't last 5 years?",
            "answer": f"Of NBA players with shorter careers (<5 years): {nba_to_intl_count} transitioned to international basketball, {nba_to_gl_count} moved to the NBA G-League, and {len(nba_sub.get('nba_left', []))} left professional basketball entirely."
        },
        {
            "patterns": ["europe.*long", "european.*career", "europe.*5"],
            "question": "How many Europe players had long careers?",
            "answer": f"Of {europe_count} Europe-first players, {len(europe_sub.get('eu_long', []))} ({len(europe_sub.get('eu_long', []))/europe_count*100:.1f}%) had careers of 5+ international seasons, while {len(europe_sub.get('eu_left', []))} ({len(europe_sub.get('eu_left', []))/europe_count*100:.1f}%) left pro basketball relatively quickly."
        },
        {
            "patterns": ["other.*international.*long", "other.*overseas.*career"],
            "question": "How many Other International players had long careers?",
            "answer": f"Of {other_intl_count} Other International-first players, {len(other_intl_sub.get('oi_long', []))} ({len(other_intl_sub.get('oi_long', []))/other_intl_count*100:.1f}%) had careers of 5+ international seasons, while {len(other_intl_sub.get('oi_left', []))} ({len(other_intl_sub.get('oi_left', []))/other_intl_count*100:.1f}%) left pro basketball relatively quickly."
        },
    ]
}

with open(os.path.join(OUTPUT_DIR, "faq-data.json"), "w") as f:
    json.dump(faqs, f, indent=2)
print("Wrote faq-data.json")

# ===========================================================================
# Summary
# ===========================================================================
print(f"\n{'SUMMARY':=^60}")
print(f"Total D1 players analyzed: {total:,}")
print(f"  NBA:                {nba_count:>6}  ({nba_count/total*100:.1f}%)")
print(f"  NBA G-League:       {gl_count:>6}  ({gl_count/total*100:.1f}%)")
print(f"  Europe:             {europe_count:>6}  ({europe_count/total*100:.1f}%)")
print(f"  Other International:{other_intl_count:>6}  ({other_intl_count/total*100:.1f}%)")
print(f"  No Pro:             {nopro_count:>6}  ({nopro_count/total*100:.1f}%)")
print(f"\nAvg college PPG -> NBA: {ppg_nba}, G-League: {ppg_gl}, Europe: {ppg_europe}, Other Intl: {ppg_other_intl}, No Pro: {ppg_nopro}")
print(f"Avg height -> NBA: {ht_nba}, G-League: {ht_gl}, Europe: {ht_europe}, Other Intl: {ht_other_intl}, No Pro: {ht_nopro}")
print(f"\nTop NBA schools: {', '.join(f'{s} ({c})' for s, c in top_nba_schools[:5])}")
print(f"\nFiles written to: {OUTPUT_DIR}")
print("  - sankey-level1.json")
print("  - sankey-nba.json")
print("  - sankey-gleague.json")
print("  - sankey-europe.json")
print("  - sankey-other-intl.json")
print("  - example-players.json")
print("  - faq-data.json")
print("\nDone!")

db.close()
