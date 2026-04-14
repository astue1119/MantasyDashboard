import streamlit as st
import pandas as pd
import sqlite3

# -----------------------
# CONFIG
# -----------------------
st.set_page_config(page_title="Team Deep Dive", layout="wide")

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
team_summary_df = run_query("""
SELECT *
FROM league_team_summary
""")

weekly_df = run_query("""
SELECT *
FROM team_weekly_summary
""")

draft_df = run_query("""
SELECT *
FROM team_draft_summary
""")

dominance_df = run_query("""
SELECT *
FROM team_weekly_dominance 
""")

# -----------------------
# SIDEBAR FILTERS
# -----------------------
st.sidebar.header("Filters")

# Get unique seasons
seasons = sorted(team_summary_df["season"].unique(), reverse=True)

selected_season = st.sidebar.selectbox("Select Season", seasons)

# Map season -> league_id
league_id_map = (
    team_summary_df[["season", "league_id"]]
    .drop_duplicates()
    .set_index("season")["league_id"]
    .to_dict()
)

selected_league = league_id_map[selected_season]

team_summary_df = team_summary_df[team_summary_df["league_id"] == selected_league]
weekly_df = weekly_df[weekly_df["league_id"] == selected_league]
draft_df = draft_df[draft_df["league_id"] == selected_league]
dominance_df = dominance_df[dominance_df["league_id"] == selected_league]

managers = sorted(team_summary_df["manager"].unique(), reverse=False)
selected_manager = st.sidebar.selectbox("Select Manager", managers)

# Map season -> league_id
team_name_map = (
    team_summary_df[["manager", "team_name"]]
    .drop_duplicates()
    .set_index("manager")["team_name"]
    .to_dict()
)

selected_team = team_name_map[selected_manager]

# Filter to team
team_info = team_summary_df[team_summary_df["team_name"] == selected_team].iloc[0]
team_weekly = weekly_df[weekly_df["team_name"] == selected_team]
team_draft = draft_df[draft_df["team_name"] == selected_team]
team_dom = dominance_df[dominance_df["team_key"] == team_info["team_key"]]

# -----------------------
# PAGE TITLE
# -----------------------
st.title(f"🏈 {selected_team}")

# -----------------------
# TEAM SUMMARY METRICS
# -----------------------
col1, col2, col3, col4 = st.columns(4)

col1.metric("Record", f"{team_info['wins']}-{team_info['losses']}")
col2.metric("Points For", round(team_info["points_for"], 1))
col3.metric("Points Against", round(team_info["points_against"], 1))
col4.metric("Aggression", team_info["aggression_score"])

# -----------------------
# WEEKLY PERFORMANCE
# -----------------------
st.subheader("Weekly Performance")

weekly_chart = team_weekly.set_index("week")[["points", "projected_points"]]
st.line_chart(weekly_chart)

# -----------------------
# DOMINANCE
# -----------------------
st.subheader("Performance vs League Average")

dom_chart = team_dom.set_index("week")["vs_league_avg"]
st.bar_chart(dom_chart)

# -----------------------
# WIN / LOSS BREAKDOWN
# -----------------------
st.subheader("Match Results")

results_df = team_weekly.copy()
results_df["result"] = results_df["is_winner"].apply(lambda x: "W" if x == 1 else "L")

st.dataframe(
    results_df[
        ["week", "points", "opponent_points", "result"]
    ],
    use_container_width=True
)

# -----------------------
# DRAFT BREAKDOWN
# -----------------------
st.subheader("Draft Breakdown")

draft_display = team_draft.copy()
draft_display["keeper"] = draft_display["is_keeper"].apply(
    lambda x: "Yes" if x == 1 else ""
)

st.dataframe(
    draft_display[
        ["full_name", "position", "auction_cost", "keeper"]
    ].sort_values(by="auction_cost", ascending=False),
    use_container_width=True
)

# -----------------------
# POSITION SPENDING
# -----------------------
st.subheader("Spending by Position")

pos_spend = (
    team_draft.groupby("position")["auction_cost"]
    .sum()
    .sort_values(ascending=False)
)

st.bar_chart(pos_spend)