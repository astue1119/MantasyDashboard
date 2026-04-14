import streamlit as st
import pandas as pd
import sqlite3

# -----------------------
# CONFIG
# -----------------------
st.set_page_config(page_title="Matchup Analyzer", layout="wide")

DB_PATH = "MantasyFootbrawl.db"

# -----------------------
# DB CONNECTION
# -----------------------
@st.cache_data
def run_query(query):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# -----------------------
# LOAD DATA
# -----------------------
matchups_df = run_query("""
SELECT *
FROM matchup_analysis_view
""")

# -----------------------
# SIDEBAR FILTERS
# -----------------------
st.sidebar.header("Filters")

# Get unique seasons
seasons = sorted(matchups_df["season"].unique(), reverse=True)

selected_season = st.sidebar.selectbox("Select Season", seasons)

# Map season -> league_id
league_id_map = (
    matchups_df[["season", "league_id"]]
    .drop_duplicates()
    .set_index("season")["league_id"]
    .to_dict()
)

selected_league = league_id_map[selected_season]

matchups_df = matchups_df[matchups_df["league_id"] == selected_league]

managers = sorted(matchups_df["manager"].unique(), reverse=False)
selected_manager = st.sidebar.selectbox("Select Manager", managers)

# Filter for team
team_df = matchups_df[matchups_df["manager"] == selected_manager]

opponents = sorted(team_df["opponent_manager"].unique())
selected_opponent = st.sidebar.selectbox("Opponent", ["All"] + opponents)

if selected_opponent != "All":
    team_df = team_df[team_df["opponent_manager"] == selected_opponent]

weeks = sorted(team_df["week"].unique())
selected_weeks = st.sidebar.multiselect("Weeks", weeks, default=weeks)

team_df = team_df[team_df["week"].isin(selected_weeks)]

# -----------------------
# PAGE TITLE
# -----------------------
st.title("⚔️ Matchup Analyzer")

st.subheader(f"{selected_manager} vs {selected_opponent}")

# -----------------------
# SUMMARY METRICS
# -----------------------
wins = team_df["is_winner"].sum()
losses = len(team_df) - wins
avg_margin = team_df["margin"].mean()
avg_points = team_df["points"].mean()

col1, col2, col3, col4 = st.columns(4)

col1.metric("Record", f"{wins}-{losses}")
col2.metric("Avg Points", round(avg_points, 1))
col3.metric("Avg Margin", round(avg_margin, 1))
col4.metric("Games Played", len(team_df))

# -----------------------
# WEEKLY RESULTS TABLE
# -----------------------
st.subheader("Matchup Results")

display_df = team_df.copy()
display_df["result"] = display_df["is_winner"].apply(lambda x: "W" if x == 1 else "L")

st.dataframe(
    display_df[
        ["week", "opponent_manager", "points", "opponent_points", "margin", "result"]
    ].sort_values(by="week"),
    use_container_width=True
)

# -----------------------
# SCORING COMPARISON
# -----------------------
st.subheader("Points vs Opponent")

score_chart = team_df.set_index("week")[["points", "opponent_points"]]
st.line_chart(score_chart)

# -----------------------
# MARGIN OF VICTORY
# -----------------------
st.subheader("Margin of Victory")

margin_chart = team_df.set_index("week")["margin"]
st.bar_chart(margin_chart)

# -----------------------
# VS LEAGUE AVERAGE
# -----------------------
st.subheader("Performance vs League Average")

vs_avg_chart = team_df.set_index("week")["vs_league_avg"]
st.bar_chart(vs_avg_chart)

# -----------------------
# PROJECTION VS ACTUAL
# -----------------------
st.subheader("Projected vs Actual")

proj_chart = team_df.set_index("week")[["points", "projected_points"]]
st.line_chart(proj_chart)