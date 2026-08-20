import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="FPL Analyzer", page_icon="⚽", layout="centered")

st.title("⚽ My FPL Team Analyzer")
st.caption("Personal mobile dashboard for squad analysis & rating")

# 1. Inputs
team_id = st.text_input("Enter FPL Team ID", placeholder="e.g. 123456")
gw = st.number_input("Gameweek", min_value=1, max_value=38, value=1)

@st.cache_data(ttl=600)
def fetch_fpl_data(t_id, gameweek):
    base_url = "https://fantasy.premierleague.com/api"
    
    # Static metadata
    static_res = requests.get(f"{base_url}/bootstrap-static/").json()
    elements = {p["id"]: p for p in static_res["elements"]}
    teams = {t["id"]: t["short_name"] for t in static_res["teams"]}
    
    # Manager picks
    picks_res = requests.get(f"{base_url}/entry/{t_id}/event/{gameweek}/picks/")
    if picks_res.status_code != 200:
        return None, None
    picks_data = picks_res.json()
    
    # Entry info
    entry_res = requests.get(f"{base_url}/entry/{t_id}/").json()
    
    squad = []
    for pick in picks_data["picks"]:
        p = elements[pick["element"]]
        squad.append({
            "Name": p["web_name"],
            "Team": teams[p["team"]],
            "Pos": ["GK", "DEF", "MID", "FWD"][p["element_type"] - 1],
            "Price": p["now_cost"] / 10,
            "Form": float(p.get("form", 0.0)),
            "Captain": pick["is_captain"],
            "Vice": pick["is_vice_captain"],
            "Bench": pick["position"] > 11,
            "Order": pick["position"]
        })
    return squad, entry_res

if st.button("Analyze Squad", type="primary"):
    if not team_id:
        st.warning("Please enter your Team ID first.")
    else:
        with st.spinner("Fetching data..."):
            squad, entry = fetch_fpl_data(team_id, gw)
            
        if not squad:
            st.error("Could not find team data. Make sure the Team ID and Gameweek are valid.")
        else:
            df = pd.DataFrame(squad)
            starters = df[~df["Bench"]]
            bench = df[df["Bench"]]
            
            # --- Quick Metrics ---
            total_value = df["Price"].sum()
            bench_value = bench["Price"].sum()
            captain_row = df[df["Captain"]].iloc[0] if not df[df["Captain"]].empty else None
            
            st.subheader("📊 Squad Overview")
            col1, col2 = st.columns(2)
            col1.metric("Squad Value", f"£{total_value:.1f}m")
            col2.metric("Bench Cost", f"£{bench_value:.1f}m")
            
            # --- Squad Rating Engine ---
            score = 10.0
            warnings = []
            
            # Check 1: Over-invested bench
            if bench_value > 19.0:
                score -= 1.5
                warnings.append("⚠️ **High bench value:** Too much money tied up on substitutes.")
            
            # Check 2: Playing GK on the bench
            bench_gks = bench[bench["Pos"] == "GK"]
            if not bench_gks.empty and bench_gks.iloc[0]["Price"] > 4.0:
                score -= 1.0
                warnings.append("⚠️ **Expensive reserve GK:** Consider downgrading backup keeper to a £4.0m enabler.")
            
            # Check 3: Captain selection
            if captain_row is not None and captain_row["Price"] < 8.0:
                score -= 1.0
                warnings.append("⚠️ **Differential captain:** Captain armband is placed on a non-premium player.")

            st.markdown(f"### Overall Rating: `{max(score, 1.0):.1f} / 10`")
            
            if warnings:
                st.write("#### Suggestions:")
                for w in warnings:
                    st.markdown(w)
            else:
                st.success("✅ Solid squad balance with optimal starting funds!")

            # --- Lineup Display ---
            st.write("#### Starting XI")
            st.dataframe(
                starters[["Pos", "Name", "Team", "Price", "Captain", "Vice"]],
                use_container_width=True,
                hide_index=True
            )
            
            st.write("#### Bench")
            st.dataframe(
                bench[["Pos", "Name", "Team", "Price"]],
                use_container_width=True,
                hide_index=True
            )