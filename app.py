"""Endangered Languages dashboard.  Run with:  streamlit run app.py
Needs languages_clean.csv and text_themes.csv in the same folder (export from the notebook)."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Endangered Languages", layout="wide")

ORDER = ["Vulnerable", "Definitely endangered", "Severely endangered", "Critically endangered", "Extinct"]
COLORS = {"Vulnerable": "#1b9e77", "Definitely endangered": "#e6c229", "Severely endangered": "#f26419",
          "Critically endangered": "#7b2cbf", "Extinct": "#111111"}
BANDS = ["<100", "100-999", "1k-9.9k", "10k+", "unknown"]


@st.cache_data
def load():
    return pd.read_csv("languages_clean.csv"), pd.read_csv("text_themes.csv")


df, themes = load()

# ---------- Header + call to action ----------
st.title("Endangered languages: size, place, and risk")
st.markdown("**Question:** is how endangered a language is linked more to **how many people speak it**, or to **where it is**?")
st.info("👈 **Try it:** use the filters on the left to explore the map, or pick a language under "
        "**Find a language** (try *Tulu*). Then open the **Size vs place** tab.")

# ---------- Sidebar filters ----------
st.sidebar.header("Filter the languages")
areas = st.sidebar.multiselect("World area", sorted(df["world_area"].unique()), default=sorted(df["world_area"].unique()))
status = st.sidebar.multiselect("Status", ORDER, default=ORDER)
bands = st.sidebar.multiselect("Number of speakers", BANDS, default=BANDS)
pick = st.sidebar.selectbox("Find a language", ["(none)"] + sorted(df["name"].unique()))
if pick != "(none)":
    r = df[df["name"] == pick].iloc[0]
    sp = "unknown" if pd.isna(r["speakers"]) else f"{r['speakers']:,.0f}"
    st.sidebar.success(f"**{pick}**: {r['endangerment']}, {sp} speakers")

f = df[df["world_area"].isin(areas) & df["endangerment"].isin(status) & df["size_band"].isin(bands)]
st.sidebar.caption(f"Showing {len(f):,} of {len(df):,} languages")
if f.empty:
    st.warning("No languages match these filters. Add a world area, status, or speaker group in the sidebar.")
    st.stop()

# ---------- Numbers for the current selection ----------
st.caption("The three numbers below describe your **current filter selection**.")
known = f["speakers"].dropna()
c1, c2, c3 = st.columns(3)
c1.metric("Languages selected", f"{len(f):,}")
c2.metric("Critically endangered or extinct", f"{f['endangerment'].isin(ORDER[3:]).mean():.0%}")
c3.metric("Median speakers", f"{known.median():,.0f}" if len(known) else "n/a")
c3.caption(f"Based on {len(known):,} languages with a known speaker count")

tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Map", "📊 Size vs place", "📖 What Wikipedia says", "✅ Takeaways"])

# ---------- Tab 1: map (responds to filters) ----------
with tab1:
    fig = px.scatter_geo(f, lat="latitude", lon="longitude", color="endangerment",
                         category_orders={"endangerment": ORDER}, color_discrete_map=COLORS,
                         hover_name="name", hover_data={"speakers": ":,.0f", "world_area": True,
                                                        "latitude": False, "longitude": False},
                         projection="natural earth")
    fig.update_traces(marker_size=6, marker_opacity=0.8)
    fig.update_geos(showland=True, landcolor="#f2f2f2", showcountries=False, lataxis_range=[-60, 85])
    if pick != "(none)":
        h = df[df["name"] == pick]
        fig.add_trace(go.Scattergeo(lat=h["latitude"], lon=h["longitude"], mode="markers+text", text=h["name"],
                                    textposition="top center", name="Your pick", hoverinfo="skip",
                                    marker=dict(size=16, color="rgba(0,0,0,0)", line=dict(color="black", width=3))))
    fig.update_layout(height=520, margin=dict(l=0, r=0, t=0, b=0), legend_title="Status")
    st.plotly_chart(fig)
    st.caption(f"Each dot is one language ({len(f):,} shown, approximate point). Only endangered or extinct languages "
               "are in this data, so dense areas may simply have many languages.")

# ---------- Tab 2: size vs place (static, labeled) ----------
with tab2:
    k = df[(df["size_band"] != "unknown") & (df["endangerment"] != "Extinct")]
    g = (k.groupby(["size_band", "world_area"])
          .agg(n=("language_id", "size"), pct=("endangerment", lambda s: (s == "Critically endangered").mean() * 100))
          .reset_index())
    g["label"] = g["pct"].round(0).astype(int).astype(str) + "%<br>n=" + g["n"].astype(str)
    fig2 = px.bar(g, x="size_band", y="pct", color="world_area", barmode="group", text="label",
                  category_orders={"size_band": BANDS[:4]},
                  labels={"size_band": "Number of speakers", "pct": "Critically endangered (% of group)",
                          "world_area": "World area"})
    fig2.update_yaxes(range=[0, 110])
    fig2.update_layout(height=480)
    st.plotly_chart(fig2)
    st.caption(f"**Population for this chart:** all {len(k):,} living languages with a known speaker count. "
               "It does **not** change with the sidebar filters.")
    st.markdown("**What it means:** smaller languages are more likely to be critically endangered everywhere. "
                "But for languages with 100 to 999 speakers, about 55% in Europe, Africa & W. Asia are critically "
                "endangered, against about 13 to 15% in the Americas and Asia & Oceania. Place seems to matter, "
                "but this data can't say why.")

# ---------- Tab 3: text themes (static, labeled) ----------
with tab3:
    p = themes.pivot(index="theme", columns="world_area", values="pct")
    m = themes.pivot(index="theme", columns="world_area", values="matched").reindex_like(p)
    a = themes.pivot(index="theme", columns="world_area", values="articles").reindex_like(p)
    txt = p.round(0).astype(int).astype(str) + "%<br>(" + m.astype(int).astype(str) + "/" + a.astype(int).astype(str) + ")"
    fig3 = go.Figure(go.Heatmap(z=p.values, x=list(p.columns), y=list(p.index), text=txt.values,
                                texttemplate="%{text}", colorscale="YlGnBu", zmin=0, zmax=100,
                                colorbar_title="% of articles"))
    fig3.update_layout(height=450)
    st.plotly_chart(fig3)
    st.caption("**Population for this chart:** 56 Wikipedia articles from a random sample of 60 languages (17 to 20 per area). "
               "Not filtered. Boxes show the share of articles containing a word search, with (matches/articles). "
               "These are word counts on a small sample, so treat differences as hints.")
    q1, q2 = st.columns(2)
    q1.markdown("**Theme: very few speakers left**\n\n> \"The language's last native speaker, Della Prince, died in 1962.\"\n\n"
                "Wiyot article (language_id 774)")
    q2.markdown("**Counterexample: small but not the worst label**\n\n> Banawá Yafi (language_id 1766) has about 1,000 "
                "speakers but is listed as Vulnerable, not Critically endangered.")

# ---------- Tab 4: takeaways ----------
with tab4:
    st.markdown("""
**What the evidence shows** (full dataset, not the current filters)
- Smaller languages are usually more endangered.
- Place matters even at the same size (see *Size vs place*).
- The tropics don't explain risk on their own: overall, 31.3% of languages inside and 31.9% outside are critically
  endangered or extinct, and the pattern flips between world areas (Americas: 26% inside vs 51% outside;
  Europe, Africa & W. Asia: 39% inside vs 22% outside).

**What it can't tell us**
- *Why* languages are endangered, or whether children are still learning them.
- Whether some places have more endangered languages than stable ones, since only endangered languages are listed.
- 183 languages have no speaker count, so they are left out of the size summaries.

**Who this is for:** community language programs and the groups that support them. It is a starting point for
conversations, not a ranking of who needs help.
""")
