import streamlit as st
import pandas as pd
import sqlite3

# -----------------------
# CONFIG
# -----------------------
st.set_page_config(page_title="Draft Analysis", layout="wide")

DB_PATH = "C:/Users/andys/PycharmProjects/FantasyFootball/MantasyFootbrawl.db"

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
team_spend_df = run_query("""
SELECT *
FROM draft_team_spending
""")

position_spend_df = run_query("""
SELECT *
FROM draft_spend_by_position
""")

draft_df = run_query("""
SELECT *
FROM draft_with_keepers
""")

best_values_df = run_query("""
SELECT *
FROM best_draft_values
""")

worst_values_df = run_query("""
SELECT *
FROM worst_draft_values
""")

# -----------------------
# SIDEBAR FILTER
# -----------------------
st.sidebar.header("Filters")

seasons = sorted(team_spend_df["season"].unique(), reverse=True)
selected_season = st.sidebar.selectbox("Select Season", seasons)

# Map season -> league_id
league_id_map = (
    team_spend_df[["season", "league_id"]]
    .drop_duplicates()
    .set_index("season")["league_id"]
    .to_dict()
)

selected_league = league_id_map[selected_season]

team_spend_df = team_spend_df[team_spend_df["league_id"] == selected_league]
position_spend_df = position_spend_df[position_spend_df["league_id"] == selected_league]
draft_df = draft_df[draft_df["league_id"] == selected_league]
best_values_df = best_values_df[best_values_df["league_id"] == selected_league]
worst_values_df = worst_values_df[worst_values_df["league_id"] == selected_league]

# -----------------------
# PAGE TITLE
# -----------------------
st.title("💰 Draft Analysis")

# -----------------------
# TEAM SPENDING
# -----------------------
st.subheader("Total Spend by Team")

team_spend_chart = team_spend_df.set_index("manager")["total_spent"]
st.bar_chart(team_spend_chart)

# -----------------------
# SPEND BY POSITION
# -----------------------
st.subheader("Spend by Position")

pivot_pos = position_spend_df.pivot(
    index="manager",
    columns="position",
    values="total_spent"
).fillna(0)

st.bar_chart(pivot_pos)

# -----------------------
# BEST / WORST VALUES
# -----------------------
st.subheader("Best Draft Values 💎")

st.dataframe(
    best_values_df[
        ["full_name", "position", "auction_cost", "total_fantasy_points", "points_per_dollar"]
    ],
    use_container_width=True
)

st.subheader("Worst Draft Values 💀")

st.dataframe(
    worst_values_df[
        ["full_name", "position", "auction_cost", "total_fantasy_points", "points_per_dollar"]
    ],
    use_container_width=True
)

# -----------------------
# FULL DRAFT TABLE
# -----------------------
st.subheader("Full Draft Results")

# Optional: cleaner display
draft_display = draft_df.copy()

# Add keeper label
draft_display["keeper"] = draft_display["is_keeper"].apply(
    lambda x: "Yes" if x == 1 else ""
)

st.dataframe(
    draft_display[
        ["manager", "full_name", "position", "auction_cost", "keeper"]
    ].sort_values(by="auction_cost", ascending=False),
    use_container_width=True
)