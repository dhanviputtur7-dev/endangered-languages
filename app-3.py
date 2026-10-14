"""Endangered Languages dashboard.  Run with:  streamlit run app.py
Needs languages_clean.csv and text_themes.csv in the same folder (export from the notebook)."""
import json
import re
import urllib.parse
import urllib.request

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
AREA_COLORS = {"Americas": "#245E55", "Asia & Oceania": "#808BC5", "Europe, Africa & W. Asia": "#ED773C"}
ZONE_COLORS = {"Tropics": "#ED773C", "Outside tropics": "#245E55"}
BANDS = ["<100", "100-999", "1k-9.9k", "10k+", "unknown"]
THEME_ORDER = ["decline", "revival", "recognition", "outside pressure", "few speakers left", "identity and heritage"]

# Same word searches as the notebook (Section 2f)
THEME_PATTERNS = {
    "decline": r"\b(?:endangered|decline|declining|declined|shift|shifted|assimilat\w*|suppress\w*|banned|prohibit\w*|dying)\b",
    "revival": r"\b(?:revival|revitali[sz]\w*|revive\w*|immersion|taught|teach\w*|school|schools|program|programme)\b",
    "recognition": r"\b(?:official language|official status|recogni[sz]ed|recognition|constitution|government)\b",
    "outside pressure": r"\b(?:colonial\w*|coloni[sz]\w*|migrat\w*|urban\w*|cities|globali[sz]\w*)\b",
    "few speakers left": r"\b(?:last (?:native |known |fluent |living )?speakers?|few (?:remaining |living )?speakers|nearly extinct|no (?:living |native |fluent )?speakers|moribund|dormant|elderly|elders)\b",
    "identity and heritage": r"\b(?:identity|identif\w*|ancestral|ancestors?|heritage|tribe|tribal|clan|ethnic\w*)\b",
}
COUNTER = r"\b(?:thriving|vigorous|growing|increas\w*|stable|widely spoken)\b"

# Simplified outline of Karnataka (lon, lat), from Natural Earth admin-1 boundaries
KARNATAKA = [[74.85, 12.77], [74.94, 12.88], [74.72, 13.33], [74.68, 13.55], [74.74, 13.65], [74.55, 13.95], [74.45, 14.25], [74.38, 14.43], [74.38, 14.54], [74.3, 14.57], [74.25, 14.72], [74.11, 14.8], [74.24, 14.88], [74.15, 14.92], [74.27, 15.04], [74.24, 15.23], [74.26, 15.38], [74.25, 15.59], [74.09, 15.66], [74.22, 15.74], [74.37, 15.84], [74.42, 16.05], [74.48, 16.22], [74.32, 16.29], [74.36, 16.4], [74.3, 16.46], [74.24, 16.48], [74.29, 16.53], [74.38, 16.57], [74.52, 16.63], [74.56, 16.55], [74.68, 16.68], [74.81, 16.77], [74.85, 16.86], [75.05, 16.95], [75.24, 16.9], [75.45, 16.96], [75.63, 16.98], [75.63, 17.13], [75.58, 17.29], [75.64, 17.48], [75.85, 17.4], [76.02, 17.35], [76.25, 17.37], [76.33, 17.45], [76.31, 17.6], [76.47, 17.73], [76.63, 17.74], [76.74, 17.9], [76.9, 18.09], [77.09, 18.2], [77.23, 18.41], [77.41, 18.33], [77.58, 18.27], [77.56, 18.08], [77.52, 17.85], [77.47, 17.72], [77.59, 17.55], [77.59, 17.48], [77.38, 17.16], [77.43, 16.81], [77.41, 16.65], [77.39, 16.57], [77.49, 16.38], [77.48, 16.2], [77.26, 15.96], [77.04, 15.74], [77.0, 15.63], [76.97, 15.5], [77.1, 15.31], [77.06, 15.01], [76.94, 15.02], [76.72, 14.99], [76.82, 14.86], [76.74, 14.61], [76.86, 14.49], [76.9, 14.41], [76.88, 14.32], [77.08, 14.24], [77.23, 14.33], [77.38, 14.24], [77.41, 14.32], [77.47, 14.2], [77.34, 14.12], [77.36, 13.99], [77.36, 13.9], [77.26, 14.02], [77.02, 14.05], [76.93, 14.18], [76.94, 14.06], [77.01, 13.9], [76.96, 13.77], [77.04, 13.74], [77.13, 13.81], [77.13, 13.89], [77.19, 13.89], [77.38, 13.85], [77.45, 13.7], [77.6, 13.77], [77.7, 13.81], [77.77, 13.92], [77.9, 13.93], [77.91, 13.89], [78.0, 13.87], [78.09, 13.69], [78.17, 13.61], [78.32, 13.59], [78.37, 13.49], [78.38, 13.34], [78.51, 13.28], [78.57, 13.22], [78.48, 13.05], [78.46, 12.89], [78.34, 12.87], [78.25, 12.86], [78.03, 12.85], [77.9, 12.87], [77.7, 12.68], [77.57, 12.5], [77.56, 12.34], [77.72, 12.18], [77.73, 12.06], [77.43, 11.81], [77.17, 11.8], [76.93, 11.81], [76.55, 11.65], [76.4, 11.71], [76.26, 11.81], [76.13, 11.86], [75.96, 11.93], [75.74, 12.08], [75.61, 12.13], [75.38, 12.31], [75.37, 12.47], [75.28, 12.5], [75.19, 12.6], [75.1, 12.67], [75.0, 12.7], [74.95, 12.77], [74.85, 12.77]]


@st.cache_data
def load():
    d = pd.read_csv("languages_clean.csv")
    d["severe"] = d["endangerment"].isin(ORDER[3:])
    d["speakers_txt"] = d["speakers"].map(lambda v: "unknown" if pd.isna(v) else f"{v:,.0f}")
    return d, pd.read_csv("text_themes.csv")


@st.cache_data(ttl=86400)
def wiki_text(title):
    """Plain text of one English Wikipedia article (raises on failure so errors are not cached)."""
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "query", "prop": "extracts", "explaintext": 1, "redirects": 1, "titles": title, "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": "endangered-languages-dashboard/1.0 (student project; endangered-languages.streamlit.app)"})
    with urllib.request.urlopen(req, timeout=15) as r:
        page = next(iter(json.load(r)["query"]["pages"].values()))
    text = page.get("extract")
    if not text:
        raise ValueError("no article text")
    return text


def kwic(text, pattern, width=110):
    m = re.search(pattern, text, flags=re.IGNORECASE)
    if not m:
        return ""
    return "..." + text[max(0, m.start() - width): m.end() + width].replace("\n", " ") + "..."


def style(fig, height):
    fig.update_layout(template="plotly_white", height=height, font=dict(size=14, color=INK),
                      paper_bgcolor="white", plot_bgcolor="white", margin=dict(l=10, r=10, t=30, b=10))
    return fig


def status_traces(fig, d, size=7):
    """One trace per status, all plain dots (color shows status)."""
    for s in ORDER:
        ds = d[d["endangerment"] == s]
        if ds.empty:
            continue
        fig.add_trace(go.Scattergeo(lon=ds["longitude"], lat=ds["latitude"], mode="markers", name=f"{s} ({len(ds):,})",
                                    text=ds["name"], customdata=ds[["world_area", "speakers_txt"]].values,
                                    hovertemplate="<b>%{text}</b><br>%{customdata[0]}<br>Speakers: %{customdata[1]}<extra></extra>",
                                    marker=dict(symbol="circle", size=size, color=COLORS[s], opacity=0.85,
                                                line=dict(color=INK, width=0.6))))


def land_style(fig):
    fig.update_geos(showland=True, landcolor="#F4F0E8", showocean=True, oceancolor="#FFFFFF", showcountries=True,
                    countrycolor="#D8D0C2", coastlinecolor="#BDB4A3", showframe=False)


df, themes = load()
AREAS = sorted(df["world_area"].unique())

# ---------- Header + call to action ----------
st.title("Endangered languages: size, place, and risk")
st.markdown("**Question:** How are speaker population and geographic location associated with the severity of "
            "language endangerment around the world?")
st.caption(f"Data: {len(df):,} languages listed as endangered or extinct that have a map location.")
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

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["Map", "Size vs place", "Tropics test", "What Wikipedia says", "Example: Tulu", "Takeaways"])

# ---------- Tab 1: map (responds to filters) ----------
with tab1:
    fig = go.Figure()
    lons = list(range(-180, 181, 5))
    band = [(x, 23.5) for x in lons] + [(x, -23.5) for x in reversed(lons)]
    band.append(band[0])
    fig.add_trace(go.Scattergeo(lon=[p[0] for p in band], lat=[p[1] for p in band], mode="lines", fill="toself",
                                fillcolor="rgba(237,119,60,0.15)", line=dict(width=0), hoverinfo="skip",
                                name="Tropics (shaded, 23.5° N to 23.5° S)"))
    for lat in (23.5, -23.5):
        fig.add_trace(go.Scattergeo(lon=lons, lat=[lat] * len(lons), mode="lines", hoverinfo="skip", showlegend=False,
                                    line=dict(color="#5A5A55", width=1.2, dash="dash")))
    status_traces(fig, f)
    if pick != "(none)":
        h = df[df["name"] == pick]
        fig.add_trace(go.Scattergeo(lat=h["latitude"], lon=h["longitude"], mode="markers+text", text=h["name"],
                                    textposition="top center", name="Your pick", hoverinfo="skip",
                                    marker=dict(symbol="circle-open", size=20, color=INK, line=dict(width=3))))
    land_style(fig)
    fig.update_geos(projection_type="natural earth", lataxis_range=[-60, 85])
    style(fig, 560)
    fig.update_layout(legend=dict(title="Status (number shown)", font=dict(size=14)), hoverlabel=dict(font_size=15))
    st.plotly_chart(fig, theme=None)
    st.caption(f"**Chart summary:** each dot is one language ({len(f):,} shown, approximate point), colored by status. "
               "The shaded band and dashed lines mark the tropics. Only endangered or extinct languages are in this data, "
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

# ---------- Tab 5: Tulu example ----------
with tab5:
    st.markdown("Tulu is one example, **not evidence for the conclusions**. It shows that a language with "
                "millions of speakers can still be on the list.")
    tulu = df[df["name"] == "Tulu"]
    if tulu.empty:
        st.warning("Tulu was not found in the data.")
    else:
        tr = tulu.iloc[0]
        left, right = st.columns([3, 2])
        with left:
            fig5 = go.Figure()
            fig5.add_trace(go.Scattergeo(lon=[p[0] for p in KARNATAKA], lat=[p[1] for p in KARNATAKA], mode="lines",
                                         fill="toself", fillcolor="rgba(36,94,85,0.12)",
                                         line=dict(color="#245E55", width=2), hoverinfo="skip",
                                         name="Karnataka (simplified outline)"))
            near = df[df["longitude"].between(73.5, 79) & df["latitude"].between(11, 19)]
            status_traces(fig5, near, size=10)
            fig5.add_trace(go.Scattergeo(lon=[tr["longitude"]], lat=[tr["latitude"]], mode="markers+text", text=["Tulu"],
                                         textposition="top right", textfont=dict(size=16, color=INK), name="Tulu",
                                         hoverinfo="skip", marker=dict(symbol="circle-open", size=24, color=INK, line=dict(width=3))))
            land_style(fig5)
            fig5.update_geos(projection_type="mercator", lonaxis_range=[73.5, 79], lataxis_range=[11, 19], resolution=50)
            style(fig5, 520)
            fig5.update_layout(legend=dict(title="Status (number shown)", font=dict(size=14)), hoverlabel=dict(font_size=15))
            st.plotly_chart(fig5, theme=None)
            st.caption("**Chart summary:** the green outline is Karnataka. Dots are languages in the data whose map point falls in "
                       "this window (not all are in Karnataka), colored by status like the main map. Tulu is circled. "
                       "The outline is simplified.")
        with right:
            st.metric("Tulu status", str(tr["endangerment"]))
            st.metric("Speakers", tr["speakers_txt"])
            st.markdown(f"World area: **{tr['world_area']}**. Zone: **{tr['zone']}**.")
            if pd.notna(tr["speakers"]):
                vul = df[(df["endangerment"] == "Vulnerable") & df["speakers"].notna()]
                bigger = int((vul["speakers"] > tr["speakers"]).sum())
                st.markdown(f"Only **{bigger}** of the **{len(vul):,}** Vulnerable languages with a known speaker count "
                            f"({bigger / len(vul):.1%}) have more speakers than Tulu.")

        st.subheader("What Wikipedia says about Tulu")
        st.markdown("""
*Paraphrased from the English Wikipedia article "Tulu language" (read October 14, 2026).*
- **Where and how many:** spoken mainly in coastal Karnataka (Dakshina Kannada and Udupi) and northern Kasaragod in Kerala. The 2011 census counted about 1.85 million native speakers, and UNESCO lists it as Vulnerable.
- **Culture:** known for oral epic poems (the Epic of Siri), Yakshagana theatre, and a small film industry. It is now written mostly in the Kannada script.
- **Status:** an additional administrative language alongside Kannada in two districts, but not on India's 8th Schedule. It is taught in some schools and at universities. The article also reports a September 2026 Karnataka cabinet decision on its recognition, which I have not checked.
- **Its own warning:** the article says Tulu is less popular than other languages, could become endangered, and faces pressure from mainstream languages. It also notes that speakers who migrated are often counted as Kannada speakers.
""")
        st.markdown("**Do my notebook's word searches show up?** The table runs the same six word searches on the article's full text, "
                    "plus the counterexample words.")
        try:
            article = wiki_text("Tulu language")
        except Exception:
            article = None
        if article is None:
            st.warning("Could not reach Wikipedia right now, so the word search results are not shown. Try again in a minute.")
        else:
            rows = []
            for theme, pat in {**THEME_PATTERNS, "counterexample words": COUNTER}.items():
                found = re.findall(pat, article, flags=re.IGNORECASE)
                rows.append({"Theme": theme, "Mentioned?": "Yes" if found else "No", "Matches": len(found),
                             "Words found": ", ".join(sorted({w.lower() for w in found})) or "none"})
            st.dataframe(pd.DataFrame(rows), hide_index=True)
            st.caption("Word searches count words, not meaning, so a match can be a false alarm (for example, 'cities' may just name "
                       "places). One article is also not a sample.")
            with st.expander("See the words around the first match for each theme"):
                for theme, pat in {**THEME_PATTERNS, "counterexample words": COUNTER}.items():
                    snippet = kwic(article, pat)
                    if snippet:
                        st.text(f"{theme}: {snippet}")

# ---------- Tab 6: takeaways ----------
with tab6:
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
