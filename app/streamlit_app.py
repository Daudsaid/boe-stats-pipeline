"""UK Interest Rates Pipeline: Streamlit dashboard on the BoE pipeline marts.

Reads the Parquet files in app/data (written by `boe export`), so the deployed
app needs no database or secrets. Run locally with:

    uv run streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent / "data"
REPO_URL = "https://github.com/Daudsaid/boe-stats-pipeline"

# Validated categorical palette (fixed order, never cycled). Max 4 series per chart.
SLOT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]

alt.data_transformers.disable_max_rows()

st.set_page_config(page_title="UK Interest Rates Pipeline", page_icon="📈", layout="wide")


# --------------------------------------------------------------------------- data
@st.cache_data(show_spinner=False)
def load() -> dict:
    def read(name: str) -> pd.DataFrame:
        return pd.read_parquet(DATA_DIR / f"{name}.parquet")

    decisions = read("fct_bank_rate_decisions")
    decisions["effective_date"] = pd.to_datetime(decisions["effective_date"])

    reaction = read("fct_decision_market_reaction")
    reaction["effective_date"] = pd.to_datetime(reaction["effective_date"])

    curve = read("fct_yield_curve_daily")
    curve["observed_on"] = pd.to_datetime(curve["observed_on"])

    monthly = read("fct_monthly_macro")
    monthly["month"] = pd.to_datetime(monthly["month"])

    meta = json.loads((DATA_DIR / "meta.json").read_text())
    return {
        "decisions": decisions.sort_values("effective_date"),
        "reaction": reaction.sort_values("effective_date"),
        "curve": curve.sort_values("observed_on"),
        "monthly": monthly.sort_values("month"),
        "meta": meta,
    }


def bank_rate_path(decisions: pd.DataFrame, end: pd.Timestamp) -> pd.DataFrame:
    """Step series from the decision log: opening rate, every change, then today."""
    first = decisions.iloc[0]
    rows = [{"date": pd.Timestamp("1975-01-02"), "rate": first["previous_rate"]}]
    rows += [
        {"date": d, "rate": r}
        for d, r in zip(decisions["effective_date"], decisions["new_rate"], strict=True)
    ]
    rows.append({"date": end, "rate": decisions.iloc[-1]["new_rate"]})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------- charts
def line_chart(
    wide: pd.DataFrame,
    x: str,
    series: dict[str, str],
    y_title: str,
    fmt: str = ".2f",
    height: int = 340,
    step: bool = False,
    zero_rule: bool = False,
) -> alt.LayerChart:
    """Multi-series line chart with a crosshair tooltip showing every series.

    `series` maps column name -> display label, in palette order.
    """
    labels = list(series.values())
    long = wide.melt(id_vars=[x], value_vars=list(series), var_name="key", value_name="value")
    long["series"] = long["key"].map(series)
    # keep nulls: "break-paths" mode breaks the line at gaps instead of bridging them

    span_days = (wide[x].max() - wide[x].min()).days if len(wide) else 0
    x_axis = alt.Axis(
        format="%Y" if span_days > 3 * 365 else "%b %Y",
        labelOverlap=True,
        tickCount="year" if span_days > 3 * 365 else "month",
    )

    color = alt.Color(
        "series:N",
        scale=alt.Scale(domain=labels, range=SLOT[: len(labels)]),
        legend=alt.Legend(title=None, orient="top") if len(labels) > 1 else None,
    )
    lines = (
        alt.Chart(long)
        .mark_line(
            strokeWidth=2,
            interpolate="step-after" if step else "linear",
            invalid="break-paths-show-domains",
        )
        .encode(
            x=alt.X(f"{x}:T", title=None, axis=x_axis),
            y=alt.Y("value:Q", title=y_title, scale=alt.Scale(zero=False)),
            color=color,
        )
    )

    hover = alt.selection_point(fields=[x], nearest=True, on="pointerover", empty=False)
    tooltip = [alt.Tooltip(f"{x}:T", title="Date")] + [
        alt.Tooltip(f"{col}:Q", title=label, format=fmt) for col, label in series.items()
    ]
    rule = (
        alt.Chart(wide)
        .mark_rule(strokeWidth=1)
        .encode(
            x=f"{x}:T",
            opacity=alt.condition(hover, alt.value(0.35), alt.value(0)),
            tooltip=tooltip,
        )
        .add_params(hover)
    )
    dots = (
        lines.mark_point(filled=True, size=60)
        .encode(opacity=alt.condition(hover, alt.value(1), alt.value(0)))
        .transform_filter(hover)
    )
    layers = [lines, rule, dots]
    if zero_rule:
        layers.insert(0, alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(opacity=0.4).encode(y="y:Q"))
    return alt.layer(*layers).properties(height=height)


def show(chart) -> None:
    st.altair_chart(chart, width="stretch")


def year_range(key: str, first: int, last: int, default_start: int) -> tuple[int, int]:
    return st.slider("Years", first, last, (max(first, default_start), last), key=key)


def fmt_bp(v: float) -> str:
    return f"{v:+.0f}bp"


# ---------------------------------------------------------------------------- app
d = load()
decisions, reaction, curve, monthly, meta = (
    d["decisions"],
    d["reaction"],
    d["curve"],
    d["monthly"],
    d["meta"],
)
today = pd.Timestamp(date.today())
latest_br = meta["series_latest"].get("IUDBEDR", {}).get("latest", "?")

st.title("UK Interest Rates Pipeline")
st.markdown("##### 50 years of Bank of England data, from Bank Rate to your mortgage")
st.caption(
    f"Bank of England data, latest Bank Rate observation {latest_br}. "
    f"Refreshed {meta['exported_at'][:10]} by an automated pipeline "
    f"([dlt → DuckDB → dbt]({REPO_URL}))."
)

# --- headline numbers --------------------------------------------------------
last_dec = decisions.iloc[-1]
c_last = curve.dropna(subset=["gilt_10y"])
m_mort = monthly.dropna(subset=["mortgage_2y_75ltv"])
m_fx = monthly.dropna(subset=["gbp_usd_eom"])
m_m4 = monthly.dropna(subset=["m4_growth_12m"])

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric(
    "Bank Rate",
    f"{last_dec['new_rate']:.2f}%",
    f"{fmt_bp(last_dec['change_bps'])} on {last_dec['effective_date']:%d %b %Y}",
    delta_color="off",
)
gilt_now, gilt_prev = c_last.iloc[-1], c_last.iloc[max(0, len(c_last) - 22)]
k2.metric(
    "10y gilt yield",
    f"{gilt_now['gilt_10y']:.2f}%",
    f"{fmt_bp((gilt_now['gilt_10y'] - gilt_prev['gilt_10y']) * 100)} over ~1 month",
    delta_color="off",
)
k3.metric(
    "2y fixed mortgage (75% LTV)",
    f"{m_mort.iloc[-1]['mortgage_2y_75ltv']:.2f}%",
    f"{fmt_bp((m_mort.iloc[-1]['mortgage_2y_75ltv'] - m_mort.iloc[-2]['mortgage_2y_75ltv']) * 100)}"
    f" vs {m_mort.iloc[-2]['month']:%b}",
    delta_color="off",
)
k4.metric(
    "GBP/USD",
    f"{m_fx.iloc[-1]['gbp_usd_eom']:.4f}",
    f"{m_fx.iloc[-1]['gbp_usd_mom_pct']:+.2f}% this month",
    delta_color="off",
)
k5.metric(
    "M4 money growth (12m)",
    f"{m_m4.iloc[-1]['m4_growth_12m']:.1f}%",
    f"{m_m4.iloc[-1]['m4_growth_12m'] - m_m4.iloc[-2]['m4_growth_12m']:+.1f}pp vs "
    f"{m_m4.iloc[-2]['month']:%b}",
    delta_color="off",
)

tab_rate, tab_mort, tab_gilt, tab_money, tab_data = st.tabs(
    ["Bank Rate", "Mortgage pass-through", "Gilt curve", "Sterling & money", "Data"]
)

# --- Bank Rate ---------------------------------------------------------------
with tab_rate:
    y0, y1 = year_range("rate_years", 1975, today.year, 1975)
    path = bank_rate_path(decisions, today)
    path = path[(path["date"].dt.year >= y0) & (path["date"].dt.year <= y1)]
    show(line_chart(path, "date", {"rate": "Bank Rate"}, "Percent", step=True))

    in_range = decisions[decisions["effective_date"].dt.year.between(y0, y1)]
    a, b, c = st.columns(3)
    a.metric("Rate changes in range", len(in_range))
    b.metric(
        "Hikes / cuts",
        f"{(in_range.direction == 'hike').sum()} / {(in_range.direction == 'cut').sum()}",
    )
    if len(in_range):
        c.metric("Range of Bank Rate", f"{path['rate'].min():.2f}% – {path['rate'].max():.2f}%")

    left, right = st.columns([3, 2])
    with left:
        st.subheader("Hikes and cuts by decade")
        dec = decisions.assign(
            decade=(decisions["effective_date"].dt.year // 10 * 10).astype(str) + "s"
        )
        counts = dec.groupby(["decade", "direction"]).size().reset_index(name="changes")
        show(
            alt.Chart(counts)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("decade:N", title=None),
                xOffset=alt.XOffset("direction:N", sort=["hike", "cut"]),
                y=alt.Y("changes:Q", title="Number of changes"),
                color=alt.Color(
                    "direction:N",
                    scale=alt.Scale(domain=["hike", "cut"], range=SLOT[:2]),
                    legend=alt.Legend(title=None, orient="top"),
                ),
                tooltip=["decade", "direction", "changes"],
            )
            .properties(height=300)
        )
    with right:
        st.subheader("Most recent changes")
        st.dataframe(
            decisions.sort_values("effective_date", ascending=False)
            .head(12)[["effective_date", "previous_rate", "new_rate", "change_bps"]]
            .rename(
                columns={
                    "effective_date": "Date",
                    "previous_rate": "From %",
                    "new_rate": "To %",
                    "change_bps": "Change (bp)",
                }
            ),
            hide_index=True,
            width="stretch",
            column_config={"Date": st.column_config.DateColumn(format="D MMM YYYY")},
        )

# --- Mortgage pass-through ---------------------------------------------------
with tab_mort:
    st.markdown(
        "Quoted 2-year fixed mortgage rates against Bank Rate. Quoted rates are monthly "
        "averages, so they're compared with the monthly-average Bank Rate."
    )
    first_mort = int(m_mort["month"].dt.year.min())
    y0, y1 = year_range("mort_years", first_mort, today.year, 2007)
    mm = monthly[monthly["month"].dt.year.between(max(y0, first_mort), y1)]
    show(
        line_chart(
            mm,
            "month",
            {
                "bank_rate_avg": "Bank Rate (avg)",
                "mortgage_2y_75ltv": "2y fixed, 75% LTV",
                "mortgage_2y_90ltv": "2y fixed, 90% LTV",
            },
            "Percent",
        )
    )

    st.subheader("Lender margin over Bank Rate")
    st.caption("2y fixed (75% LTV) minus monthly-average Bank Rate, in basis points.")
    show(
        line_chart(
            mm,
            "month",
            {"mortgage_75ltv_spread_bps": "Spread"},
            "Basis points",
            fmt=".0f",
            height=240,
            zero_rule=True,
        )
    )

    st.subheader("How mortgage rates moved after each Bank Rate change")
    rx = reaction[
        (reaction["effective_date"].dt.year.between(y0, y1))
        & reaction["mortgage_move_3m_bps"].notna()
    ]
    if rx.empty:
        st.info("No completed 3-month windows in this range.")
    else:
        cols = st.columns(2)
        for col, direction in zip(cols, ["cut", "hike"], strict=True):
            sub = rx[rx["direction"] == direction]
            if len(sub):
                col.metric(
                    f"Average 3-month move after a {direction}",
                    fmt_bp(sub["mortgage_move_3m_bps"].mean()),
                    f"{len(sub)} {direction}s, avg size {fmt_bp(sub['change_bps'].mean())}",
                    delta_color="off",
                )
        show(
            alt.Chart(rx)
            .mark_circle(size=90, opacity=0.85, stroke="white", strokeWidth=1)
            .encode(
                x=alt.X("change_bps:Q", title="Bank Rate change (bp)"),
                y=alt.Y("mortgage_move_3m_bps:Q", title="2y fixed move over 3 months (bp)"),
                color=alt.value(SLOT[0]),
                tooltip=[
                    alt.Tooltip("effective_date:T", title="Change on", format="%d %b %Y"),
                    alt.Tooltip("change_bps:Q", title="Bank Rate (bp)"),
                    alt.Tooltip(
                        "mortgage_2y_75ltv_before:Q", title="Mortgage before %", format=".2f"
                    ),
                    alt.Tooltip(
                        "mortgage_2y_75ltv_after_3m:Q", title="3 months after %", format=".2f"
                    ),
                    alt.Tooltip("mortgage_move_3m_bps:Q", title="Move (bp)", format=".0f"),
                ],
            )
            .properties(height=320)
        )

# --- Gilt curve --------------------------------------------------------------
with tab_gilt:
    first_gilt = int(curve["observed_on"].dt.year.min())
    y0, y1 = year_range("gilt_years", first_gilt, today.year, 2015)
    cv = curve[curve["observed_on"].dt.year.between(y0, y1)]
    if y1 - y0 > 6:  # weekly closes keep long ranges light and readable
        cv = (
            cv.set_index("observed_on")
            .resample("W-FRI")
            .last()
            .dropna(subset=["gilt_10y"])
            .reset_index()
        )
    show(
        line_chart(
            cv,
            "observed_on",
            {
                "bank_rate": "Bank Rate",
                "gilt_5y": "5y gilt",
                "gilt_10y": "10y gilt",
                "gilt_20y": "20y gilt",
            },
            "Percent",
        )
    )

    st.subheader("Curve slope: 10y minus 5y")
    st.caption(
        "Below zero, long-dated borrowing is cheaper than medium-dated: markets "
        "expect rates to fall."
    )
    show(
        line_chart(
            cv,
            "observed_on",
            {"slope_10y_5y_bps": "10y − 5y"},
            "Basis points",
            fmt=".0f",
            height=240,
            zero_rule=True,
        )
    )

    st.subheader("Market reaction to recent Bank Rate changes")
    st.caption(
        "10y gilt and GBP/USD from the last close before the change to 5 business days "
        "after; mortgage from the month before to 3 months after."
    )
    recent = reaction.sort_values("effective_date", ascending=False).head(12)
    st.dataframe(
        recent[
            [
                "effective_date",
                "change_bps",
                "gilt_10y_move_bps",
                "gbp_usd_move_pct",
                "mortgage_move_3m_bps",
            ]
        ].rename(
            columns={
                "effective_date": "Date",
                "change_bps": "Bank Rate (bp)",
                "gilt_10y_move_bps": "10y gilt (bp)",
                "gbp_usd_move_pct": "GBP/USD (%)",
                "mortgage_move_3m_bps": "2y fixed, 3m (bp)",
            }
        ),
        hide_index=True,
        width="stretch",
        column_config={
            "Date": st.column_config.DateColumn(format="D MMM YYYY"),
            "10y gilt (bp)": st.column_config.NumberColumn(format="%+.0f"),
            "GBP/USD (%)": st.column_config.NumberColumn(format="%+.2f"),
            "2y fixed, 3m (bp)": st.column_config.NumberColumn(format="%+.0f"),
        },
    )
    st.caption("Blank cells: the window hasn't completed yet.")

# --- Sterling & money --------------------------------------------------------
with tab_money:
    y0, y1 = year_range("money_years", 1975, today.year, 1999)
    mm = monthly[monthly["month"].dt.year.between(y0, y1)]
    st.subheader("Sterling, end of month")
    show(
        line_chart(
            mm,
            "month",
            {"gbp_usd_eom": "GBP/USD", "gbp_eur_eom": "GBP/EUR"},
            "Foreign currency per £1",
            fmt=".4f",
        )
    )
    st.subheader("Broad money (M4), 12-month growth")
    show(
        line_chart(
            mm,
            "month",
            {"m4_growth_12m": "M4 growth"},
            "Percent",
            fmt=".1f",
            height=260,
            zero_rule=True,
        )
    )

# --- Data --------------------------------------------------------------------
with tab_data:
    st.markdown(
        f"All figures come from the [Bank of England Database]"
        f"(https://www.bankofengland.co.uk/boeapps/database/). The pipeline, models and "
        f"tests are in the [GitHub repo]({REPO_URL})."
    )
    latest = pd.DataFrame(
        [
            {"Series code": k, "Name": v["name"], "Latest observation": v["latest"]}
            for k, v in meta["series_latest"].items()
        ]
    )
    st.dataframe(latest, hide_index=True, width="stretch", height=35 * (len(latest) + 1) + 3)

    st.subheader("Download the marts")
    downloads = {
        "Bank Rate decisions": decisions,
        "Market reaction to decisions": reaction,
        "Daily yield curve": curve,
        "Monthly macro panel": monthly,
    }
    cols = st.columns(len(downloads))
    for col, (label, df) in zip(cols, downloads.items(), strict=True):
        col.download_button(
            f"{label} (CSV)",
            df.to_csv(index=False).encode(),
            file_name=label.lower().replace(" ", "_") + ".csv",
            mime="text/csv",
            width="stretch",
        )

st.caption("Source: Bank of England. Not investment advice.")
