import pandas as pd
import plotly.express as px
import seaborn as sns
import streamlit as st


st.set_page_config(page_title="✈️ 항공 승객 분석", layout="wide")

flights = sns.load_dataset("flights")
month_order = list(flights["month"].drop_duplicates())
month_numbers = {month: number for number, month in enumerate(month_order, start=1)}
flights["month_number"] = flights["month"].map(month_numbers).astype("int64")

st.title("✈️ 항공 승객 분석")

metric_columns = st.columns(3)
metric_columns[0].metric("총 행 수", f"{len(flights):,}")
metric_columns[1].metric(
    "연도 범위",
    f"{flights['year'].min()}–{flights['year'].max()}",
)
metric_columns[2].metric("최대 승객 수", f"{flights['passengers'].max():,}")

with st.sidebar:
    month_range = st.slider(
        "월 범위",
        min_value=1,
        max_value=12,
        value=(1, 12),
        format="%d월",
    )

selected_flights = flights[
    flights["month_number"].between(month_range[0], month_range[1])
]
yearly_average = (
    selected_flights.groupby("year", as_index=False)["passengers"]
    .mean()
    .rename(columns={"passengers": "평균 승객 수"})
    .sort_values("year")
)
yearly_average["3년 이동평균"] = yearly_average["평균 승객 수"].rolling(
    window=3
).mean()
yearly_lines = yearly_average.melt(
    id_vars="year",
    value_vars=["평균 승객 수", "3년 이동평균"],
    var_name="구분",
    value_name="승객수",
)

st.subheader("연도별 평균 승객 수")
yearly_figure = px.line(
    yearly_lines,
    x="year",
    y="승객수",
    color="구분",
    line_dash="구분",
    line_dash_map={"평균 승객 수": "solid", "3년 이동평균": "dot"},
    labels={"year": "연도", "승객수": "평균 승객 수"},
)
st.plotly_chart(yearly_figure, use_container_width=True)

monthly_average = (
    flights.groupby(["month_number", "month"], as_index=False)["passengers"]
    .mean()
    .rename(columns={"passengers": "평균 승객 수"})
    .sort_values("month_number")
)
st.subheader("월별 평균 승객 수")
monthly_bar_figure = px.bar(
    monthly_average,
    x="month",
    y="평균 승객 수",
    category_orders={"month": month_order},
    labels={"month": "월"},
)
st.plotly_chart(monthly_bar_figure, use_container_width=True)

st.subheader("월별 승객 수 분포")
monthly_box_figure = px.box(
    flights.sort_values("month_number"),
    x="month",
    y="passengers",
    category_orders={"month": month_order},
    labels={"month": "월", "passengers": "승객 수"},
)
st.plotly_chart(monthly_box_figure, use_container_width=True)

flight_pivot = flights.pivot_table(
    index="year",
    columns="month",
    values="passengers",
    aggfunc="mean",
).reindex(columns=month_order)
st.subheader("연도별·월별 승객 수 히트맵")
heatmap_figure = px.imshow(
    flight_pivot,
    x=month_order,
    y=flight_pivot.index,
    color_continuous_scale="Blues",
    labels={"x": "월", "y": "연도", "color": "승객 수"},
    aspect="auto",
)
st.plotly_chart(heatmap_figure, use_container_width=True)
