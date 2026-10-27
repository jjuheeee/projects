import calendar
import csv
import json
import os
from collections import Counter
import uuid
from datetime import date

import pandas as pd
import streamlit as st


DIARY_FILE = "diary.csv"
MEALS_FILE = "meals.csv"
MOODS_FILE = "moods.json"
SETTINGS_FILE = "settings.json"
FOOD_CATALOG_FILE = "food_catalog.csv"
FOOD_PREFERENCES_FILE = "food_preferences.json"
DIARY_COLUMNS = ["ID", "날짜", "작성자", "제목", "내용", "날씨", "기분"]
MEAL_COLUMNS = [
    "ID",
    "날짜",
    "식사",
    "음식",
    "섭취량",
    "단위",
    "기준 칼로리",
    "칼로리(kcal)",
]
LEGACY_DIARY_COLUMNS = [
    ["날짜", "제목", "내용", "날씨"],
    ["날짜", "작성자", "제목", "내용", "날씨"],
]
MOOD_OPTIONS = [
    "😆 매우 행복",
    "😊 행복",
    "😐 보통",
    "😢 슬픔",
    "😡 화남",
    "😴 피곤",
    "😰 불안",
]
MEAL_TYPES = ["아침", "점심", "저녁", "간식"]
UNITS = [
    "g",
    "개",
    "인분",
    "그릇",
    "잔",
    "봉지",
    "줄",
    "조각",
    "장",
    "컵",
    "캔",
    "팩",
    "병",
]
FOOD_CATALOG_COLUMNS = [
    "카테고리",
    "음식",
    "기준량",
    "단위",
    "기준칼로리(kcal)",
    "출처",
]
THEME_COLORS = {
    "파랑": "#1976d2",
    "초록": "#388e3c",
    "보라": "#7b1fa2",
    "주황": "#f57c00",
    "빨강": "#d32f2f",
}


def load_diary():
    if not os.path.exists(DIARY_FILE):
        return pd.DataFrame(columns=DIARY_COLUMNS)

    with open(DIARY_FILE, encoding="utf-8-sig", newline="") as diary_file:
        rows = list(csv.reader(diary_file))

    if not rows:
        return pd.DataFrame(columns=DIARY_COLUMNS)

    source_columns = rows[0]
    if source_columns != DIARY_COLUMNS and source_columns not in LEGACY_DIARY_COLUMNS:
        raise ValueError(f"지원하지 않는 일기 CSV 열 형식입니다: {source_columns}")

    entries = []
    for line_number, row in enumerate(rows[1:], start=2):
        if not row:
            continue

        if len(row) > len(source_columns):
            extra_fields = len(row) - len(source_columns)
            content_index = source_columns.index("내용")
            row = (
                row[:content_index]
                + [",".join(row[content_index : content_index + extra_fields + 1])]
                + row[content_index + extra_fields + 1 :]
            )
        if len(row) != len(source_columns):
            raise ValueError(
                f"일기 CSV {line_number}행의 열 개수가 올바르지 않습니다: "
                f"기대 {len(source_columns)}개, 실제 {len(row)}개"
            )

        entry = dict(zip(source_columns, row))
        entry["ID"] = entry.get("ID") or str(
            uuid.uuid5(uuid.NAMESPACE_URL, f"{line_number}:{row!r}")
        )
        entry.setdefault("작성자", "")
        entry.setdefault("기분", "")
        try:
            entry["날짜"] = date.fromisoformat(entry["날짜"]).isoformat()
        except ValueError as error:
            raise ValueError(
                f"일기 CSV {line_number}행의 날짜가 YYYY-MM-DD 형식이 아닙니다."
            ) from error
        entries.append(entry)

    return pd.DataFrame(entries, columns=DIARY_COLUMNS)


def save_diary(diary):
    diary.reindex(columns=DIARY_COLUMNS).to_csv(
        DIARY_FILE,
        index=False,
        encoding="utf-8-sig",
    )


def load_meals():
    if not os.path.exists(MEALS_FILE):
        return []
    with open(MEALS_FILE, encoding="utf-8-sig", newline="") as meals_file:
        rows = list(csv.DictReader(meals_file))
    for row in rows:
        try:
            row["날짜"] = date.fromisoformat(row["날짜"]).isoformat()
            row["섭취량"] = float(row["섭취량"])
            row["기준 칼로리"] = float(row["기준 칼로리"])
            row["칼로리(kcal)"] = float(row["칼로리(kcal)"])
        except (KeyError, ValueError) as error:
            raise ValueError("식단 CSV의 데이터 형식이 올바르지 않습니다.") from error
    return rows


def save_meals(meals):
    with open(MEALS_FILE, "w", encoding="utf-8-sig", newline="") as meals_file:
        writer = csv.DictWriter(meals_file, fieldnames=MEAL_COLUMNS)
        writer.writeheader()
        writer.writerows(meals)


def load_food_catalog():
    with open(FOOD_CATALOG_FILE, encoding="utf-8-sig", newline="") as catalog_file:
        rows = list(csv.DictReader(catalog_file))

    if not set(FOOD_CATALOG_COLUMNS).issubset(rows[0] if rows else {}):
        raise ValueError(f"{FOOD_CATALOG_FILE}의 열 형식이 올바르지 않습니다.")

    foods = {}
    for row in rows:
        try:
            row["기준량"] = float(row["기준량"])
            row["기준칼로리(kcal)"] = (
                float(row["기준칼로리(kcal)"])
                if row["기준칼로리(kcal)"].strip()
                else None
            )
        except ValueError as error:
            raise ValueError(
                f"음식 카탈로그의 '{row['음식']}' 기준량 또는 칼로리가 올바르지 않습니다."
            ) from error
        foods[row["음식"]] = row
    return list(foods.values())


def save_food_catalog(foods):
    with open(FOOD_CATALOG_FILE, "w", encoding="utf-8-sig", newline="") as catalog_file:
        writer = csv.DictWriter(catalog_file, fieldnames=FOOD_CATALOG_COLUMNS)
        writer.writeheader()
        for food in foods:
            writer.writerow(
                {
                    **food,
                    "기준칼로리(kcal)": (
                        food["기준칼로리(kcal)"]
                        if food["기준칼로리(kcal)"] is not None
                        else ""
                    ),
                }
            )


def load_food_preferences():
    if not os.path.exists(FOOD_PREFERENCES_FILE):
        return {"favorites": []}
    with open(FOOD_PREFERENCES_FILE, encoding="utf-8") as preferences_file:
        preferences = json.load(preferences_file)
    if not isinstance(preferences, dict) or not isinstance(
        preferences.get("favorites", []), list
    ):
        raise ValueError("food_preferences.json의 형식이 올바르지 않습니다.")
    return {"favorites": list(dict.fromkeys(preferences.get("favorites", [])))}


def save_food_preferences(preferences):
    with open(FOOD_PREFERENCES_FILE, "w", encoding="utf-8") as preferences_file:
        json.dump(preferences, preferences_file, ensure_ascii=False, indent=2)


def food_from_history(food_name, meals):
    for meal in reversed(meals):
        if meal["음식"] == food_name:
            amount = meal["섭취량"]
            calories = meal["기준 칼로리"]
            return {
                "카테고리": "최근 기록",
                "음식": food_name,
                "기준량": amount,
                "단위": meal["단위"],
                "기준칼로리(kcal)": calories,
                "출처": "이전 식단 기록의 사용자 입력값",
            }
    return None


def choose_food(food, meals, food_catalog):
    if isinstance(food, str):
        selected_food = next(
            (item for item in food_catalog if item["음식"] == food),
            None,
        )
        selected_food = selected_food or food_from_history(food, meals) or {
            "카테고리": "직접 입력",
            "음식": food,
            "기준량": 100.0,
            "단위": "g",
            "기준칼로리(kcal)": None,
            "출처": "직접 입력 필요",
        }
    else:
        selected_food = food
        if selected_food["기준칼로리(kcal)"] is None:
            previous_meal = food_from_history(selected_food["음식"], meals)
            if previous_meal:
                selected_food = {
                    **selected_food,
                    "기준량": previous_meal["기준량"],
                    "단위": previous_meal["단위"],
                    "기준칼로리(kcal)": previous_meal["기준칼로리(kcal)"],
                    "출처": previous_meal["출처"],
                }

    st.session_state["selected_food_name"] = selected_food["음식"]
    st.session_state["new_food_name"] = selected_food["음식"]
    st.session_state["new_food_amount"] = selected_food["기준량"]
    st.session_state["new_food_unit"] = selected_food["단위"]
    st.session_state["new_food_calories"] = (
        selected_food["기준칼로리(kcal)"] or 0.0
    )
    st.session_state["selected_food_source"] = selected_food["출처"]


def load_moods():
    if not os.path.exists(MOODS_FILE):
        return {}
    with open(MOODS_FILE, encoding="utf-8") as moods_file:
        moods = json.load(moods_file)
    if not isinstance(moods, dict):
        raise ValueError("moods.json은 날짜별 기분을 담은 JSON 객체여야 합니다.")
    normalized_moods = {}
    for day, mood in moods.items():
        normalized_day = date.fromisoformat(day).isoformat()
        if mood not in MOOD_OPTIONS:
            raise ValueError(f"moods.json에 지원하지 않는 기분 값이 있습니다: {mood}")
        normalized_moods[normalized_day] = mood
    return normalized_moods


def save_moods(moods):
    with open(MOODS_FILE, "w", encoding="utf-8") as moods_file:
        json.dump(moods, moods_file, ensure_ascii=False, indent=2)


def load_settings():
    default_settings = {
        "author_name": "",
        "theme": "파랑",
        "last_viewed_date": None,
    }
    if not os.path.exists(SETTINGS_FILE):
        return default_settings

    with open(SETTINGS_FILE, encoding="utf-8") as settings_file:
        settings = json.load(settings_file)
    if not isinstance(settings, dict):
        raise ValueError("settings.json은 JSON 객체여야 합니다.")
    return {**default_settings, **settings}


def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as settings_file:
        json.dump(settings, settings_file, ensure_ascii=False, indent=2)


def diary_mood_for_day(diary, moods, day):
    day_entries = diary[diary["날짜"] == day]
    if not day_entries.empty:
        saved_mood = day_entries.iloc[-1]["기분"]
        if saved_mood in MOOD_OPTIONS:
            return saved_mood
    return moods.get(day, "")


def set_flash(message):
    st.session_state["flash_message"] = message


def render_diary_delete_confirmation(diary, diary_id, surface):
    pending_delete = st.session_state.get("pending_diary_delete")
    if not pending_delete:
        return
    if pending_delete != {"id": diary_id, "surface": surface}:
        return

    st.warning("정말 이 일기를 삭제하시겠습니까?")
    confirm, cancel = st.columns(2)
    if confirm.button(
        "삭제 확인",
        key=f"confirm_diary_delete_{surface}_{diary_id}",
    ):
        save_diary(diary[diary["ID"] != diary_id].reset_index(drop=True))
        st.session_state.pop("pending_diary_delete", None)
        set_flash("선택한 일기가 삭제되었습니다.")
        st.rerun()
    if cancel.button(
        "취소",
        key=f"cancel_diary_delete_{surface}_{diary_id}",
    ):
        st.session_state.pop("pending_diary_delete", None)
        st.rerun()


def render_calendar(diary, moods):
    today = date.today()
    if "calendar_month" not in st.session_state:
        st.session_state["calendar_month"] = today.replace(day=1)
    if "selected_date" not in st.session_state:
        st.session_state["selected_date"] = today.isoformat()

    with st.sidebar:
        st.subheader("월별 달력")
        st.markdown(
            f"""
            <style>
            div[class*="st-key-calendar_cell_"] {{
                box-sizing: border-box;
                height: 3.5rem;
                min-height: 3.5rem;
                padding: 0.1rem;
                border-radius: 0.4rem;
                text-align: center;
            }}
            div[class*="st-key-calendar_cell_"] button {{
                height: 1.8rem;
                min-height: 1.8rem;
                padding: 0 0.1rem;
            }}
            div[class*="st-key-calendar_cell_"] [data-testid="stCaptionContainer"] {{
                margin-top: -0.15rem;
                font-size: 0.65rem;
                line-height: 1;
                white-space: nowrap;
            }}
            div[class~="st-key-calendar_cell_{today.isoformat()}"] {{
                background-color: #e3f2fd;
                outline: 1px solid #1976d2;
            }}
            """
            + "".join(
                f"""
                div[class~="st-key-calendar_cell_{day}"] {{
                    background-color: #f1f8e9;
                }}
                """
                for day in diary["날짜"].unique()
                if day != today.isoformat()
            ),
            unsafe_allow_html=True,
        )
        previous, month_label, following = st.columns([1, 3, 1])
        current_month = st.session_state["calendar_month"]
        if previous.button("◀", key="calendar_previous_month"):
            year, month = current_month.year, current_month.month - 1
            if month == 0:
                year, month = year - 1, 12
            st.session_state["calendar_month"] = date(year, month, 1)
            st.rerun()
        month_label.markdown(f"**{current_month.year}년 {current_month.month}월**")
        if following.button("▶", key="calendar_next_month"):
            year, month = current_month.year, current_month.month + 1
            if month == 13:
                year, month = year + 1, 1
            st.session_state["calendar_month"] = date(year, month, 1)
            st.rerun()

        weekdays = ["월", "화", "수", "목", "금", "토", "일"]
        for column, weekday in zip(st.columns(7), weekdays):
            column.caption(weekday)

        entry_counts = diary["날짜"].value_counts().to_dict()
        for week in calendar.monthcalendar(current_month.year, current_month.month):
            columns = st.columns(7)
            for column, day_number in zip(columns, week):
                if day_number == 0:
                    column.write("")
                    continue

                day = date(
                    current_month.year, current_month.month, day_number
                ).isoformat()
                mood = diary_mood_for_day(diary, moods, day)
                mood_emoji = mood.split(" ", 1)[0] if mood else ""
                count = entry_counts.get(day, 0)
                label_parts = [mood_emoji, str(day_number)]
                if day == today.isoformat():
                    label_parts.insert(0, "🔵")
                with column.container(key=f"calendar_cell_{day}"):
                    if st.button(
                        " ".join(part for part in label_parts if part),
                        key=f"calendar_day_{day}",
                        type="primary" if day == st.session_state["selected_date"] else "secondary",
                        width="stretch",
                    ):
                        st.session_state["selected_date"] = day
                    if count:
                        st.caption(f"📖 {count}개")


settings = load_settings()
last_viewed_date = settings["last_viewed_date"]
settings["last_viewed_date"] = date.today().isoformat()
save_settings(settings)
diary = load_diary()
meals = load_meals()
moods = load_moods()
food_catalog = load_food_catalog()
food_preferences = load_food_preferences()

with st.sidebar:
    st.subheader("설정")
    author_name = st.text_input(
        "작성자 이름",
        value=settings["author_name"],
        key="author_name_input",
    )
    if st.button("이름 저장", key="save_author_name"):
        settings["author_name"] = author_name
        save_settings(settings)
        set_flash("작성자 이름이 저장되었습니다.")

    theme_options = list(THEME_COLORS)
    if settings["theme"] not in theme_options:
        settings["theme"] = theme_options[0]
    theme = st.selectbox(
        "테마 색상",
        theme_options,
        index=theme_options.index(settings["theme"]),
        key="theme_select",
    )
    if theme != settings["theme"]:
        settings["theme"] = theme
        save_settings(settings)

    today = date.today().isoformat()
    saved_today_mood = moods.get(today)
    today_mood = st.selectbox(
        "오늘의 기분",
        MOOD_OPTIONS,
        index=MOOD_OPTIONS.index(saved_today_mood) if saved_today_mood else None,
        placeholder="기분을 선택해주세요",
        key="today_mood_select",
    )
    if today_mood and moods.get(today) != today_mood:
        moods[today] = today_mood
        save_moods(moods)

render_calendar(diary, moods)
selected_date = st.session_state["selected_date"]
selected_day = date.fromisoformat(selected_date)

if st.session_state.get("flash_message"):
    st.success(st.session_state.pop("flash_message"))

st.markdown(
    f"""
    <div style="background-color: {THEME_COLORS[theme]}; color: white;
                padding: 1rem; border-radius: 0.5rem; text-align: center;">
        오늘의 테마: {theme}
    </div>
    """,
    unsafe_allow_html=True,
)

st.title("📔 나의 일기장")
st.caption(f"선택한 날짜: {selected_date}")

with st.container():
    st.subheader("일기 쓰기")
    title = st.text_input("제목", key="diary_title")
    content = st.text_area("내용", height=150, key="diary_content")
    weather = st.selectbox(
        "날씨",
        ["맑음", "흐림", "비", "눈", "바람"],
        key="diary_weather",
    )
    if selected_date == date.today().isoformat() and today_mood:
        diary_mood = today_mood
        st.write(f"오늘의 기분: {diary_mood} (사이드바에서 선택)")
    else:
        saved_day_mood = diary_mood_for_day(diary, moods, selected_date)
        mood_index = MOOD_OPTIONS.index(saved_day_mood) if saved_day_mood else 2
        diary_mood = st.selectbox(
            "기분",
            MOOD_OPTIONS,
            index=mood_index,
            key=f"diary_mood_{selected_date}",
        )
    if st.button("일기 저장", key="save_diary"):
        new_entry = {
            "ID": str(uuid.uuid4()),
            "날짜": selected_date,
            "작성자": settings["author_name"],
            "제목": title,
            "내용": content,
            "날씨": weather,
            "기분": diary_mood,
        }
        diary = pd.concat([diary, pd.DataFrame([new_entry])], ignore_index=True)
        save_diary(diary)
        set_flash("일기가 저장되었습니다.")
        st.rerun()

with st.container():
    meal_section_title = (
        "오늘의 식단"
        if selected_date == date.today().isoformat()
        else f"{selected_date} 식단"
    )
    st.subheader(meal_section_title)
    st.caption(
        "음식 이름 카탈로그에는 150개 이상의 자주 먹는 음식을 담았습니다. "
        "현재 확인된 영양정보 API가 연결되어 있지 않아, 출처가 확인되지 않은 "
        "음식은 포장지나 신뢰할 수 있는 자료의 칼로리를 직접 입력해주세요."
    )
    selected_meals = [meal for meal in meals if meal["날짜"] == selected_date]

    meal_tabs = st.tabs(
        ["음식 검색", "자주 먹는 음식 추천", "최근 먹은 음식", "즐겨찾기"]
    )
    food_by_name = {food["음식"]: food for food in food_catalog}
    meal_frequency = Counter(meal["음식"] for meal in meals)
    if meal_frequency:
        popular_food_names = [name for name, _ in meal_frequency.most_common(10)]
    else:
        popular_food_names = [
            "흰쌀밥",
            "김치찌개",
            "라면",
            "삼겹살",
            "떡볶이",
            "김밥",
            "햄버거",
            "바나나",
            "삶은 계란",
            "아메리카노",
        ]

    with meal_tabs[0]:
        search_query = st.text_input(
            "음식 이름 검색",
            placeholder="예: 김치, 치킨, 바나나",
            key="food_search_query",
        ).strip()
        if search_query:
            matched_foods = [
                food
                for food in food_catalog
                if search_query.casefold() in food["음식"].casefold()
            ][:20]
        else:
            matched_foods = [
                food_by_name[name]
                for name in popular_food_names
                if name in food_by_name
            ]

        search_options = {
            f'{food["음식"]} · {food["카테고리"]}': food
            for food in matched_foods
        }
        if search_query and search_query not in food_by_name:
            custom_label = f"✍️ 직접 입력: {search_query}"
            search_options[custom_label] = None
        if not search_options:
            search_options = {"검색어를 입력하거나 직접 음식 이름을 입력하세요": None}

        selected_search_option = st.selectbox(
            "검색 결과" if search_query else "인기 음식",
            list(search_options),
            index=None,
            placeholder="음식을 선택해주세요",
            key="food_search_result",
        )
        previous_search_option = st.session_state.get("_previous_food_search_result")
        if selected_search_option and selected_search_option != previous_search_option:
            chosen_food = search_options[selected_search_option]
            if chosen_food is None and search_query:
                choose_food(search_query, meals, food_catalog)
            elif chosen_food is not None:
                choose_food(chosen_food, meals, food_catalog)
            st.session_state["_previous_food_search_result"] = selected_search_option

    with meal_tabs[1]:
        st.subheader("🍽️ 오늘 뭐 먹었나요?")
        st.caption("추천은 기록을 돕기 위한 제안이며, 선택만으로 식단에 저장되지는 않습니다.")
        refresh_count = st.session_state.get("food_recommendation_refresh", 0)
        if st.button("🔄 다른 음식 보기", key="refresh_food_recommendations"):
            st.session_state["food_recommendation_refresh"] = refresh_count + 1
            st.rerun()

        recommendations = {
            "아침 추천": ["토스트", "삶은 계란", "시리얼", "바나나", "요거트"],
            "점심 추천": ["김치찌개", "제육덮밥", "돈가스", "비빔밥", "김밥"],
            "저녁 추천": ["삼겹살", "치킨", "파스타", "닭갈비", "샐러드"],
            "간식 추천": ["아이스크림", "과자", "카페라떼", "고구마", "과일"],
        }
        for category_index, (category, names) in enumerate(recommendations.items()):
            rotation = refresh_count % len(names)
            displayed_names = names[rotation:] + names[:rotation]
            with st.expander(category):
                recommendation_columns = st.columns(2)
                for index, name in enumerate(displayed_names):
                    if recommendation_columns[index % 2].button(
                        name,
                        key=f"food_recommendation_{category_index}_{index}",
                    ):
                        choose_food(name, meals, food_catalog)

        if meal_frequency:
            st.caption("자주 기록한 음식")
            for index, (name, count) in enumerate(meal_frequency.most_common(5)):
                if st.button(
                    f"{name} · {count}회",
                    key=f"frequent_food_{index}",
                ):
                    choose_food(name, meals, food_catalog)

    recent_food_names = list(
        dict.fromkeys(meal["음식"] for meal in reversed(meals))
    )[:10]
    with meal_tabs[2]:
        if recent_food_names:
            for index, name in enumerate(recent_food_names):
                recent_record = food_from_history(name, meals)
                if st.button(
                    f'{name} · {recent_record["기준량"]:g} {recent_record["단위"]}',
                    key=f"recent_food_{index}",
                ):
                    choose_food(recent_record, meals, food_catalog)
        else:
            st.info("최근 기록한 음식이 아직 없습니다.")

    with meal_tabs[3]:
        favorite_names = food_preferences["favorites"]
        if favorite_names:
            for index, name in enumerate(favorite_names):
                favorite_columns = st.columns([4, 1])
                if favorite_columns[0].button(name, key=f"favorite_food_{index}"):
                    choose_food(name, meals, food_catalog)
                if favorite_columns[1].button(
                    "해제",
                    key=f"remove_favorite_food_{index}",
                ):
                    food_preferences["favorites"].remove(name)
                    save_food_preferences(food_preferences)
                    st.rerun()
        else:
            st.info("즐겨찾기 음식이 없습니다. 음식을 선택한 뒤 즐겨찾기에 추가해보세요.")

    st.divider()
    st.markdown("#### 선택한 음식 기록")
    st.session_state.setdefault("new_food_name", "")
    st.session_state.setdefault("new_food_amount", 100.0)
    st.session_state.setdefault("new_food_unit", "g")
    st.session_state.setdefault("new_food_calories", 0.0)
    food_name = st.text_input("음식 이름", key="new_food_name")
    selected_food_info = food_by_name.get(food_name.strip()) or food_from_history(
        food_name.strip(), meals
    )
    if selected_food_info:
        food_category = selected_food_info["카테고리"]
        source = selected_food_info["출처"]
        if selected_food_info["기준칼로리(kcal)"] is None:
            st.info(f"{food_category} · 칼로리 출처: {source}")
        else:
            st.caption(f"{food_category} · 칼로리 기준: {source}")
    else:
        food_category = "기타"
        st.info("목록에 없는 음식입니다. 음식 이름과 확인한 칼로리를 직접 입력하면 목록에 저장됩니다.")

    meal_type = st.selectbox("식사 종류", MEAL_TYPES, key="new_meal_type")
    amount_columns = st.columns(2)
    amount = amount_columns[0].number_input(
        "섭취량",
        min_value=0.1,
        step=1.0 if st.session_state["new_food_unit"] == "g" else 0.1,
        key="new_food_amount",
    )
    unit = amount_columns[1].selectbox(
        "단위",
        UNITS,
        key="new_food_unit",
    )
    calorie_label = (
        "100g당 칼로리(kcal)"
        if unit == "g"
        else f"1{unit}당 칼로리(kcal)"
    )
    calories_per_base = st.number_input(
        calorie_label,
        min_value=0.0,
        step=1.0,
        key="new_food_calories",
    )
    if calories_per_base > 0:
        calculated_calories = (
            amount * calories_per_base / 100
            if unit == "g"
            else amount * calories_per_base
        )
        st.metric("예상 칼로리", f"약 {calculated_calories:,.2f} kcal")
    else:
        calculated_calories = 0.0
        st.caption("신뢰할 수 있는 칼로리 정보를 확인해 입력해주세요.")

    if food_name.strip() and food_name.strip() not in food_preferences["favorites"]:
        if st.button("☆ 즐겨찾기에 추가", key="add_food_favorite"):
            food_preferences["favorites"].append(food_name.strip())
            save_food_preferences(food_preferences)
            st.rerun()
    elif food_name.strip():
        if st.button("★ 즐겨찾기 해제", key="remove_selected_food_favorite"):
            food_preferences["favorites"].remove(food_name.strip())
            save_food_preferences(food_preferences)
            st.rerun()

    add_meal = st.button("식단에 추가", key="add_meal")

    if add_meal:
        if not food_name.strip():
            st.error("음식 이름을 입력해주세요.")
        elif calories_per_base <= 0:
            st.error("확인한 음식 칼로리를 0보다 큰 값으로 입력해주세요.")
        else:
            meals.append(
                {
                    "ID": str(uuid.uuid4()),
                    "날짜": selected_date,
                    "식사": meal_type,
                    "음식": food_name.strip(),
                    "섭취량": amount,
                    "단위": unit,
                    "기준 칼로리": calories_per_base,
                    "칼로리(kcal)": round(calculated_calories, 2),
                }
            )
            save_meals(meals)
            if food_name.strip() in food_by_name:
                catalog_item = food_by_name[food_name.strip()]
                catalog_item["기준량"] = 100.0 if unit == "g" else 1.0
                catalog_item["단위"] = unit
                catalog_item["기준칼로리(kcal)"] = calories_per_base
                catalog_item["출처"] = "사용자 입력 (이전 식단 기록)"
            else:
                food_catalog.append(
                    {
                        "카테고리": food_category,
                        "음식": food_name.strip(),
                        "기준량": 100.0 if unit == "g" else 1.0,
                        "단위": unit,
                        "기준칼로리(kcal)": calories_per_base,
                        "출처": "사용자 입력 (이전 식단 기록)",
                    }
                )
            save_food_catalog(food_catalog)
            set_flash("식단이 추가되었습니다.")
            st.rerun()

    selected_meals = [meal for meal in meals if meal["날짜"] == selected_date]
    total_calories = sum(meal["칼로리(kcal)"] for meal in selected_meals)
    st.metric("하루 총섭취 칼로리", f"{total_calories:,.2f} kcal")
    if selected_meals:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "식사": meal["식사"],
                        "음식": meal["음식"],
                        "섭취량": f'{meal["섭취량"]:g} {meal["단위"]}',
                        "기준 칼로리 (100g/단위당)": meal["기준 칼로리"],
                        "칼로리(kcal)": meal["칼로리(kcal)"],
                    }
                    for meal in selected_meals
                ]
            ),
            hide_index=True,
            width="stretch",
        )

        meal_labels = {
            meal["ID"]: (
                f'{meal["식사"]} · {meal["음식"]} '
                f'({meal["섭취량"]:g} {meal["단위"]})'
            )
            for meal in selected_meals
        }
        selected_meal_id = st.selectbox(
            "수정 또는 삭제할 음식",
            list(meal_labels),
            format_func=lambda meal_id: meal_labels[meal_id],
            key="edit_meal_id",
        )
        meal_to_edit = next(
            meal for meal in selected_meals if meal["ID"] == selected_meal_id
        )
        with st.form(f"edit_meal_form_{selected_meal_id}"):
            edit_type = st.selectbox(
                "식사 종류 수정",
                MEAL_TYPES,
                index=MEAL_TYPES.index(meal_to_edit["식사"]),
                key=f"edit_type_{selected_meal_id}",
            )
            edit_food = st.text_input(
                "음식 이름 수정",
                value=meal_to_edit["음식"],
                key=f"edit_food_{selected_meal_id}",
            )
            edit_amount = st.number_input(
                "섭취량 수정",
                min_value=0.1,
                value=meal_to_edit["섭취량"],
                step=0.1,
                key=f"edit_amount_{selected_meal_id}",
            )
            edit_unit = st.selectbox(
                "단위 수정",
                UNITS,
                index=UNITS.index(meal_to_edit["단위"]),
                key=f"edit_unit_{selected_meal_id}",
            )
            edit_calorie_label = (
                "100g당 칼로리 수정"
                if edit_unit == "g"
                else "1개/인분당 칼로리 수정"
            )
            edit_calories = st.number_input(
                edit_calorie_label,
                min_value=0.0,
                value=meal_to_edit["기준 칼로리"],
                step=1.0,
                key=f"edit_calories_{selected_meal_id}",
            )
            update_meal = st.form_submit_button("선택한 음식 수정")
        if update_meal:
            if not edit_food.strip():
                st.error("음식 이름을 입력해주세요.")
            elif edit_calories <= 0:
                st.error("확인한 음식 칼로리를 0보다 큰 값으로 입력해주세요.")
            else:
                updated_meals = []
                for meal in meals:
                    if meal["ID"] == selected_meal_id:
                        meal = {
                            **meal,
                            "식사": edit_type,
                            "음식": edit_food.strip(),
                            "섭취량": edit_amount,
                            "단위": edit_unit,
                            "기준 칼로리": edit_calories,
                            "칼로리(kcal)": round(
                                edit_amount * edit_calories / 100
                                if edit_unit == "g"
                                else edit_amount * edit_calories,
                                2,
                            ),
                        }
                    updated_meals.append(meal)
                save_meals(updated_meals)
                set_flash("식단이 수정되었습니다.")
                st.rerun()

        if st.button("선택한 음식 삭제", key="delete_meal"):
            save_meals(
                [meal for meal in meals if meal["ID"] != selected_meal_id]
            )
            set_flash("식단이 삭제되었습니다.")
            st.rerun()
    else:
        st.info("선택한 날짜에 등록된 식단이 없습니다.")

with st.container():
    st.subheader(f"{selected_date} 기록")
    selected_diary = diary[diary["날짜"] == selected_date]
    selected_mood = diary_mood_for_day(diary, moods, selected_date)
    if selected_mood:
        st.write(f"기분: {selected_mood}")
    if not selected_diary.empty:
        for _, entry in selected_diary.iterrows():
            title_column, delete_column = st.columns([5, 1])
            with title_column:
                with st.expander(f'📖 {entry["제목"] or "제목 없는 일기"}'):
                    st.write(f'날씨: {entry["날씨"]}')
                    st.write(f'기분: {entry["기분"] or "미기록"}')
                    st.write(entry["내용"])
            if delete_column.button(
                "🗑️ 삭제",
                key=f"delete_diary_date_{entry['ID']}",
                help="이 일기 삭제",
            ):
                st.session_state["pending_diary_delete"] = {
                    "id": entry["ID"],
                    "surface": "date",
                }
            render_diary_delete_confirmation(diary, entry["ID"], "date")
    if selected_meals:
        st.write("식단 기록:")
        for meal in selected_meals:
            st.write(
                f'{meal["식사"]}: {meal["음식"]} · '
                f'{meal["섭취량"]:g} {meal["단위"]} · '
                f'{meal["칼로리(kcal)"]:g} kcal'
            )
    if selected_diary.empty and not selected_meals and not selected_mood:
        st.info("선택한 날짜에는 아직 기록이 없습니다.")

if last_viewed_date:
    st.caption(f"마지막으로 일기를 확인한 날: {last_viewed_date}")
else:
    st.caption("처음 방문이에요! 일기를 써봐요 🌱")
