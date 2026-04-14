import streamlit as st
import pandas as pd
import sqlite3

# -----------------------
# CONFIG
# -----------------------
st.set_page_config(page_title="Optimal Lineup", layout="wide")

DB_PATH = "MantasyFootbrawl.db"

# -----------------------
# DB
# -----------------------
@st.cache_data
def run_query(query):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(query, conn)
    conn.close()
    return df

df = run_query("SELECT * FROM roster_weekly_points")

# -----------------------
# FILTERS
# -----------------------
st.sidebar.header("Filters")

# Get unique seasons
seasons = sorted(df["season"].unique(), reverse=True)
selected_season = st.sidebar.selectbox("Select Season", seasons)

# Map season -> league_id
league_id_map = (
    df[["season", "league_id"]]
    .drop_duplicates()
    .set_index("season")["league_id"]
    .to_dict()
)

league = league_id_map[selected_season]

df = df[df["league_id"] == league]

managers = sorted(df["manager"].unique(), reverse=False)
selected_manager = st.sidebar.selectbox("Select Manager", managers)

# Map season -> league_id
team_name_map = (
    df[["manager", "team_key"]]
    .drop_duplicates()
    .set_index("manager")["team_key"]
    .to_dict()
)

team = team_name_map[selected_manager]

team_df = df[df["team_key"] == team]

weeks = sorted(team_df["week"].unique())
selected_weeks = st.sidebar.multiselect("Weeks", weeks, default=weeks)

team_df = team_df[team_df["week"].isin(selected_weeks)]

# -----------------------
# OPTIMAL LINEUP FUNCTION
# -----------------------
def get_optimal_lineup(players):
    players = players.copy()
    lineup = []

    # QB
    qb = players[players["eligible_positions"].str.contains("QB", na=False)]
    if not qb.empty:
        best = qb.sort_values("fantasy_points", ascending=False).iloc[0]
        lineup.append(best)
        players = players.drop(best.name)

    # RB (2)
    rb = players[players["eligible_positions"].str.contains("RB", na=False)]
    best_rb = rb.sort_values("fantasy_points", ascending=False).head(2)
    for _, row in best_rb.iterrows():
        lineup.append(row)
    players = players.drop(best_rb.index)

    # WR (2)
    wr = players[players["eligible_positions"].str.contains("WR", na=False)]
    best_wr = wr.sort_values("fantasy_points", ascending=False).head(2)
    for _, row in best_wr.iterrows():
        lineup.append(row)
    players = players.drop(best_wr.index)

    # TE (1)
    te = players[players["eligible_positions"].str.contains("TE", na=False)]
    if not te.empty:
        best = te.sort_values("fantasy_points", ascending=False).iloc[0]
        lineup.append(best)
        players = players.drop(best.name)

    # FLEX
    flex = players[
        players["eligible_positions"].str.contains("RB|WR|TE", na=False)
    ]
    if not flex.empty:
        best = flex.sort_values("fantasy_points", ascending=False).iloc[0]
        lineup.append(best)

    # K (1)
    k = players[players["eligible_positions"].str.contains("K", na=False)]
    if not k.empty:
        best = k.sort_values("fantasy_points", ascending=False).iloc[0]
        lineup.append(best)
        players = players.drop(best.name)

    # DEF (1)
    defense = players[players["eligible_positions"].str.contains("DEF", na=False)]
    if not defense.empty:
        best = defense.sort_values("fantasy_points", ascending=False).iloc[0]
        lineup.append(best)
        players = players.drop(best.name)

    # ✅ Convert safely
    if lineup:
        return pd.DataFrame(lineup)
    else:
        return pd.DataFrame(columns=players.columns)

# -----------------------
# CALCULATE RESULTS
# -----------------------
results = []

for week in selected_weeks:
    week_players = team_df[team_df["week"] == week]

    actual_points = week_players[week_players["is_starting"] == 1]["fantasy_points"].sum()

    optimal_lineup = get_optimal_lineup(week_players)
    optimal_points = optimal_lineup["fantasy_points"].sum()

    efficiency = actual_points / optimal_points if optimal_points > 0 else 0

    results.append({
        "week": week,
        "actual_points": actual_points,
        "optimal_points": optimal_points,
        "efficiency": round(efficiency, 3)
    })

results_df = pd.DataFrame(results)

# -----------------------
# PAGE
# -----------------------
st.title("🧠 Optimal Lineup Analysis")

# Summary
col1, col2, col3 = st.columns(3)

col1.metric("Avg Efficiency", round(results_df["efficiency"].mean(), 3))
col2.metric("Total Actual", round(results_df["actual_points"].sum(), 1))
col3.metric("Total Optimal", round(results_df["optimal_points"].sum(), 1))

# Table
st.subheader("Weekly Efficiency")

st.dataframe(results_df, use_container_width=True)

# Chart
st.subheader("Efficiency Over Time")

chart = results_df.set_index("week")["efficiency"]
st.line_chart(chart)

# Compare actual vs optimal
st.subheader("Actual vs Optimal Points")

compare_chart = results_df.set_index("week")[["actual_points", "optimal_points"]]
st.line_chart(compare_chart)