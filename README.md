# 나의 일기장

## 실행

```bash
uv run streamlit run diary.py
```

앱은 일기, 식단, 기분을 각각 `diary.csv`, `meals.csv`, `moods.json`에 저장하고 설정은 `settings.json`에 저장합니다. 음식 카탈로그는 `food_catalog.csv`, 즐겨찾기는 `food_preferences.json`에 보관합니다. 현재 영양정보 API가 연결되지 않아 확인되지 않은 음식의 칼로리는 추정하지 않습니다. 신뢰할 수 있는 식품 정보를 확인해 직접 입력한 칼로리는 해당 음식 카탈로그에 저장되어 다음 기록에서 다시 사용할 수 있습니다.