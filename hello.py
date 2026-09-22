import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo


st.title("나만의 인사 앱")

name = st.text_input("이름을 입력하세요")

if name:
    st.write(f"안녕하세요, {name}님! 오늘도 좋은 하루 보내세요!")
else:
    st.info("이름을 입력하면 인사말이 표시됩니다.")

if st.button("현재 시간 보기"):
    local_time = datetime.now(ZoneInfo("Asia/Seoul"))
    current_time = local_time.strftime("%Y-%m-%d %H:%M:%S %Z")
    st.write(f"현재 시간: {current_time}")

if st.button("응원 메시지 받기"):
    st.write("오늘도 화이팅이에요! 당신은 할 수 있어요!")
