import os
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ------------------------------------------------------------------ config
PARLOUR = "Fresh and Slim"
OWNER = "Ms. Rina"
CURRENCY = "৳"
COMMISSION_RATE = 0.02  # only used if the sheet's commission column is empty
SHEET_NAME = "Entries"

ACCENT = "#22D3EE"
ACCENT2 = "#A78BFA"
GOOD = "#34D399"
PALETTE = [ACCENT, ACCENT2, GOOD, "#F472B6", "#FBBF24", "#60A5FA", "#FB923C", "#94A3B8"]

st.set_page_config(page_title=f"{PARLOUR} | Dashboard", page_icon="💅", layout="wide")

st.markdown(
    f"""
<style>
.block-container {{padding-top: 1.4rem; max-width: 1250px;}}
.hero {{padding: 18px 22px; border-radius: 14px; margin-bottom: 14px;
  background: linear-gradient(120deg, #0B1220 0%, #111C33 55%, #1B1442 100%);
  border: 1px solid #1E293B;}}
.hero h1 {{margin: 0; font-size: 1.7rem; letter-spacing: .5px;}}
.hero h1 span {{color: {ACCENT};}}
.hero p {{margin: 2px 0 0 0; color: #94A3B8; font-size: .9rem;}}
div[data-testid="stMetric"] {{background: #0F172A; border: 1px solid #1E293B;
  border-left: 3px solid {ACCENT}; padding: 12px 16px; border-radius: 10px;}}
div[data-testid="stMetricValue"] {{font-size: 1.6rem;}}
.stTabs [data-baseweb="tab"] {{font-weight: 600; letter-spacing: .4px;}}
</style>
<div class="hero"><h1>💅 <span>{PARLOUR}</span> · Live Dashboard</h1>
<p>Owner: {OWNER} &nbsp;|&nbsp; Data: Google Sheet (auto-refresh every minute)</p></div>
""",
    unsafe_allow_html=True,
)


def money(x: float) -> str:
    return f"{CURRENCY}{x:,.0f}"


# ------------------------------------------------------------------ data
def _sheet_id() -> str:
    try:
        sid = st.secrets.get("SHEET_ID", "")
    except Exception:
        sid = ""
    return sid or os.environ.get("SHEET_ID", "")


@st.cache_data(ttl=60, show_spinner="Sheet theke data ashche...")
def load_raw(sheet_id: str) -> tuple[pd.DataFrame, str]:
    if sheet_id:
        url = (f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq"
               f"?tqx=out:csv&sheet={SHEET_NAME}")
        return pd.read_csv(url, dtype=str), "Google Sheet (live)"
    here = os.path.dirname(os.path.abspath(__file__))
    return pd.read_csv(os.path.join(here, "demo_data.csv"), dtype=str), "Demo data (SHEET_ID set kora nai)"


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.iloc[:, :10].copy()
    df.columns = ["Date", "CustomerNo", "CustomerName", "Entry", "Exit", "Service",
                  "Amount", "Employee", "Commission", "Duration"][: df.shape[1]]
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
    df = df[df["Date"].notna() & df["Entry"].notna() & (df["Entry"].astype(str).str.strip() != "")].copy()
    comm = pd.to_numeric(df.get("Commission"), errors="coerce")
    df["Commission"] = comm.where(comm.notna(), df["Amount"] * COMMISSION_RATE)
    df["Employee"] = df["Employee"].fillna("").astype(str).str.strip().replace("", "Unassigned")
    df["Service"] = df["Service"].fillna("").astype(str).str.strip().replace("", "Other")
    df["Duration"] = pd.to_numeric(df.get("Duration"), errors="coerce")
    df["Year"], df["Month"] = df["Date"].dt.year, df["Date"].dt.month
    df["Day"] = df["Date"].dt.date
    return df.sort_values(["Date", "Entry"]).reset_index(drop=True)


def style(fig, h=340):
    fig.update_layout(height=h, margin=dict(l=8, r=8, t=36, b=8), template="plotly_dark",
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#CBD5E1"), legend=dict(orientation="h", y=-0.2),
                      colorway=PALETTE)
    fig.update_xaxes(gridcolor="#1E293B")
    fig.update_yaxes(gridcolor="#1E293B")
    return fig


def employee_table(d: pd.DataFrame) -> pd.DataFrame:
    t = (d.groupby("Employee")
          .agg(Jobs=("Amount", "size"), Earning=("Amount", "sum"), Commission=("Commission", "sum"))
          .sort_values("Earning", ascending=False).reset_index())
    return t


def emp_chart(t: pd.DataFrame, title: str):
    fig = go.Figure()
    fig.add_bar(x=t["Employee"], y=t["Jobs"], name="Jobs", marker_color=ACCENT,
                text=t["Jobs"], textposition="outside")
    fig.update_layout(title=title)
    return style(fig, 300)


def emp_cfg():
    return {"Earning": st.column_config.NumberColumn(f"Earning ({CURRENCY})", format="%d"),
            "Commission": st.column_config.NumberColumn(f"Commission ({CURRENCY})", format="%.2f")}


def kpis(d: pd.DataFrame, label_days: str | None = None):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Customers", f"{len(d):,}")
    c2.metric("Total Earning", money(d["Amount"].sum()))
    c3.metric("Commission Payable", f"{CURRENCY}{d['Commission'].sum():,.2f}")
    avg = d["Amount"].mean() if len(d) else 0
    c4.metric("Avg / Customer", money(avg))


# ------------------------------------------------------------------ load
try:
    raw, source = load_raw(_sheet_id())
    data = clean(raw)
except Exception as exc:  # network / permission / format problems
    st.error("Google Sheet theke data load hoy nai. Sheet **'Anyone with the link - Viewer'** kora ache kina ar SHEET_ID thik ache kina dekhun.")
    st.caption(f"Technical detail: {exc}")
    st.stop()

with st.sidebar:
    st.markdown(f"### {PARLOUR}")
    st.caption(source)
    if st.button("🔄 Refresh now"):
        load_raw.clear()
        st.rerun()
    st.caption(f"Total entries: {len(data):,}")

if data.empty:
    st.info("Ekhono kono entry nai. Google Sheet a Date + Entry Time likhun.")
    st.stop()

tab_d, tab_m, tab_y = st.tabs(["📅 Daily", "🗓️ Monthly", "📈 Yearly"])

# ------------------------------------------------------------------ daily
with tab_d:
    days = sorted(data["Day"].unique())
    pick = st.date_input("Date", value=days[-1], min_value=days[0], max_value=max(days[-1], date.today()),
                         key="day")
    d = data[data["Day"] == pick]
    if d.empty:
        st.warning("Ei din e kono customer entry nai.")
    else:
        kpis(d)
        c1, c2 = st.columns([1, 1])
        t = employee_table(d)
        with c1:
            st.markdown("##### Ke koita kaj korse")
            st.dataframe(t, hide_index=True, column_config=emp_cfg())
            st.plotly_chart(emp_chart(t, "Jobs per employee"))
        with c2:
            sv = d.groupby("Service")["Amount"].sum().reset_index()
            fig = px.pie(sv, names="Service", values="Amount", hole=0.55, title="Earning by service")
            st.plotly_chart(style(fig, 420))
        st.markdown("##### Customer list")
        show = d[["CustomerNo", "CustomerName", "Entry", "Exit", "Service", "Employee", "Amount", "Commission"]]
        show = show.rename(columns={"CustomerNo": "Customer", "CustomerName": "Name", "Amount": f"Amount ({CURRENCY})",
                                    "Commission": f"Commission ({CURRENCY})"})
        st.dataframe(show, hide_index=True)

    st.markdown("##### Last 7 days")
    in_week = (data["Date"] >= pd.Timestamp(pick) - pd.Timedelta(days=6)) & (data["Date"] <= pd.Timestamp(pick))
    last = (data[in_week]
            .groupby("Day").agg(Customers=("Amount", "size"), Earning=("Amount", "sum")).reset_index())
    if not last.empty:
        fig = go.Figure()
        fig.add_bar(x=last["Day"].astype(str), y=last["Earning"], name="Earning", marker_color=ACCENT)
        fig.add_scatter(x=last["Day"].astype(str), y=last["Customers"], name="Customers", yaxis="y2",
                        mode="lines+markers", line=dict(color=ACCENT2, width=3))
        fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False, title="Customers"),
                          yaxis=dict(title=f"Earning ({CURRENCY})"))
        st.plotly_chart(style(fig, 320))

# ------------------------------------------------------------------ monthly
with tab_m:
    ym = sorted({(y, m) for y, m in zip(data["Year"], data["Month"])})
    labels = [f"{date(y, m, 1):%B %Y}" for y, m in ym]
    sel = st.selectbox("Month", labels, index=len(labels) - 1)
    y, m = ym[labels.index(sel)]
    d = data[(data["Year"] == y) & (data["Month"] == m)]
    kpis(d)
    daily = d.groupby("Day").agg(Customers=("Amount", "size"), Earning=("Amount", "sum")).reset_index()
    c1, c2, c3 = st.columns(3)
    best = daily.loc[daily["Earning"].idxmax()]
    c1.metric("Best day", f"{best['Day']:%d %b}", money(best["Earning"]))
    c2.metric("Working days", f"{len(daily)}")
    c3.metric("Avg earning / day", money(daily["Earning"].mean()))
    fig = go.Figure()
    fig.add_bar(x=daily["Day"].astype(str), y=daily["Earning"], name="Earning", marker_color=ACCENT)
    fig.add_scatter(x=daily["Day"].astype(str), y=daily["Customers"], name="Customers", yaxis="y2",
                    mode="lines+markers", line=dict(color=ACCENT2, width=3))
    fig.update_layout(title="Daily earning & customers", yaxis2=dict(overlaying="y", side="right", showgrid=False),
                      yaxis=dict(title=f"Earning ({CURRENCY})"))
    st.plotly_chart(style(fig, 360))
    c1, c2 = st.columns(2)
    t = employee_table(d)
    with c1:
        st.markdown("##### Employee summary (jobs, earning, commission)")
        st.dataframe(t, hide_index=True, column_config=emp_cfg())
    with c2:
        sv = d.groupby("Service").agg(Customers=("Amount", "size"), Earning=("Amount", "sum")) \
              .sort_values("Earning", ascending=False).reset_index()
        fig = px.bar(sv, x="Earning", y="Service", orientation="h", title="Earning by service")
        fig.update_yaxes(autorange="reversed")
        fig.update_traces(marker_color=ACCENT2)
        st.plotly_chart(style(fig, 340))

# ------------------------------------------------------------------ yearly
with tab_y:
    years = sorted(data["Year"].unique())
    yr = st.selectbox("Year", years, index=len(years) - 1)
    d = data[data["Year"] == yr]
    kpis(d)
    mo = d.groupby("Month").agg(Customers=("Amount", "size"), Earning=("Amount", "sum"),
                                Commission=("Commission", "sum")).reindex(range(1, 13), fill_value=0).reset_index()
    mo["Name"] = [f"{date(2000, k, 1):%b}" for k in mo["Month"]]
    c1, c2 = st.columns(2)
    top = mo.loc[mo["Earning"].idxmax()]
    c1.metric("Best month", top["Name"], money(top["Earning"]))
    c2.metric("Avg earning / active month", money(mo.loc[mo["Earning"] > 0, "Earning"].mean()))
    fig = go.Figure()
    fig.add_bar(x=mo["Name"], y=mo["Earning"], name="Earning", marker_color=ACCENT)
    fig.add_scatter(x=mo["Name"], y=mo["Customers"], name="Customers", yaxis="y2", mode="lines+markers",
                    line=dict(color=ACCENT2, width=3))
    fig.update_layout(title=f"Monthly earning {yr}", yaxis2=dict(overlaying="y", side="right", showgrid=False),
                      yaxis=dict(title=f"Earning ({CURRENCY})"))
    st.plotly_chart(style(fig, 360))
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Month-wise summary")
        out = mo[["Name", "Customers", "Earning", "Commission"]].rename(columns={"Name": "Month"})
        st.dataframe(out, hide_index=True, column_config=emp_cfg())
    with c2:
        st.markdown("##### Employee summary (full year)")
        st.dataframe(employee_table(d), hide_index=True, column_config=emp_cfg())
