import plotly.express as px
import seaborn as sns
import streamlit as st


st.set_page_config(page_title="🍽️ 레스토랑 팁 분석", layout="wide")

tips = sns.load_dataset("tips")

st.title("🍽️ 레스토랑 팁 분석")

st.subheader("기술 통계 요약")
metric_columns = st.columns(4)
metric_columns[0].metric("총 데이터 수", f"{len(tips):,}")
metric_columns[1].metric(
    "평균 식사 금액",
    f"${tips['total_bill'].mean():.2f}",
)
metric_columns[2].metric("평균 팁 금액", f"${tips['tip'].mean():.2f}")
average_tip_percentage = (tips["tip"] / tips["total_bill"] * 100).mean()
metric_columns[3].metric("평균 팁 비율", f"{average_tip_percentage:.2f}%")
st.dataframe(tips.describe(), use_container_width=True)

color_options = {
    "성별(sex)": "sex",
    "흡연여부(smoker)": "smoker",
    "요일(day)": "day",
    "시간대(time)": "time",
}
group_options = {
    "요일(day)": "day",
    "성별(sex)": "sex",
    "시간대(time)": "time",
    "흡연여부(smoker)": "smoker",
}
column_labels = {
    "total_bill": "식사 금액 ($)",
    "tip": "팁 금액 ($)",
    "size": "인원 수",
    "sex": "성별",
    "smoker": "흡연 여부",
    "day": "요일",
    "time": "시간대",
}

with st.sidebar:
    scatter_color_label = st.selectbox("산점도 색상 기준", list(color_options))
    bar_group_label = st.selectbox("막대차트 그룹 기준", list(group_options))

st.subheader("식사 금액과 팁")
scatter_figure = px.scatter(
    tips,
    x="total_bill",
    y="tip",
    color=color_options[scatter_color_label],
    hover_data=["total_bill", "tip", "size"],
    trendline="ols",
    labels=column_labels,
)
st.plotly_chart(scatter_figure, use_container_width=True)

group_column = group_options[bar_group_label]
grouped_bills = (
    tips.groupby(group_column, observed=True, as_index=False)["total_bill"]
    .sum()
    .sort_values("total_bill", ascending=False)
)
grouped_bills["합계 표시"] = grouped_bills["total_bill"].map("${:,.2f}".format)

st.subheader("선택 기준별 총 식사 금액 합계")
bar_figure = px.bar(
    grouped_bills,
    x=group_column,
    y="total_bill",
    text="합계 표시",
    title="선택 기준별 총 식사 금액 합계",
    labels=column_labels,
)
bar_figure.update_traces(textposition="outside")
st.plotly_chart(bar_figure, use_container_width=True)
