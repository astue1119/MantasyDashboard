import streamlit as st
import pandas as pd
import sqlite3

# -----------------------
# CONFIG
# -----------------------
st.set_page_config(page_title="League Overview", layout="wide")

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
league_df = run_query("""
SELECT *
FROM league_team_summary
ORDER BY wins DESC, points_for DESC
""")

dominance_df = run_query("""
SELECT *
FROM team_weekly_dominance
""")

luck_df = run_query("""
SELECT *
FROM team_luck_index
""")

# -----------------------
# SIDEBAR FILTERS
# -----------------------
st.sidebar.header("Filters")

# Get unique seasons
seasons = sorted(league_df["season"].unique(), reverse=True)

selected_season = st.sidebar.selectbox("Select Season", seasons)

# Map season -> league_id
league_id_map = (
    league_df[["season", "league_id"]]
    .drop_duplicates()
    .set_index("season")["league_id"]
    .to_dict()
)

selected_league = league_id_map[selected_season]

# Apply filtering
league_df = league_df[league_df["league_id"] == selected_league]
dominance_df = dominance_df[dominance_df["league_id"] == selected_league]
luck_df = luck_df[luck_df["league_id"] == selected_league]

# Merge luck into main table
league_df = league_df.merge(
    luck_df[["team_key", "luck_score"]],
    on="team_key",
    how="left"
)

# -----------------------
# PAGE TITLE
# -----------------------
st.title("🏈 League Overview")

# -----------------------
# STANDINGS TABLE
# -----------------------
st.subheader("Standings")

display_cols = [
    "team_name",
    "manager",
    "wins",
    "losses",
    "points_for",
    "points_against",
    "luck_score",
    "aggression_score"
]

st.dataframe(
    league_df[display_cols]
    .sort_values(by=["wins", "points_for"], ascending=False),
    use_container_width=True
)

# -----------------------
# POINTS SCORED CHART
# -----------------------
st.subheader("Total Points Scored")

points_df = league_df[["team_name", "points_for"]].set_index("team_name")
st.bar_chart(points_df)

# -----------------------
# POINTS AGAINST CHART
# -----------------------
st.subheader("Points Against")

pa_df = league_df[["team_name", "points_against"]].set_index("team_name")
st.bar_chart(pa_df)

# -----------------------
# WEEKLY DOMINANCE
# -----------------------
st.subheader("Weekly Dominance (vs League Average)")

# Map team names
team_map = league_df.set_index("team_key")["team_name"].to_dict()

dominance_df["team_name"] = dominance_df["team_key"].map(team_map)

pivot_df = dominance_df.pivot(
    index="week",
    columns="team_name",
    values="vs_league_avg"
)

st.line_chart(pivot_df)

# -----------------------
# TOP / BOTTOM TEAMS BY DOMINANCE
# -----------------------
st.subheader("Average Dominance")

avg_dom = (
    dominance_df.groupby("team_name")["vs_league_avg"]
    .mean()
    .sort_values(ascending=False)
)

col1, col2 = st.columns(2)

with col1:
    st.write("🔥 Top Teams")
    st.dataframe(avg_dom.head(5))

with col2:
    st.write("🥶 Bottom Teams")
    st.dataframe(avg_dom.tail(5))