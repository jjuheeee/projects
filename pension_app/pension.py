from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(page_title="📋 국민연금 사업장 분석 대시보드", layout="wide")
st.title("📋 국민연금 사업장 분석 대시보드")

PENSION_RATE = 0.095
SALARY_CAP = 6_590_000
DATA_PATH = Path(__file__).parent / "data" / "cleaned_pension.csv"


@st.cache_data
def load_data() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH, encoding="utf-8-sig")


def find_column(data: pd.DataFrame, candidates: tuple[str, ...]) -> str:
    for candidate in candidates:
        if candidate in data.columns:
            return candidate
    expected = ", ".join(candidates)
    raise ValueError(f"필수 컬럼을 찾을 수 없습니다. 다음 중 하나가 필요합니다: {expected}")


try:
    pension = load_data()
    subscriber_column = find_column(
        pension, ("member_count", "subscriber_count", "가입자수", "사업장가입자수")
    )
    contribution_column = find_column(
        pension, ("charge_amount", "monthly_contribution", "당월고지금액", "월보험료")
    )
    sido_column = find_column(pension, ("sido",))
    company_type_column = find_column(pension, ("company_type", "사업장형태"))
    industry_column = find_column(pension, ("industry", "업종"))
    company_name_column = find_column(pension, ("company_name", "사업장명"))
    estimated_salary_column = find_column(pension, ("estimated_salary_per",))
except (OSError, ValueError, pd.errors.ParserError) as error:
    st.error(f"국민연금 데이터를 불러오지 못했습니다: {error}")
    st.stop()

if pension.empty:
    st.error("국민연금 데이터가 비어 있습니다.")
    st.stop()

latest_data = pension.copy()

latest_data[subscriber_column] = pd.to_numeric(
    latest_data[subscriber_column], errors="coerce"
).fillna(0)
latest_data[contribution_column] = pd.to_numeric(
    latest_data[contribution_column], errors="coerce"
).fillna(0)
latest_data[estimated_salary_column] = pd.to_numeric(
    latest_data[estimated_salary_column], errors="coerce"
)
latest_data["estimated_monthly_salary"] = (
    latest_data[contribution_column]
    .div(latest_data[subscriber_column].where(latest_data[subscriber_column] > 0))
    .div(PENSION_RATE)
    .clip(upper=SALARY_CAP)
)

subscriber_total = latest_data[subscriber_column].sum()
if subscriber_total > 0:
    average_salary = (
        latest_data["estimated_monthly_salary"].fillna(0)
        .mul(latest_data[subscriber_column])
        .sum()
        / subscriber_total
    )
else:
    average_salary = 0

metrics = st.columns(3)
metrics[0].metric("총 등록 사업장 수", f"{len(latest_data):,}")
metrics[1].metric("총 가입자 수", f"{subscriber_total:,.0f}")
metrics[2].metric("전국 평균 1인당 추정 월급여", f"{average_salary:,.0f}원")

with st.sidebar:
    st.subheader("지역 선택")
    sido_options = sorted(latest_data[sido_column].dropna().unique().tolist())
    selected_sido = st.selectbox("시도", sido_options)

    st.subheader("분석 필터")
    business_type = st.selectbox("사업장 형태", ["전체", "법인", "개인"])
    minimum_subscribers = st.slider(
        "최소 가입자 수",
        min_value=1,
        max_value=100,
        value=1,
    )

filtered_data = latest_data.loc[
    latest_data[sido_column].eq(selected_sido)
    & latest_data[subscriber_column].ge(minimum_subscribers)
]
if business_type != "전체":
    filtered_data = filtered_data.loc[
        filtered_data[company_type_column].eq(business_type)
    ]

st.subheader(f"{selected_sido} 지역별 고용 현황")
filtered_member_total = filtered_data[subscriber_column].sum()
filtered_average_salary = (
    filtered_data["estimated_monthly_salary"]
    .fillna(0)
    .mul(filtered_data[subscriber_column])
    .sum()
    / filtered_member_total
    if filtered_member_total > 0
    else 0
)
salary_difference = filtered_average_salary - average_salary
filtered_metrics = st.columns(4)
filtered_metrics[0].metric("해당 시도 사업장 수", f"{len(filtered_data):,}")
filtered_metrics[1].metric("해당 시도 총 가입자 수", f"{filtered_member_total:,.0f}")
filtered_metrics[2].metric(
    "해당 시도 평균 1인당 추정 월급여",
    f"{filtered_average_salary:,.0f}원",
    delta=f"{salary_difference:+,.0f}원",
    delta_color="normal",
)
filtered_metrics[3].metric(
    "전국 평균 1인당 추정 월급여",
    f"{average_salary:,.0f}원",
)

if filtered_data.empty:
    st.info("선택한 조건에 해당하는 사업장이 없습니다.")
else:
    industry_summary = (
        filtered_data.groupby(industry_column, as_index=False)
        .agg(
            사업장수=(company_name_column, "size"),
            가입자수=(subscriber_column, "sum"),
            평균추정월급여=(estimated_salary_column, "mean"),
        )
    )
    company_chart, member_chart = st.columns(2)
    with company_chart:
        company_figure = px.bar(
            industry_summary.nlargest(10, "사업장수").sort_values("사업장수"),
            x="사업장수",
            y=industry_column,
            orientation="h",
            labels={industry_column: "업종", "사업장수": "사업장 수"},
            title="선택 시도 업종별 사업장 수 TOP 10",
        )
        st.plotly_chart(company_figure, use_container_width=True)
    with member_chart:
        st.subheader("가입자 수 상위 업종")
        member_figure = px.bar(
            industry_summary.nlargest(10, "가입자수").sort_values("가입자수"),
            x="가입자수",
            y=industry_column,
            orientation="h",
            labels={industry_column: "업종", "가입자수": "가입자 수"},
        )
        st.plotly_chart(member_figure, use_container_width=True)

    salary_top_industries = (
        industry_summary.nlargest(10, "평균추정월급여")
        .sort_values("평균추정월급여")
        .copy()
    )
    salary_top_industries["급여 표시"] = salary_top_industries[
        "평균추정월급여"
    ].map(lambda salary: f"{salary:,.0f}원")
    salary_figure = px.bar(
        salary_top_industries,
        x="평균추정월급여",
        y=industry_column,
        orientation="h",
        text="급여 표시",
        labels={
            industry_column: "업종",
            "평균추정월급여": "평균 1인당 추정 월급여",
        },
        title="선택 시도 업종별 평균 추정 월급여 TOP 10",
    )
    salary_figure.update_traces(textposition="outside", cliponaxis=False)
    salary_figure.add_hline(y=6590000, line_dash="dash", line_color="red")
    st.plotly_chart(salary_figure, use_container_width=True)

    st.subheader("사업장 목록")
    display_columns = [
        company_name_column,
        industry_column,
        company_type_column,
        subscriber_column,
        "estimated_monthly_salary",
    ]
    display_data = filtered_data.nlargest(100, subscriber_column)[display_columns]
    st.dataframe(
        display_data.rename(
            columns={
                company_name_column: "사업장명",
                industry_column: "업종",
                company_type_column: "사업장 형태",
                subscriber_column: "가입자 수",
                "estimated_monthly_salary": "1인당 추정 월급여",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
