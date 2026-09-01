"""Plotly grafikleri. Renkler CVD-guvenli (renk koru dostu) dogrulanmis bir paletten
geliyor; sira onemli, rastgele renk secmiyoruz. Tek eksen kurali: asla ikinci y ekseni yok.
"""

import plotly.graph_objects as go

# koyu tema yuzeyleri ve murekkep tonlari
SURFACE = "#1a1a19"
GRID = "#2c2c2a"
AXIS = "#383835"
INK = "#ffffff"
INK2 = "#c3c2b7"
MUTED = "#898781"

# kategorik seri renkleri (sabit sira: 1. seri hep mavi, 2. hep turuncu...)
SERIES = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181"]

# ayrisan (diverging) uclar: negatif kirmizi, pozitif mavi, orta notr gri
NEG = "#e66767"
POS = "#3987e5"
MID = "#383835"

FONT = 'system-ui, "Segoe UI", sans-serif'


def _layout(fig, title, pct=False, show_legend=False):
    fig.update_layout(
        title=dict(text=title, font=dict(color=INK, size=15)),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font=dict(color=INK2, family=FONT, size=12),
        margin=dict(l=55, r=20, t=50, b=40),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#0d0d0d", bordercolor=AXIS),
        showlegend=show_legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1),
        height=340,
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False,
                     tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False,
                     tickfont=dict(color=MUTED),
                     tickformat=".0%" if pct else None)
    return fig


def line_chart(series_map, title, pct=False, dashed=(), refline=None, hover_fmt=".3f"):
    """Bir veya birkac cizgi. series_map: {isim: Series}. dashed: kesikli cizilecekler."""
    fig = go.Figure()
    for i, (name, s) in enumerate(series_map.items()):
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, name=name, mode="lines",
            line=dict(color=SERIES[i], width=2,
                      dash="dot" if name in dashed else "solid"),
            hovertemplate="%{y:" + (".2%" if pct else hover_fmt) + "}<extra>" + name + "</extra>",
        ))
    if refline is not None:
        fig.add_hline(y=refline, line_dash="dash", line_color=MUTED, line_width=1)
    return _layout(fig, title, pct=pct, show_legend=len(series_map) > 1)


def underwater_chart(dd, title="Underwater Plot — Drawdown from Peak"):
    """Zirveden dusus grafigi: tek seri, negatif bolge kirmizi dolgulu."""
    fig = go.Figure(go.Scatter(
        x=dd.index, y=dd.values, mode="lines",
        line=dict(color=NEG, width=1.5),
        fill="tozeroy", fillcolor="rgba(230,103,103,0.25)",
        hovertemplate="%{y:.2%}<extra></extra>",
    ))
    return _layout(fig, title, pct=True)


def monthly_heatmap(table, title="Monthly Returns"):
    """Yil x ay isi haritasi. Ayrisan skala: kayip kirmizi, kazanc mavi, sifir notr."""
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig = go.Figure(go.Heatmap(
        z=table.values,
        x=[months[m - 1] for m in table.columns],
        y=[str(y) for y in table.index],
        colorscale=[[0, NEG], [0.5, MID], [1, POS]],
        zmid=0, xgap=2, ygap=2,  # hucreler arasi 2px yuzey bosluğu
        colorbar=dict(tickformat=".0%", outlinewidth=0),
        hovertemplate="%{y} %{x}: %{z:.2%}<extra></extra>",
    ))
    fig = _layout(fig, title)
    fig.update_layout(hovermode="closest")
    fig.update_xaxes(gridcolor=SURFACE)
    fig.update_yaxes(gridcolor=SURFACE, autorange="reversed")
    return fig


def loadings_bar(loadings, title="Fama-French 5-Factor Loadings (b)"):
    """Faktor katsayilari: her faktor kendi sabit rengini alir, uclarda deger etiketi."""
    fig = go.Figure(go.Bar(
        x=list(loadings.index), y=list(loadings.values),
        marker=dict(color=SERIES[:len(loadings)]),
        text=[f"{v:+.2f}" for v in loadings.values],
        textposition="outside", textfont=dict(color=INK2, size=11),
        hovertemplate="%{x}: %{y:.4f}<extra></extra>",
    ))
    fig.add_hline(y=0, line_color=AXIS, line_width=1)
    fig = _layout(fig, title)
    fig.update_layout(hovermode="closest", barcornerradius=4)
    return fig


def risk_return_scatter(points, title="Risk vs Return"):
    """Her ticker bir nokta; kimligi renk degil, yanindaki etiket tasir.

    points: kolonlari [ticker, vol, ret] olan DataFrame
    """
    fig = go.Figure(go.Scatter(
        x=points["vol"], y=points["ret"], mode="markers+text",
        marker=dict(color=SERIES[0], size=11,
                    line=dict(color=SURFACE, width=2)),  # 2px yuzey halkasi
        text=points["ticker"], textposition="top center",
        textfont=dict(color=INK2, size=12),
        hovertemplate="%{text}: vol %{x:.1%}, getiri %{y:.1%}<extra></extra>",
    ))
    fig = _layout(fig, title, pct=True)
    fig.update_layout(hovermode="closest")
    fig.update_xaxes(tickformat=".0%", title=dict(text="Annualized Volatility", font=dict(color=MUTED)))
    fig.update_yaxes(title=dict(text="CAGR", font=dict(color=MUTED)))
    return fig
