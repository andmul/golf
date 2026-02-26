import reflex as rx
import pandas as pd
import plotly.graph_objects as go
import os

# ==============================================================================
# Load data ONCE
# ==============================================================================
BASE_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE_DIR, "data", "data.csv")
print(f"Loading data from: {DATA_PATH}")

try:
    df_base = pd.read_csv(DATA_PATH, index_col=0)
    df_base = df_base.reset_index(drop=True)
    df_base["Datum"] = pd.to_datetime(df_base["Datum"], errors="coerce")
    df_base = df_base.dropna(subset=["Datum"])
    print(f"Loaded {len(df_base)} rows.")
except Exception as e:
    print(f"Error loading data: {e}")
    # Initialize empty DataFrame to avoid crash if file missing or corrupt
    df_base = pd.DataFrame(columns=["Datum", "Turnier", "Club", "Spielmodus", "HCP", "Brutto", "Par", "uPar"])

# ==============================================================================
# Helpers
# ==============================================================================
def build_hovertext(df):
    return df.apply(
        lambda r: (
            f"<b>Date:</b> {r['Datum'].strftime('%d-%m-%y')}<br>"
            f"<b>Turnier:</b> {r.get('Turnier', '–')}<br>"
            f"<b>Club:</b> {r.get('Club', '–')}<br>"
            f"<b>Spielmodus:</b> {r.get('Spielmodus', '–')}<br>"
            f"<b>HCP:</b> {r.get('HCP', 0)}<br>"
            f"<b>Brutto:</b> {int(r.get('Brutto', 0)) if pd.notna(r.get('Brutto')) else 0}<br>"
            f"<b>Par:</b> "
            f"{r.get('Par')} / {int(r['uPar']):+d}"
            if not pd.isna(r.get("uPar"))
            else f"{r.get('Par')}"
        ),
        axis=1,
    )

def build_figure(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure().update_layout(
            title="Keine Daten verfügbar",
            template="plotly_white",
        )

    required = {"Datum", "HCP"}
    missing = required - set(df.columns)
    if missing:
        # Should not happen given data loading, but good for safety
        print(f"Missing columns: {missing}")
        return go.Figure()

    df = df.sort_values("Datum").reset_index(drop=True)
    df["ContinuousIndex"] = range(len(df))
    df["HoverText"] = build_hovertext(df)

    hcp_min, hcp_max = df["HCP"].min(), df["HCP"].max()
    # Ensure hcp_min/max are not NaN
    if pd.isna(hcp_min) or pd.isna(hcp_max):
        hcp_min, hcp_max = 0, 36

    hcp_pad = max((hcp_max - hcp_min) * 0.15, 1)

    fig = go.Figure()

    # HCP line
    fig.add_trace(go.Scatter(
        x=df["ContinuousIndex"],
        y=df["HCP"],
        mode="lines+markers",
        line=dict(color="#2C7BE5", width=2.5),
        marker=dict(size=7, line=dict(width=1, color="white")),
        text=df["HoverText"],
        hoverinfo="text",
        name="HCP",
    ))

    # Brutto bars
    fig.add_trace(go.Bar(
        x=df["ContinuousIndex"],
        y=df["Brutto"],
        width=0.45,
        marker=dict(color="rgba(80,200,120,0.75)"),
        text=[int(v) if v > 0 else "" for v in df["Brutto"].fillna(0)],
        textposition="inside",
        hovertext=df["HoverText"],
        hoverinfo="text",
        name="Brutto",
        yaxis="y2",
    ))

    # Winter breaks
    # Calculate gaps > 50 days
    gaps = df["Datum"].diff().dt.days > 50
    for i in df.index[gaps]:
        # i is index in sorted df with ContinuousIndex
        if i > 0:
            x = (df.loc[i - 1, "ContinuousIndex"] + df.loc[i, "ContinuousIndex"]) / 2
            fig.add_vline(x=x, line_dash="dot", line_color="firebrick", opacity=0.5)
            fig.add_annotation(
                x=x, y=1.06, xref="x", yref="paper",
                text="⛄ Winter", showarrow=False,
                font=dict(size=10, color="firebrick"),
            )

    # Determine safe Brutto range
    max_brutto = df["Brutto"].max()
    if pd.isna(max_brutto) or max_brutto == 0:
        y2_range = [0, 50]
    else:
        y2_range = [0, max_brutto * 1.1]

    fig.update_layout(
        height=650,
        template="plotly_white",
        hovermode="x unified",
        bargap=0.2,
        showlegend=False,
        title=dict(text="Turniere & Handicap-Verlauf", x=0.5),
        dragmode="pan",  # Enable panning by default
        xaxis=dict(
            tickvals=df["ContinuousIndex"],
            ticktext=df["Datum"].dt.strftime("%d-%m-%y"),
            tickangle=45,
            rangeslider=dict(visible=True, thickness=0.06),
            range=[-0.5, len(df) - 0.5],
            fixedrange=False,
        ),
        yaxis=dict(
            title="HCP",
            range=[hcp_min - hcp_pad, hcp_max + hcp_pad],
            fixedrange=True,  # Disable vertical zoom/pan
        ),
        yaxis2=dict(
            title="Brutto",
            overlaying="y",
            side="right",
            range=y2_range,
            fixedrange=True,  # Disable vertical zoom/pan
        ),
    )

    return fig

# ==============================================================================
# Reflex State
# ==============================================================================
class AppState(rx.State):
    nur_turniere_mit_ergebnis: bool = False
    nur_individuell: bool = False

    @rx.var
    def filtered_df(self) -> pd.DataFrame:
        df = df_base.copy()

        if self.nur_turniere_mit_ergebnis:
            # Filter rows where Brutto is not 0 and not NaN
            df = df[(df["Brutto"].fillna(0) != 0)]

        if self.nur_individuell:
            # Filter rows where Spielmodus starts with "Einzel"
            df = df[df["Spielmodus"].str.startswith("Einzel", na=False)]

        return df.reset_index(drop=True)

    @rx.var
    def row_count(self) -> int:
        return len(self.filtered_df)

    @rx.var
    def figure(self) -> go.Figure:
        return build_figure(self.filtered_df)

# ==============================================================================
# UI
# ==============================================================================
def index():
    return rx.container(
        rx.heading("🏌️ Turnier-Analyse", size="3"),

        rx.hstack(
            rx.checkbox(
                "nur Turniere mit Ergebnis",
                checked=AppState.nur_turniere_mit_ergebnis,
                on_change=AppState.set_nur_turniere_mit_ergebnis,
            ),
            rx.checkbox(
                "nur individuelle Ergebnisse",
                checked=AppState.nur_individuell,
                on_change=AppState.set_nur_individuell,
            ),
            spacing="5",
            padding="1em",
            background="gray.50",
            border_radius="8px",
        ),

        rx.text(
            f"Anzahl Turniere: ",
            rx.text.strong(AppState.row_count),
            color="gray.600",
        ),

        rx.plotly(data=AppState.figure),

        max_width="1450px",
        padding="2em",
    )

app = rx.App()
app.add_page(index)
