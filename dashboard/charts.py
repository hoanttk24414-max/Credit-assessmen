"""2D figures built exclusively from exported score columns."""
import plotly.graph_objects as go

from config import BANK_COLORS, DIGITAL_CODES, GROUP_ORDER
from ui_components import number


def style(figure, height=350):
    figure.update_layout(
        height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Segoe UI Variable Text, Segoe UI, system-ui, sans-serif", size=12, color="#243d78"),
        margin=dict(l=8, r=32, t=16, b=16),
        legend=dict(orientation="h", x=0, y=1.18, title=None, font=dict(size=12)),
        hoverlabel=dict(bgcolor="#11253e", font_color="#ffffff", font_size=13),
        bargap=0.32,
    )
    figure.update_xaxes(showline=False, zeroline=False, gridcolor="#e9eef4", fixedrange=True)
    figure.update_yaxes(showline=False, zeroline=False, gridcolor="#e9eef4", fixedrange=True)
    return figure


def ranking_bar(ranking, height=320):
    data = ranking.sort_values("rank", kind="stable")
    fig = go.Figure(go.Bar(
        x=data.total_score, y=data.ticker, orientation="h", width=0.52,
        marker_color=[BANK_COLORS.get(t, "#366b9c") for t in data.ticker],
        text=[number(v) for v in data.total_score],
        textposition="outside", cliponaxis=False,
        customdata=data[["bank", "rank"]],
        hovertemplate="%{customdata[0]} (%{y})<br>Hạng: %{customdata[1]}<br>Tổng điểm: %{x:.4f} / 100<extra></extra>",
    ))
    style(fig, height)
    fig.update_xaxes(range=[0, 106], tickvals=[0, 20, 40, 60, 80, 100], title=None)
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return fig


def group_comparison(groups, tickers):
    codes = [g for g in GROUP_ORDER if g in set(groups.group)]
    codes += [g for g in groups.group.unique() if g not in codes]
    labels = groups.drop_duplicates("group").set_index("group").group_label.to_dict()
    # Short chart labels only; full labels remain in the hover and data tables.
    short = {"credit": "Chất lượng<br>tín dụng", "capital": "Vốn &<br>nguồn vốn",
             "profitability": "Sinh lời &<br>hiệu quả", "digital": "Chuyển đổi số"}
    fig = go.Figure()
    for ticker in tickers:
        part = groups.loc[groups.ticker.eq(ticker)].set_index("group").reindex(codes)
        fig.add_bar(name=ticker, x=[short.get(g, labels[g]) for g in codes], y=part.group_score_100,
                    marker_color=BANK_COLORS.get(ticker, "#366b9c"),
                    customdata=[[labels[g], row.group_score, row.group_max] for g, row in part.iterrows()],
                    hovertemplate=ticker + " · %{customdata[0]}<br>Điểm nhóm: %{y:.4f} / 100<br>Đóng góp: %{customdata[1]:.4f} / %{customdata[2]:.4f}<extra></extra>")
    style(fig, 254)
    fig.update_layout(barmode="group", margin=dict(l=8, r=16, t=52, b=24))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(range=[0, 105], tickvals=[0, 25, 50, 75, 100], title=None)
    return fig


def criterion_comparison(criteria, code):
    data = criteria.loc[criteria.criterion.eq(code)]
    fig = go.Figure(go.Bar(
        x=data.ticker, y=data.normalized_0_1,
        marker_color=[BANK_COLORS.get(t, "#366b9c") for t in data.ticker], width=0.48,
        customdata=data[["raw_value", "weighted_score"]],
        hovertemplate="%{x}<br>Chuẩn hóa: %{y:.6f} / 1<br>Giá trị: %{customdata[0]:.6f}<br>Đóng góp: %{customdata[1]:.6f}<extra></extra>",
    ))
    style(fig, 290)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(range=[0, 1.08], tickvals=[0, .25, .5, .75, 1])
    return fig


def group_mini(groups, tickers):
    part = groups.set_index("ticker").reindex(tickers)
    fig = go.Figure(go.Bar(
        x=part.index, y=part.group_score_100,
        marker_color=[BANK_COLORS.get(t, "#345da3") for t in part.index],
        text=[number(v) for v in part.group_score_100],
        textposition="outside", cliponaxis=False, width=.7,
        customdata=part[["group_score", "group_max"]],
        hovertemplate="%{x}<br>Điểm nhóm: %{y:.4f} / 100<br>Đóng góp: %{customdata[0]:.4f} / %{customdata[1]:.4f}<extra></extra>",
    ))
    style(fig, 120)
    fig.update_layout(margin=dict(l=2, r=2, t=18, b=2), bargap=.18, font_size=10)
    fig.update_xaxes(showgrid=False, tickfont_size=10)
    fig.update_yaxes(range=[0, 125], showticklabels=False, showgrid=False)
    return fig


def digital_comparison(dataset, selected):
    colors = ("#1fa8ac", "#7261d2", "#4089e9")
    fig = go.Figure()
    for code, color in zip(DIGITAL_CODES, colors):
        fig.add_bar(name=code, x=dataset.bank_code, y=dataset[code + "_score_0_3"],
                    marker_color=color, marker_opacity=[1 if bank == selected else .48 for bank in dataset.bank_code],
                    hovertemplate=code + " · %{x}<br>Điểm: %{y} / 3<extra></extra>")
    style(fig, 224)
    fig.update_layout(barmode="group", margin=dict(l=4, r=6, t=34, b=4), legend_y=1.18)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(range=[0, 3.5], tickvals=[0, 1, 2, 3])
    return fig
