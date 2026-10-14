"""Endangered Languages dashboard.  Run with:  streamlit run app.py
Needs languages_clean.csv and text_themes.csv in the same folder (export from the notebook)."""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Endangered Languages", layout="wide")

INK = "#1D1D1B"
ORDER = ["Vulnerable", "Definitely endangered", "Severely endangered", "Critically endangered", "Extinct"]
COLORS = {"Vulnerable": "#9ED6DF", "Definitely endangered": "#EAC119", "Severely endangered": "#ED773C",
          "Critically endangered": "#C63F3E", "Extinct": INK}
SYMBOLS = {"Vulnerable": "circle", "Definitely endangered": "square", "Severely endangered": "diamond",
           "Critically endangered": "triangle-up", "Extinct": "x"}
AREA_COLORS = {"Americas": "#245E55", "Asia & Oceania": "#808BC5", "Europe, Africa & W. Asia": "#ED773C"}
ZONE_COLORS = {"Tropics": "#ED773C", "Outside tropics": "#245E55"}
BANDS = ["<100", "100-999", "1k-9.9k", "10k+", "unknown"]
THEME_ORDER = ["decline", "revival", "recognition", "outside pressure", "few speakers left", "identity and heritage"]


@st.cache_data
def load():
    d = pd.read_csv("languages_clean.csv")
    d["severe"] = d["endangerment"].isin(ORDER[3:])
    d["speakers_txt"] = d["speakers"].map(lambda v: "unknown" if pd.isna(v) else f"{v:,.0f}")
    return d, pd.read_csv("text_themes.csv")


def style(fig, height):
    fig.update_layout(template="plotly_white", height=height, font=dict(size=14, color=INK),
                      paper_bgcolor="white", plot_bgcolor="white", margin=dict(l=10, r=10, t=30, b=10))
    return fig


df, themes = load()
AREAS = sorted(df["world_area"].unique())

# ---------- Header + call to action ----------
st.title("Endangered languages: size, place, and risk")
st.markdown("**Question:** is how endangered a language is linked more to **how many people speak it**, or to **where it is**?")
st.info("**Try it:** use the filters below to explore the map, then open the **Size vs place** tab.")

# ---------- Filters (top of page) ----------
with st.container(border=True):
    st.markdown("**Filter the languages**")
    fc1, fc2, fc3, fc4 = st.columns(4)
    areas = fc1.multiselect("World area", AREAS, default=AREAS)
    status = fc2.multiselect("Status", ORDER, default=ORDER)
    bands = fc3.multiselect("Number of speakers", BANDS, default=BANDS)
    pick = fc4.selectbox("Find a language", ["(none)"] + sorted(df["name"].unique()))

f = df[df["world_area"].isin(areas) & df["endangerment"].isin(status) & df["size_band"].isin(bands)]
st.markdown(f"**Showing {len(f):,} of {len(df):,} languages**")
if pick != "(none)":
    r = df[df["name"] == pick].iloc[0]
    st.success(f"**{pick}**: {r['endangerment']}, {r['speakers_txt']} speakers, {r['world_area']}")
if f.empty:
    st.warning("No languages match these filters. Add a world area, status, or speaker group above.")
    st.stop()

# ---------- Numbers for the current selection ----------
st.caption("The three numbers below describe your **current filter selection**.")
known = f["speakers"].dropna()
c1, c2, c3 = st.columns(3)
c1.metric("Languages selected", f"{len(f):,}")
c2.metric("Critically endangered or extinct", f"{f['severe'].mean():.0%}")
c3.metric("Median speakers", f"{known.median():,.0f}" if len(known) else "n/a")
c3.caption(f"Based on {len(known):,} languages with a known speaker count")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Map", "Size vs place", "Tropics test", "What Wikipedia says", "Takeaways"])

# ---------- Tab 1: map (responds to filters) ----------
with tab1:
    fig = go.Figure()
    lons = list(range(-180, 181, 5))
    for i, lat in enumerate([23.5, -23.5]):
        fig.add_trace(go.Scattergeo(lon=lons, lat=[lat] * len(lons), mode="lines", hoverinfo="skip",
                                    line=dict(color="#5A5A55", width=1.5, dash="dash"),
                                    name="Tropics (23.5° N and S)", legendgroup="tropics", showlegend=(i == 0)))
    for s in ORDER:
        d = f[f["endangerment"] == s]
        if d.empty:
            continue
        fig.add_trace(go.Scattergeo(lon=d["longitude"], lat=d["latitude"], mode="markers", name=f"{s} ({len(d):,})",
                                    text=d["name"], customdata=d[["world_area", "speakers_txt"]].values,
                                    hovertemplate="<b>%{text}</b><br>%{customdata[0]}<br>Speakers: %{customdata[1]}<extra></extra>",
                                    marker=dict(symbol=SYMBOLS[s], size=8, color=COLORS[s], opacity=0.9,
                                                line=dict(color=INK, width=1.5 if s == "Extinct" else 0.6))))
    if pick != "(none)":
        h = df[df["name"] == pick]
        fig.add_trace(go.Scattergeo(lat=h["latitude"], lon=h["longitude"], mode="markers+text", text=h["name"],
                                    textposition="top center", name="Your pick", hoverinfo="skip",
                                    marker=dict(symbol="circle-open", size=20, color=INK, line=dict(width=3))))
    fig.update_geos(projection_type="natural earth", showland=True, landcolor="#F4F0E8", showocean=True,
                    oceancolor="#FFFFFF", showcountries=True, countrycolor="#D8D0C2", coastlinecolor="#BDB4A3",
                    showframe=False, lataxis_range=[-60, 85])
    style(fig, 560)
    fig.update_layout(legend=dict(title="Status (number shown)", font=dict(size=14)), hoverlabel=dict(font_size=15))
    st.plotly_chart(fig, theme=None)
    st.caption(f"**Chart summary:** each marker is one language ({len(f):,} shown, approximate point). Status is shown by both "
               "color and shape. Dashed lines mark the tropics. Only endangered or extinct languages are in this data, "
               "so dense areas may simply have many languages.")

# ---------- Tab 2: size vs place (static, labeled) ----------
with tab2:
    k = df[(df["size_band"] != "unknown") & (df["endangerment"] != "Extinct")]
    g = (k.groupby(["size_band", "world_area"])
          .agg(n=("language_id", "size"), pct=("endangerment", lambda s: (s == "Critically endangered").mean() * 100))
          .reset_index())
    g["label"] = g["pct"].round(0).astype(int).astype(str) + "%<br>n=" + g["n"].astype(str)
    fig2 = px.bar(g, x="size_band", y="pct", color="world_area", barmode="group", text="label",
                  color_discrete_map=AREA_COLORS, category_orders={"size_band": BANDS[:4], "world_area": AREAS},
                  labels={"size_band": "Number of speakers", "pct": "Critically endangered (% of group)",
                          "world_area": "World area"})
    fig2.update_traces(textposition="outside", marker_line_color=INK, marker_line_width=1)
    fig2.update_yaxes(range=[0, 110])
    style(fig2, 500)
    st.plotly_chart(fig2, theme=None)
    st.caption(f"**Population for this chart:** all {len(k):,} living languages with a known speaker count. "
               "It does **not** change with the filters above.")
    st.markdown("**What it means:** smaller languages are more likely to be critically endangered everywhere. "
                "But for languages with 100 to 999 speakers, about 55% in Europe, Africa & W. Asia are critically "
                "endangered, against about 13 to 15% in the Americas and Asia & Oceania. Place seems to matter, "
                "but this data can't say why.")

# ---------- Tab 3: tropics test (static, labeled) ----------
with tab3:
    t = df.groupby(["world_area", "zone"]).agg(n=("language_id", "size"), pct=("severe", "mean")).reset_index()
    o = df.groupby("zone").agg(n=("language_id", "size"), pct=("severe", "mean")).reset_index()
    o["world_area"] = "All areas"
    t = pd.concat([o, t], ignore_index=True)
    t["pct"] = t["pct"] * 100
    t["label"] = t["pct"].round(0).astype(int).astype(str) + "%<br>n=" + t["n"].astype(str)
    fig3a = px.bar(t, x="world_area", y="pct", color="zone", barmode="group", text="label",
                   color_discrete_map=ZONE_COLORS, category_orders={"world_area": ["All areas"] + AREAS},
                   labels={"world_area": "World area", "pct": "Critically endangered or extinct (% of languages)",
                           "zone": "Zone"})
    fig3a.update_traces(textposition="outside", marker_line_color=INK, marker_line_width=1)
    fig3a.update_yaxes(range=[0, 100])
    style(fig3a, 480)
    st.markdown("**My first guess:** languages in the tropics would be at higher risk. I tested it.")
    st.plotly_chart(fig3a, theme=None)
    tp = o.set_index("zone")["pct"]
    st.caption(f"**Population for this chart:** all {len(df):,} languages with a map location. It does **not** change with the filters above.")
    st.markdown(f"**What it means:** overall, {tp['Tropics']:.1f}% of languages in the tropics and {tp['Outside tropics']:.1f}% outside "
                "are critically endangered or extinct, so the tropics don't predict risk on their own. Within world areas the "
                "pattern changes direction: higher risk outside the tropics in the Americas, higher inside in Europe, Africa & W. Asia "
                "and in Asia & Oceania. This data can't say why.")

# ---------- Tab 4: text themes (static, labeled) ----------
with tab4:
    p = themes.pivot(index="theme", columns="world_area", values="pct").reindex(THEME_ORDER)
    m = themes.pivot(index="theme", columns="world_area", values="matched").reindex_like(p)
    a = themes.pivot(index="theme", columns="world_area", values="articles").reindex_like(p)
    txt = p.round(0).astype(int).astype(str) + "%<br>(" + m.astype(int).astype(str) + "/" + a.astype(int).astype(str) + ")"
    fig4 = go.Figure(go.Heatmap(z=p.values, x=list(p.columns), y=list(p.index), text=txt.values, texttemplate="%{text}",
                                textfont=dict(size=15), xgap=3, ygap=3, zmin=0, zmax=100,
                                colorscale=[[0, "#FFFFFF"], [1, "#245E55"]], colorbar=dict(title="% of articles"),
                                customdata=np.dstack([m.values, a.values]),
                                hovertemplate="<b>%{y}</b><br>%{x}<br>%{customdata[0]} of %{customdata[1]} articles (%{z:.0f}%)<extra></extra>"))
    fig4.update_yaxes(autorange="reversed", automargin=True)
    style(fig4, 480)
    fig4.update_layout(hoverlabel=dict(font_size=18, bgcolor="white", bordercolor=INK, font_color=INK))
    st.plotly_chart(fig4, theme=None)
    st.caption("**Population for this chart:** 56 Wikipedia articles from a random sample of 60 languages (17 to 20 per area). "
               "Not filtered. Boxes show the share of articles containing a word search, with (matches/articles). "
               "These are word counts on a small sample, so treat differences as hints. Hover over a box for its details.")
    q1, q2 = st.columns(2)
    q1.markdown("**Theme: very few speakers left**\n\n> \"The language's last native speaker, Della Prince, died in 1962.\"\n\n"
                "Wiyot article (language_id 774)")
    q2.markdown("**Counterexample: small but not the worst label**\n\n> Banawá Yafi (language_id 1766) has about 1,000 "
                "speakers but is listed as Vulnerable, not Critically endangered.")

# ---------- Tab 5: takeaways ----------
with tab5:
    st.markdown("""
**What the evidence shows** (full dataset, not the current filters)
- Smaller languages are usually more endangered.
- Place matters even at the same size (see *Size vs place*).
- I tested my first guess, the tropics, and it didn't hold up on its own (see *Tropics test*): the pattern flips between world areas.
- Many Wikipedia articles describe languages with very few speakers left and tie them to a people's identity and history.

**What it can't tell us**
- *Why* languages are endangered, or whether children are still learning them.
- Whether some places have more endangered languages than stable ones, since only endangered languages are listed.
- 183 languages have no speaker count, so they are left out of the size summaries.

**Who this is for:** community language programs and the groups that support them. It is a starting point for
conversations, not a ranking of who needs help.
""")
