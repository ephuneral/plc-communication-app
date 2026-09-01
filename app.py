import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import io

# Настройка страницы
st.set_page_config(page_title="Поиск труб", layout="wide")

API_URL = "http://localhost:8000"

st.title("Архив испытаний")

# === ИНИЦИАЛИЗАЦИЯ SESSION STATE ===
if 'pipes_data' not in st.session_state:
    st.session_state.pipes_data = []
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1
if 'total_pages' not in st.session_state:
    st.session_state.total_pages = 1
if 'total_records' not in st.session_state:
    st.session_state.total_records = 0
if 'search_params' not in st.session_state:
    st.session_state.search_params = {}

# === ФУНКЦИЯ ЗАГРУЗКИ ДАННЫХ ===
def load_data(page: int):
    with st.spinner("Загрузка данных..."):
        params = {
            "page": page,
            "page_size": 50,
            **st.session_state.search_params
        }

        try:
            response = requests.get(f"{API_URL}/pipes", params=params)
            response.raise_for_status()
            data = response.json()

            pipes_data = data.get("items", [])
            total = data.get("total", 0)
            total_pages = data.get("pages", 1)

            st.session_state.total_records = total
            st.session_state.total_pages = total_pages
            st.session_state.current_page = page

            if not pipes_data:
                st.warning("Ничего не найдено по заданным критериям.")
                st.session_state.pipes_data = []
                st.session_state.df = pd.DataFrame()
            else:
                df = pd.DataFrame(pipes_data)
                if "ts" in df.columns:
                    df["ts"] = pd.to_datetime(df["ts"], format='ISO8601').dt.strftime("%d/%m/%Y %H:%M:%S")

                result_map = {0: "ОТСУТ", 1: "НЕ ГОД", 2: "ГОД"}
                if "result" in df.columns:
                    df["result"] = df["result"].map(result_map).fillna(df["result"])

                st.session_state.pipes_data = pipes_data
                st.session_state.df = df

        except requests.exceptions.ConnectionError:
            st.error("Не удалось подключиться к API. Убедитесь, что FastAPI запущен.")
        except Exception as e:
            st.error(f"Произошла ошибка: {e}")

# === АВТОЗАГРУЗКА ===
if 'initialized' not in st.session_state:
    load_data(1)
    st.session_state.initialized = True

# === ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ===
def safe_int(value: str) -> int:
    value = value.strip()
    if value.isdigit():
        return int(value)
    return 0

# === БОКОВАЯ ПАНЕЛЬ ===
st.sidebar.header("Параметры поиска")

serial_number_str = st.sidebar.text_input("Серийный номер", value="0")
factory_number_str = st.sidebar.text_input("Заводской номер", value="0")
diameter_str = st.sidebar.text_input("Диаметр", value="0")
thickness_str = st.sidebar.text_input("Толщина", value="0")

for name, val in [
    ("Серийный номер", serial_number_str),
    ("Заводской номер", factory_number_str),
    ("Диаметр", diameter_str),
    ("Толщина", thickness_str),
]:
    if val.strip() and not val.strip().isdigit():
        st.sidebar.error(f"Поле '{name}' должно содержать только цифры")

serial_number = safe_int(serial_number_str)
factory_number = safe_int(factory_number_str)
diameter = safe_int(diameter_str)
thickness = safe_int(thickness_str)

col1, col2 = st.sidebar.columns(2)
with col1:
    date_from = st.date_input("Дата от", value=None, format="DD/MM/YYYY")
with col2:
    date_to = st.date_input("Дата до", value=None, format="DD/MM/YYYY")

if st.sidebar.button("Найти", type="primary"):
    st.session_state.search_params = {
        "serial_number": serial_number if serial_number > 0 else None,
        "factory_number": factory_number if factory_number > 0 else None,
        "diameter": diameter if diameter > 0 else None,
        "thickness": thickness if thickness > 0 else None,
    }
    if date_from:
        st.session_state.search_params["date_from"] = date_from.isoformat()
    if date_to:
        st.session_state.search_params["date_to"] = date_to.isoformat()
    load_data(1)

# === ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ ===
if not st.session_state.df.empty:
    df = st.session_state.df
    pipes_data = st.session_state.pipes_data

    st.subheader("Результаты поиска")
    st.info(f"Страница {st.session_state.current_page} из {st.session_state.total_pages} (всего записей: {st.session_state.total_records})")

    cols_to_show = [col for col in df.columns if col not in ['graph_x', 'graph_y']]

    column_names = {
        'id': 'ID', 'ts': 'Время', 'length': 'Длина', 'diameter': 'Диаметр',
        'thickness': 'Толщина', 'serial_number': 'Серийный номер',
        'factory_number': 'Заводской номер', 'operator': 'Оператор',
        'pressure_start': 'Давление старт', 'pressure_end': 'Давление конец',
        'pressure_target': 'Давление цель', 'duration': 'Длительность', 'result': 'Результат'
    }
    df_display = df[cols_to_show].rename(columns=column_names)

    # Кнопка скачивания таблицы
    excel_table = io.BytesIO()
    with pd.ExcelWriter(excel_table, engine='openpyxl') as writer:
        df_display.to_excel(writer, sheet_name="Список труб", index=False)
    excel_table.seek(0)
    st.download_button(
        label="Скачать таблицу (Excel)",
        data=excel_table,
        file_name="pipes_list.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # === ТАБЛИЦА НА ВСЮ ВЫСОТУ (без внутреннего скролла) ===
    # Высота рассчитывается: ~35px на строку + 50px на заголовок
    table_height = len(df_display) * 35 + 50
    st.dataframe(df_display, width='stretch', hide_index=True, height=table_height)

    # === ПАГИНАЦИЯ ===
    col_prev, col_mid, col_next = st.columns([1, 3, 1])

    with col_prev:
        if st.session_state.current_page > 1:
            if st.button("️Предыдущая", use_container_width=True):
                load_data(st.session_state.current_page - 1)
                st.rerun()

    with col_mid:
        st.empty()

    with col_next:
        if st.session_state.current_page < st.session_state.total_pages:
            if st.button("Следующая", use_container_width=True):
                load_data(st.session_state.current_page + 1)
                st.rerun()

    # === ВЫБОР ТРУБЫ И КНОПКА СКАЧИВАНИЯ ГРАФИКА ===
    st.subheader(" График испытания")

    if len(pipes_data) > 1:
        options = [f"ID: {p['id']} | Серийный: {p['serial_number']}" for p in pipes_data]
        selected_idx = st.selectbox(
            "Выберите трубу для отображения графика:",
            range(len(pipes_data)),
            format_func=lambda i: options[i],
            key="pipe_selector"
        )
        selected_pipe = pipes_data[selected_idx]
    else:
        selected_pipe = pipes_data[0]

    graph_x = selected_pipe.get("graph_x", [])
    graph_y = selected_pipe.get("graph_y", [])

    while graph_x and graph_x[-1] == 0 and graph_y[-1] == 0:
        graph_x.pop()
        graph_y.pop()

    if graph_x and graph_y:
        # Кнопка скачивания графика
        graph_df = pd.DataFrame({
            "Время, сек": [x * 0.1 for x in graph_x],
            "Давление, бар": graph_y
        })

        excel_graph = io.BytesIO()
        with pd.ExcelWriter(excel_graph, engine='openpyxl') as writer:
            graph_df.to_excel(writer, sheet_name="График", index=False)
        excel_graph.seek(0)

        st.download_button(
            label="Скачать график (Excel)",
            data=excel_graph,
            file_name=f"pipe_{selected_pipe['ts']}_{selected_pipe['serial_number']}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # === ГРАФИК ЗАКОММЕНТИРОВАН ===
        # graph_x_seconds = [x * 0.1 for x in graph_x]
        #
        # fig = go.Figure()
        # fig.add_trace(go.Scatter(
        #     x=graph_x_seconds, y=graph_y, mode='lines',
        #     line=dict(color='royalblue', width=2), name='Давление'
        # ))
        #
        # target_pressure = selected_pipe.get("pressure_target", 0)
        # if target_pressure > 0:
        #     fig.add_hline(
        #         y=target_pressure, line_dash="dash", line_color="red",
        #         annotation_text=f"Цель: {target_pressure} бар",
        #         annotation_position="top right"
        #     )
        #
        # fig.update_layout(
        #     title=f"График испытания (Серийный: {selected_pipe['serial_number']})",
        #     xaxis_title="Время, сек", yaxis_title="Давление, бар",
        #     hovermode="closest", template="plotly_white"
        # )
        # fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
        # fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
        # st.plotly_chart(fig, width='stretch')
    else:
        st.info("Для выбранной трубы отсутствуют данные графика.")
else:
    st.info(" Добро пожаловать! Используйте фильтры слева для поиска труб.")