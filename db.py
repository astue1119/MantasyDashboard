import sqlite3
from yahoo_oauth import OAuth2
from yahoo_fantasy_api import Game, League, Team
import time

def get_db():
    conn = sqlite3.connect("MantasyFootbrawl.db")
    conn.row_factory = sqlite3.Row
    return conn

def store_league(oauth, league_id):
    league = League(oauth, league_id)
    settings = league.settings()

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO leagues
        (
            league_id,
            name,
            season,
            scoring_type,
            num_teams,
            start_week,
            end_week,
            playoff_start_week,
            uses_playoff,
            uses_faab,
            waiver_type,
            trade_end_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        league_id,
        settings.get("name"),
        int(settings.get("season")),
        settings.get("scoring_type"),

        # From settings
        int(settings.get("num_teams", 0)),
        int(settings.get("start_week", 0)),
        int(settings.get("end_week", 0)),
        int(settings.get("playoff_start_week", 0)) if settings.get("playoff_start_week") else None,

        # Booleans → SQLite INTEGER
        1 if settings.get("uses_playoff") else 0,
        1 if settings.get("uses_faab") else 0,

        settings.get("waiver_type"),
        settings.get("trade_end_date")
    ))

    conn.commit()
    conn.close()

oauth = OAuth2(None, None, from_file='oauth2.json')

if not oauth.token_is_valid():
    oauth.refresh_access_token()

def store_teams(oauth, league_id):
    league = League(oauth, league_id)

    teams = league.teams()
    standings_list = league.standings()

    # Convert list → dict for fast lookup
    standings_map = {
        team["team_key"]: team
        for team in standings_list
    }

    conn = get_db()
    cur = conn.cursor()

    for team_key, team in teams.items():

        standings = standings_map.get(team_key, {})
        outcome = standings.get("outcome_totals", {})

        cur.execute("""
            INSERT OR REPLACE INTO teams (
                team_key,
                league_id,
                name,
                manager,
                number_of_moves,
                number_of_trades,
                draft_grade,
                wins,
                losses,
                ties,
                percentage,
                points_for,
                points_against,
                rank,
                clinched_playoffs,
                streak_type,
                streak_length,
                division_id,
                auction_budget_spent
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            team_key,
            league_id,
            team.get("name"),

            team["managers"][0]["manager"]["nickname"]
            if team.get("managers") else None,

            int(team.get("number_of_moves", 0)),
            int(team.get("number_of_trades", 0)),
            team.get("draft_grade"),

            int(outcome.get("wins", 0)),
            int(outcome.get("losses", 0)),
            int(outcome.get("ties", 0)),
            float(outcome.get("percentage", 0)),

            float(standings.get("points_for", 0)),
            float(standings.get("points_against", 0)),
            int(standings.get("rank", 0)),

            1 if int(standings.get("rank", 999)) <= 4 else 0,

            standings.get("streak", {}).get("type"),
            int(standings.get("streak", {}).get("value", 0)),

            int(team.get("division_id")) if team.get("division_id") else None,
            float(team.get("auction_budget_spent", 0))
        ))

    conn.commit()
    conn.close()

def store_matchups(oauth, league_id, week):
    league = League(oauth, league_id)
    data = league.matchups(week=week)

    conn = get_db()
    cur = conn.cursor()

    root = next(iter(data.values()))
    scoreboard = root["league"][1]["scoreboard"]
    matchups = scoreboard["0"]["matchups"]

    for matchup_wrapper in matchups.values():
        if not isinstance(matchup_wrapper, dict):
            continue

        matchup = matchup_wrapper["matchup"]
        teams = matchup["0"]["teams"]

        team_a = teams["0"]["team"]
        team_b = teams["1"]["team"]

        # --- Basic Info ---
        matchup_id = int(matchup.get("matchup_id", 0))
        is_playoffs = 1 if matchup.get("is_playoffs") == "1" else 0
        is_consolation = 1 if matchup.get("is_consolation") == "1" else 0

        # --- Team A ---
        team_a_key = team_a[0][0]["team_key"]
        team_a_points = float(team_a[1]["team_points"]["total"])
        team_a_proj = float(team_a[1].get("team_projected_points", {}).get("total", 0))
        team_a_win_prob = float(team_a[1].get("win_probability", 0))

        # --- Team B ---
        team_b_key = team_b[0][0]["team_key"]
        team_b_points = float(team_b[1]["team_points"]["total"])
        team_b_proj = float(team_b[1].get("team_projected_points", {}).get("total", 0))
        team_b_win_prob = float(team_b[1].get("win_probability", 0))

        # --- Winner ---
        if team_a_points > team_b_points:
            winner_team_key = team_a_key
        elif team_b_points > team_a_points:
            winner_team_key = team_b_key
        else:
            winner_team_key = None  # tie

        team_a_is_winner = 1 if winner_team_key == team_a_key else 0
        team_b_is_winner = 1 if winner_team_key == team_b_key else 0

        # --- Insert Team A Row ---
        cur.execute("""
            INSERT OR REPLACE INTO matchups
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            league_id,
            week,
            team_a_key,
            team_b_key,
            team_a_points,
            team_b_points,
            matchup_id,
            is_playoffs,
            is_consolation,
            winner_team_key,
            team_a_proj,
            team_b_proj,
            team_a_win_prob,
            team_a_is_winner
        ))

        # --- Insert Team B Row ---
        cur.execute("""
            INSERT OR REPLACE INTO matchups
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            league_id,
            week,
            team_b_key,
            team_a_key,
            team_b_points,
            team_a_points,
            matchup_id,
            is_playoffs,
            is_consolation,
            winner_team_key,
            team_b_proj,
            team_a_proj,
            team_b_win_prob,
            team_b_is_winner
        ))

    conn.commit()
    conn.close()

def store_draft_results(oauth, league_id):
    league = League(oauth, league_id)
    draft_results = league.draft_results()

    conn = get_db()
    cur = conn.cursor()

    for draft in draft_results:

        cur.execute("""
            INSERT OR REPLACE INTO draft_results (
                league_id,
                team_key,
                player_key,
                player_id,
                player_name,
                auction_cost,
                position,
                nfl_team
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            league_id,
            draft.get("team_key"),
            draft.get("player_key"),
            int(draft.get("player_id")),
            draft.get("name"),
            float(draft.get("cost", 0)) if draft.get("cost") else None,
            draft.get("position"),
            draft.get("editorial_team_abbr")
        ))

    conn.commit()
    conn.close()

def store_rosters(oauth, league_id):
    league = League(oauth, league_id)
    settings = league.settings()
    end_week = int(settings.get("end_week", 14))

    teams = league.teams()

    conn = get_db()
    cur = conn.cursor()

    for week in range(1, end_week + 1):
        print(f"Processing Week {week}")

        for team in teams.values():
            team_key = team["team_key"]

            import time
            time.sleep(0.5)
            roster = league.to_team(team_key).roster(week=week)

            for player in roster:

                player_id = int(player.get("player_id"))
                player_key = player.get("player_key")
                name = player.get("name")
                position = player.get("primary_position")
                nfl_team = player.get("editorial_team_abbr")
                selected_position = player.get("selected_position")
                eligible_positions = ",".join(player.get("eligible_positions", []))

                is_starting = 1 if selected_position not in ["BN", "IR"] else 0

                # Insert into players table if new
                cur.execute("""
                    INSERT OR IGNORE INTO players (
                        player_id,
                        player_key,
                        full_name,
                        position,
                        nfl_team
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    player_id,
                    player_key,
                    name,
                    position,
                    nfl_team
                ))

                # Insert into rosters table
                cur.execute("""
                    INSERT OR REPLACE INTO rosters (
                        league_id,
                        team_key,
                        week,
                        player_id,
                        player_key,
                        player_name,
                        selected_position,
                        eligible_positions,
                        position,
                        nfl_team,
                        is_starting
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    league_id,
                    team_key,
                    week,
                    player_id,
                    player_key,
                    name,
                    selected_position,
                    eligible_positions,
                    position,
                    nfl_team,
                    is_starting
                ))

    conn.commit()
    conn.close()

def store_weekly_points(oauth, league_id):
    from yahoo_fantasy_api import League
    import time

    league = League(oauth, league_id)
    settings = league.settings()

    season = int(settings.get("season"))
    end_week = int(settings.get("end_week", 14))

    conn = get_db()
    cur = conn.cursor()

    # ✅ Only pull players for THIS league
    cur.execute("""
        SELECT DISTINCT player_key, player_id
        FROM rosters
        WHERE league_id = ?
    """, (league_id,))
    player_rows = cur.fetchall()

    print(f"\nFound {len(player_rows)} players for league {league_id}")

    MAX_RETRIES = 5
    MICRO_SLEEP = 0.15  # small delay to reduce rate limiting

    for week in range(1, end_week + 1):
        print(f"\n========== Processing Week {week} ==========")

        for idx, (player_key, player_id) in enumerate(player_rows, start=1):

            retries = 0

            while retries < MAX_RETRIES:
                try:
                    print(f"Player {idx}/{len(player_rows)}: {player_key}")

                    # Small delay between calls
                    time.sleep(MICRO_SLEEP)

                    stats_list = league.player_stats(
                        player_id,
                        req_type="week",
                        week=week
                    )

                    # Default to 0 if no stats
                    fantasy_points = 0.0

                    if stats_list:
                        if isinstance(stats_list, list):
                            for stat_item in stats_list:
                                fantasy_points += float(
                                    stat_item.get("total_points", 0) or 0
                                )
                        else:
                            fantasy_points = float(
                                stats_list.get("total_points", 0) or 0
                            )

                    print(f"  → Fantasy Points: {fantasy_points}")

                    cur.execute("""
                        INSERT OR REPLACE INTO player_weekly_points (
                            league_id,
                            season,
                            week,
                            player_key,
                            fantasy_points
                        )
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        league_id,
                        season,
                        week,
                        player_key,
                        fantasy_points
                    ))

                    break  # Success → exit retry loop

                except Exception as e:
                    error_text = str(e)

                    # 🔥 Rate limit handling
                    if "Request denied" in error_text:
                        wait_time = 60
                        retries += 1
                        print(f"⚠️ Rate limited. Sleeping {wait_time}s (retry {retries}/{MAX_RETRIES})")
                        time.sleep(wait_time)
                    else:
                        print(f"❌ Error for {player_key}: {e}")
                        break

        conn.commit()
        print(f"✅ Week {week} committed to database")

    conn.close()
    print("\n🎉 Weekly ingestion complete.")

def store_season_stats(oauth, league_id):
    from yahoo_fantasy_api import League
    import time

    league = League(oauth, league_id)
    settings = league.settings()

    season = int(settings.get("season"))

    conn = get_db()
    cur = conn.cursor()

    # Only players from this league
    cur.execute("""
        SELECT DISTINCT player_key, player_id
        FROM rosters
        WHERE league_id = ?
    """, (league_id,))
    player_rows = cur.fetchall()

    print(f"\nFound {len(player_rows)} players for league {league_id}")

    MAX_RETRIES = 5
    MICRO_SLEEP = 0.15

    for idx, (player_key, player_id) in enumerate(player_rows, start=1):

        retries = 0

        while retries < MAX_RETRIES:
            try:
                print(f"Processing player {idx}/{len(player_rows)}: {player_key}")

                time.sleep(MICRO_SLEEP)

                stats_list = league.player_stats(
                    player_id,
                    req_type="season"
                )

                if not stats_list:
                    print("  No seasonal data")
                    break

                # Handle list response
                player_data = stats_list[0] if isinstance(stats_list, list) else stats_list

                # --- TOTALS TABLE ---
                total_points = float(player_data.get("total_points", 0) or 0)
                keeper_info = player_data.get("is_keeper") or {}
                is_keeper = 1 if keeper_info.get("kept") else 0
                print(f"Keeper raw: {player_data.get('is_keeper')}")
                print(f"Keeper parsed: {is_keeper}")

                cur.execute("""
                    INSERT OR REPLACE INTO player_season_totals (
                        league_id,
                        season,
                        player_id,
                        total_fantasy_points,
                        is_keeper
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    league_id,
                    season,
                    player_id,
                    total_points,
                    is_keeper
                ))

                # --- STAT DETAILS TABLE ---
                stats = player_data.get("stats", [])

                print(f"  → Total Points: {total_points} | Keeper: {is_keeper}")

                break  # success

            except Exception as e:
                error_text = str(e)

                if "Request denied" in error_text:
                    retries += 1
                    wait_time = 60
                    print(f"⚠️ Rate limited. Sleeping {wait_time}s (retry {retries})")
                    time.sleep(wait_time)
                else:
                    print(f"❌ Error for {player_key}: {e}")
                    break

    conn.commit()
    conn.close()

    print("\n🎉 Seasonal stats ingestion complete.")

def store_season_stat_details(oauth, league_id):
    from yahoo_fantasy_api import League
    import time

    league = League(oauth, league_id)
    settings = league.settings()

    season = int(settings.get("season"))

    conn = get_db()
    cur = conn.cursor()

    # Only players from this league
    cur.execute("""
        SELECT DISTINCT player_key, player_id
        FROM rosters
        WHERE league_id = ?
    """, (league_id,))
    player_rows = cur.fetchall()

    print(f"\nFound {len(player_rows)} players for season stat details")

    MAX_RETRIES = 5
    MICRO_SLEEP = 0.15

    # Fields that are NOT stats
    NON_STAT_FIELDS = {
        "player_id",
        "name",
        "position_type",
        "total_points"
    }

    for idx, (player_key, player_id) in enumerate(player_rows, start=1):

        retries = 0

        while retries < MAX_RETRIES:
            try:
                print(f"\nProcessing {idx}/{len(player_rows)}: {player_key}")
                time.sleep(MICRO_SLEEP)

                stats_list = league.player_stats(
                    player_id,
                    req_type="season"
                )

                if not stats_list:
                    print("  → No stats returned")
                    break

                # Handle list response
                player_data = stats_list[0] if isinstance(stats_list, list) else stats_list

                print(f"  → Keys: {list(player_data.keys())}")

                # Loop through ALL fields and treat them as stats
                for stat_name, stat_value in player_data.items():

                    if stat_name in NON_STAT_FIELDS:
                        continue

                    try:
                        stat_value = float(stat_value)
                    except:
                        continue  # skip non-numeric

                    print(f"    → {stat_name}: {stat_value}")

                    cur.execute("""
                        INSERT OR REPLACE INTO player_season_stat_details (
                            league_id,
                            season,
                            player_id,
                            stat_name,
                            stat_value
                        )
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        league_id,
                        season,
                        player_id,
                        stat_name,   # using stat_name as stat_id
                        stat_value
                    ))
                    print(f"    ✅ Inserted: {player_id} | {stat_name} | {stat_value}")
                conn.commit()
                break  # success

            except Exception as e:
                error_text = str(e)

                if "Request denied" in error_text:
                    wait_time = 60
                    retries += 1
                    print(f"⚠️ Rate limited. Sleeping {wait_time}s")
                    time.sleep(wait_time)
                else:
                    print(f"❌ Error: {e}")
                    break

    conn.close()

    print("\n🎉 Season stat details ingestion complete.")

def debug_season_stat_details(oauth, league_id):
    from yahoo_fantasy_api import League
    import time
    import json

    league = League(oauth, league_id)
    settings = league.settings()

    season = int(settings.get("season"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT player_key, player_id
        FROM rosters
        WHERE league_id = ?
        LIMIT 5
    """, (league_id,))
    player_rows = cur.fetchall()

    print(f"\nDEBUG MODE: Testing {len(player_rows)} players")

    for player_key, player_id in player_rows:
        print("\n==============================")
        print(f"Player: {player_key} (ID: {player_id})")

        try:
            stats_list = league.player_stats(player_id, req_type="season")

            print("\nRAW stats_list:")
            print(json.dumps(stats_list, indent=2))

            if not stats_list:
                print("❌ No stats_list returned")
                continue

            # Normalize structure
            player_data = stats_list[0] if isinstance(stats_list, list) else stats_list

            print("\nPLAYER DATA KEYS:")
            print(player_data.keys())

            # 🔍 Check if stats exists
            stats = player_data.get("stats")

            print("\nSTATS FIELD:")
            print(stats)

            if not stats:
                print("❌ 'stats' field is empty or missing")
                continue

            print(f"\nFound {len(stats)} stats entries")

            # Try inserting one to test DB
            sample = stats[0]
            print("\nSample stat entry:")
            print(sample)

            stat_id = sample.get("stat_id")
            stat_value = sample.get("value")

            print(f"Parsed → stat_id: {stat_id}, stat_value: {stat_value}")

        except Exception as e:
            print(f"❌ ERROR: {e}")

def backfill_player_metadata(oauth):
    from yahoo_fantasy_api import League
    import time

    conn = get_db()
    cur = conn.cursor()

    # Get one league_id per player_key (to construct API calls)
    cur.execute("""
        SELECT DISTINCT player_key, player_id, league_id
        FROM rosters
        WHERE player_key IS NOT NULL
    """)
    player_rows = cur.fetchall()

    print(f"Found {len(player_rows)} players to update")

    MICRO_SLEEP = 0.2
    MAX_RETRIES = 5

    for idx, (player_key, player_id, league_id) in enumerate(player_rows, start=1):

        retries = 0

        while retries < MAX_RETRIES:
            try:
                print(f"\n[{idx}/{len(player_rows)}] {player_key}")
                time.sleep(MICRO_SLEEP)

                league = League(oauth, league_id)

                # Pull player data
                player_data = league.player_details(player_id)

                if not player_data:
                    print("  → No data returned")
                    break

                # Handle list response
                player = player_data[0] if isinstance(player_data, list) else player_data

                position = player.get("display_position")
                nfl_team = player.get("editorial_team_abbr")

                print(f"  → Position: {position}, Team: {nfl_team}")

                # --- Update players table ---
                cur.execute("""
                    UPDATE players
                    SET position = ?, nfl_team = ?
                    WHERE player_id = ?
                """, (
                    position,
                    nfl_team,
                    player_id
                ))

                # --- Update rosters table ---
                cur.execute("""
                    UPDATE rosters
                    SET position = ?, nfl_team = ?
                    WHERE player_id = ?
                """, (
                    position,
                    nfl_team,
                    player_id
                ))

                conn.commit()
                break

            except Exception as e:
                error_text = str(e)

                if "Request denied" in error_text:
                    wait_time = 60
                    retries += 1
                    print(f"⚠️ Rate limited. Sleeping {wait_time}s")
                    time.sleep(wait_time)
                else:
                    print(f"❌ Error: {e}")
                    break

    conn.close()
    print("\n🎉 Player metadata backfill complete.")

def store_player_keepers(oauth, league_id):
    from yahoo_fantasy_api import League
    import time

    # --- Safe league init (prevents crash on rate limit) ---
    def safe_create_league(oauth, league_id):
        MAX_RETRIES = 5
        for attempt in range(MAX_RETRIES):
            try:
                league = League(oauth, league_id)
                league.settings()
                return league
            except Exception as e:
                if "Request denied" in str(e):
                    wait_time = 60
                    print(f"⚠️ League init rate-limited. Sleeping {wait_time}s")
                    time.sleep(wait_time)
                else:
                    raise e
        raise RuntimeError("Failed to initialize league")

    league = safe_create_league(oauth, league_id)

    conn = get_db()
    cur = conn.cursor()

    # --- Only players from this league ---
    cur.execute("""
        SELECT DISTINCT player_id, player_key
        FROM rosters
        WHERE league_id = ?
    """, (league_id,))
    player_rows = cur.fetchall()

    print(f"\nFound {len(player_rows)} players for keeper check")

    MAX_RETRIES = 5
    MICRO_SLEEP = 0.2

    for idx, (player_id, player_key) in enumerate(player_rows, start=1):

        retries = 0

        while retries < MAX_RETRIES:
            try:
                print(f"\nProcessing {idx}/{len(player_rows)}: {player_key}")

                time.sleep(MICRO_SLEEP)

                player_data = league.player_details(player_id)

                if not player_data:
                    print("  → No player data returned")
                    break

                # Normalize response
                if isinstance(player_data, list):
                    player_data = player_data[0]

                # --- Keeper parsing ---
                keeper_info = player_data.get("is_keeper") or {}

                is_keeper = 1 if keeper_info.get("kept") else 0

                keeper_cost = keeper_info.get("cost")
                keeper_cost = float(keeper_cost) if keeper_cost not in [None, ""] else None

                print(f"  → Keeper: {is_keeper} | Cost: {keeper_cost}")

                # --- Insert ---
                cur.execute("""
                    INSERT OR REPLACE INTO player_keepers (
                        league_id,
                        player_id,
                        player_key,
                        is_keeper,
                        keeper_cost
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    league_id,
                    player_id,
                    player_key,
                    is_keeper,
                    keeper_cost
                ))

                break  # success

            except Exception as e:
                error_text = str(e)

                if "Request denied" in error_text:
                    retries += 1
                    wait_time = 60
                    print(f"⚠️ Rate limited. Sleeping {wait_time}s (retry {retries})")
                    time.sleep(wait_time)
                else:
                    print(f"❌ Error for {player_key}: {e}")
                    break

    conn.commit()
    conn.close()

    print("\n🎉 Keeper ingestion complete.")

LEAGUE_IDS_16 = ['257.l.555890', '273.l.69198', '314.l.51555', '331.l.60660', '348.l.52705', '359.l.122617', '371.l.66032', '380.l.201654', '390.l.177654', '399.l.471671']
LEAGUE_IDS_17 = ['406.l.227', '414.l.57201', '423.l.24800', '449.l.204689', '461.l.186484']
LEAGUE_IDS = ['257.l.555890', '273.l.69198', '314.l.51555', '331.l.60660', '348.l.52705', '359.l.122617', '371.l.66032', '380.l.201654', '390.l.177654', '399.l.471671', '406.l.227', '414.l.57201', '423.l.24800', '449.l.204689', '461.l.186484']

# for league_id in LEAGUE_IDS:
#     debug_season_stat_details(oauth, league_id)

# for league_id in LEAGUE_IDS:
#     store_season_stat_details(oauth, league_id)

for league_id in LEAGUE_IDS:
    store_player_keepers(oauth, league_id)

# for league_id in LEAGUE_IDS:
#     store_season_stats(oauth, league_id)

# for league_id in LEAGUE_IDS:
#     store_weekly_points(oauth, league_id)

# for league_id in LEAGUE_IDS:
#     store_rosters(oauth, league_id)

# for league_id in LEAGUE_IDS:
#     backfill_player_metadata(oauth)

# for league_id in LEAGUE_IDS:
#     store_draft_results(oauth, league_id)

# for league_id in LEAGUE_IDS:
#     store_teams(oauth, league_id)
#
# for league_id in LEAGUE_IDS:
#     store_league(oauth, league_id)

# for league_id in LEAGUE_IDS_17:
# 	for week in range(1, 18): # adjust season length
# 	    store_matchups(oauth, league_id, week)



