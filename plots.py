"""Plotly grafikleri — Claude Design "Quant Tearsheet Redesign" kanvasina gore.

Renkler token sayfasindan (artboard 1i) geliyor; sira onemli, rastgele renk secmiyoruz.
Grafikler artik kendi rengiyle yuzen bloklar degil, kart yuzeyinin icinde yasiyor:
figur arka plani kart rengiyle ayni ve figurun icinde baslik yok — basligi kart tasiyor.

Kurallar:
- Asla ikinci y ekseni yok.
- Renk tek basina anlam tasimaz: benchmark noktali, faktor cizgileri desenli,
  referans cizgileri etiketli.
- Arayuzun tamami Ingilizce; sayilar ondalik nokta ile okunur.
"""

import plotly.graph_objects as go

# koyu tema yuzeyleri ve murekkep tonlari (ui.py ile ayni token'lar)
SURFACE = "#242932"   # kart yuzeyi — figur arka plani
GRID = "#333945"
AXIS = "#454c5a"
INK = "#f2f4f8"
INK2 = "#c8ccd6"
MUTED = "#8b93a3"

# kategorik seri renkleri (sabit sira: 1. seri hep mavi, 2. hep somon...)
SERIES = ["#8fb3e8", "#eab088", "#7fd0ab", "#e3c37e", "#e6a3bf"]
# renk korlugunde de ayrisabilmesi icin renkle birlikte gelen desen sirasi
DASHES = ["solid", "dash", "dot", "dashdot", "longdash"]

# ayrisan (diverging) uclar: negatif kirmizi, pozitif mavi, orta notr gri
NEG = "#eda1a1"
POS = "#8fb3e8"
MID = "#454c5a"
REF = "#e3c37e"  # referans cizgisi (amber, her zaman etiketli)

FONT = "'IBM Plex Sans', system-ui, sans-serif"
MONO = "'IBM Plex Mono', monospace"

HEIGHT = 300


def _layout(fig, pct=False, height=HEIGHT, show_legend=False):
    fig.update_layout(
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font=dict(color=INK2, family=FONT, size=11),
        margin=dict(l=48, r=14, t=10, b=28),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#1b1f26", bordercolor=AXIS,
                        font=dict(family=MONO, color=INK)),
        showlegend=show_legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1),
        height=height,
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False,
                     tickfont=dict(color=MUTED, family=MONO, size=10))
    fig.update_yaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False,
                     tickfont=dict(color=MUTED, family=MONO, size=10),
                     tickformat=".0%" if pct else None)
    return fig


def _refline(fig, y, label):
    """Esik cizgisi: amber, kesikli ve daima etiketli — renk tek basina yetmez."""
    fig.add_hline(y=y, line_dash="dash", line_color=REF, line_width=1,
                  annotation_text=label, annotation_position="top left",
                  annotation_font=dict(color=REF, family=MONO, size=10))
    return fig


def line_chart(series_map, pct=False, dashed=(), patterned=False, refline=None,
               refline_label=None, hover_fmt=".3f", height=HEIGHT, colors=None):
    """Bir veya birkac cizgi.

    series_map: {isim: Series}
    dashed:     noktali cizilecek seriler (benchmark her zaman burada)
    patterned:  True ise her seri renkle birlikte kendi desenini de alir
    """
    fig = go.Figure()
    palette = colors or SERIES
    for i, (name, s) in enumerate(series_map.items()):
        if name in dashed:
            dash = "dot"
        elif patterned:
            dash = DASHES[i % len(DASHES)]
        else:
            dash = "solid"
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, name=name, mode="lines",
            line=dict(color=palette[i % len(palette)], width=1.8, dash=dash),
            hovertemplate="%{y:" + (".2%" if pct else hover_fmt) + "}<extra>" + name + "</extra>",
        ))
    fig = _layout(fig, pct=pct, height=height, show_legend=False)
    if refline is not None:
        _refline(fig, refline, refline_label or f"{refline:g}")
    return fig


def underwater_chart(dd, height=HEIGHT):
    """Zirveden dusus grafigi: tek seri, negatif bolge kirmizi dolgulu."""
    fig = go.Figure(go.Scatter(
        x=dd.index, y=dd.values, mode="lines",
        line=dict(color=NEG, width=1.6),
        fill="tozeroy", fillcolor="rgba(237,161,161,0.24)",
        hovertemplate="%{y:.2%}<extra></extra>",
    ))
    return _layout(fig, pct=True, height=height)


def monthly_heatmap(table, height=HEIGHT):
    """Yil x ay isi haritasi. Ayrisan skala: kayip kirmizi, kazanc mavi, sifir notr.

    Sayi her hucrede yazili — renk tek basina anlam tasimaz.
    """
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig = go.Figure(go.Heatmap(
        z=table.values,
        x=[months[m - 1] for m in table.columns],
        y=[str(y) for y in table.index],
        colorscale=[[0, NEG], [0.5, MID], [1, POS]],
        zmid=0, xgap=2, ygap=2,  # hucreler arasi 2px yuzey boslugu
        texttemplate="%{z:.1%}", textfont=dict(family=MONO, size=9, color=INK),
        colorbar=dict(tickformat=".0%", outlinewidth=0, thickness=10,
                      tickfont=dict(family=MONO, size=9, color=MUTED)),
        hovertemplate="%{y} %{x}: %{z:.2%}<extra></extra>",
    ))
    fig = _layout(fig, height=height)
    fig.update_layout(hovermode="closest", margin=dict(l=40, r=14, t=10, b=24))
    fig.update_xaxes(gridcolor=SURFACE, side="top")
    fig.update_yaxes(gridcolor=SURFACE, autorange="reversed")
    return fig


def loadings_bar(loadings, height=HEIGHT):
    """Faktor yuklemeleri: sifir cizgisinin sagi pozitif, solu negatif maruziyet.

    Yatay bar — faktor adlari okunabilir kalsin diye; her faktor kendi sabit rengini alir.
    """
    names = list(loadings.index)
    values = list(loadings.values)
    fig = go.Figure(go.Bar(
        x=values, y=names, orientation="h",
        marker=dict(color=[SERIES[i % len(SERIES)] for i in range(len(values))]),
        text=[f"{v:+.2f}" for v in values],
        textposition="outside", textfont=dict(color=INK2, family=MONO, size=11),
        hovertemplate="%{y}: %{x:.4f}<extra></extra>",
    ))
    fig.add_vline(x=0, line_color=AXIS, line_width=1)
    fig = _layout(fig, height=height)
    fig.update_layout(hovermode="closest", barcornerradius=3,
                      margin=dict(l=8, r=40, t=10, b=24))
    fig.update_yaxes(autorange="reversed", tickfont=dict(color=INK2, family=MONO, size=11))
    return fig


def risk_return_scatter(points, height=HEIGHT, highlight=()):
    colors = [SERIES[0] if t not in highlight else SERIES[list(highlight).index(t) % 2]
              for t in points["ticker"]]
    sizes = [13 if t in highlight else 10 for t in points["ticker"]]
    fig = go.Figure(go.Scatter(
        x=points["vol"], y=points["ret"], mode="markers+text",
        marker=dict(color=colors, size=sizes,
                    line=dict(color=SURFACE, width=2)),  # 2px yuzey halkasi
        text=points["ticker"], textposition="top center",
        textfont=dict(color=INK2, family=MONO, size=11),
        hovertemplate="%{text}: volatility %{x:.1%}, CAGR %{y:.1%}<extra></extra>",
    ))
    fig = _layout(fig, pct=True, height=height)
    fig.update_layout(hovermode="closest")
    fig.update_xaxes(tickformat=".0%",
                     title=dict(text="Annualized volatility →",
                                font=dict(color=MUTED, family=MONO, size=10)))
    fig.update_yaxes(title=dict(text="↑ CAGR",
                                font=dict(color=MUTED, family=MONO, size=10)))
    return fig
