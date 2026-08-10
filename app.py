import json
import os
import uuid
from datetime import datetime

import streamlit as st

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "todos.json")
CATEGORIES = ["업무", "개인", "기타"]
CATEGORY_COLORS = {
    "업무": "#2f5fd6",
    "개인": "#c0288f",
    "기타": "#5b6270",
}
CATEGORY_BG = {
    "업무": "#e0ecff",
    "개인": "#fce7f6",
    "기타": "#eef0f2",
}


def load_todos():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_todos(todos):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)


def escape_md(text):
    for ch in ["\\", "*", "_", "`", "[", "]"]:
        text = text.replace(ch, "\\" + ch)
    return text


def category_badge(category):
    color = CATEGORY_COLORS.get(category, "#5b6270")
    bg = CATEGORY_BG.get(category, "#eef0f2")
    return (
        f"<span style='background:{bg};color:{color};padding:2px 10px;"
        f"border-radius:999px;font-size:0.8rem;font-weight:600;'>{category}</span>"
    )


st.set_page_config(page_title="My To-Do", page_icon="✅", layout="centered")

if "todos" not in st.session_state:
    st.session_state.todos = load_todos()
if "editing_id" not in st.session_state:
    st.session_state.editing_id = None
if "confirm_delete_id" not in st.session_state:
    st.session_state.confirm_delete_id = None

st.title("📝 My To-Do")

# 할 일 추가
with st.form("add_todo_form", clear_on_submit=True):
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        new_title = st.text_input(
            "할 일", placeholder="할 일을 입력하세요", label_visibility="collapsed"
        )
    with col2:
        new_category = st.selectbox(
            "카테고리", CATEGORIES, index=2, label_visibility="collapsed"
        )
    with col3:
        submitted = st.form_submit_button("추가", use_container_width=True)

    if submitted:
        if not new_title.strip():
            st.warning("할 일 제목을 입력해주세요.")
        else:
            st.session_state.todos.append(
                {
                    "id": str(uuid.uuid4()),
                    "title": new_title.strip(),
                    "category": new_category,
                    "completed": False,
                    "createdAt": datetime.now().isoformat(),
                }
            )
            save_todos(st.session_state.todos)
            st.rerun()

# 진행률
total = len(st.session_state.todos)
completed_count = sum(1 for t in st.session_state.todos if t["completed"])
percent = int(completed_count / total * 100) if total else 0
st.markdown(f"**{completed_count}/{total} 완료 ({percent}%)**")
st.progress(percent / 100)

# 카테고리 필터
selected_filter = st.radio(
    "카테고리 필터",
    ["전체"] + CATEGORIES,
    horizontal=True,
    label_visibility="collapsed",
)

st.divider()

filtered = (
    st.session_state.todos
    if selected_filter == "전체"
    else [t for t in st.session_state.todos if t["category"] == selected_filter]
)

if not filtered:
    st.info("할 일이 없습니다")

for todo in filtered:
    todo_id = todo["id"]
    with st.container(border=True):
        if st.session_state.editing_id == todo_id:
            ec1, ec2 = st.columns([3, 1])
            with ec1:
                edit_title = st.text_input(
                    "제목 수정",
                    value=todo["title"],
                    key=f"edit_title_{todo_id}",
                    label_visibility="collapsed",
                )
            with ec2:
                edit_category = st.selectbox(
                    "카테고리 수정",
                    CATEGORIES,
                    index=CATEGORIES.index(todo["category"]),
                    key=f"edit_cat_{todo_id}",
                    label_visibility="collapsed",
                )
            bc1, bc2 = st.columns(2)
            with bc1:
                if st.button("저장", key=f"save_{todo_id}", use_container_width=True):
                    if not edit_title.strip():
                        st.warning("할 일 제목을 입력해주세요.")
                    else:
                        todo["title"] = edit_title.strip()
                        todo["category"] = edit_category
                        st.session_state.editing_id = None
                        st.session_state.pop(f"edit_title_{todo_id}", None)
                        st.session_state.pop(f"edit_cat_{todo_id}", None)
                        save_todos(st.session_state.todos)
                        st.rerun()
            with bc2:
                if st.button("취소", key=f"cancel_{todo_id}", use_container_width=True):
                    st.session_state.editing_id = None
                    st.session_state.pop(f"edit_title_{todo_id}", None)
                    st.session_state.pop(f"edit_cat_{todo_id}", None)
                    st.rerun()
        else:
            c1, c2, c3, c4, c5 = st.columns([0.6, 3, 1.2, 1, 1])
            with c1:
                checked = st.checkbox(
                    "완료",
                    value=todo["completed"],
                    key=f"check_{todo_id}",
                    label_visibility="collapsed",
                )
                if checked != todo["completed"]:
                    todo["completed"] = checked
                    save_todos(st.session_state.todos)
                    st.rerun()
            with c2:
                title_text = escape_md(todo["title"])
                if todo["completed"]:
                    st.markdown(f"~~{title_text}~~")
                else:
                    st.markdown(title_text)
            with c3:
                st.markdown(category_badge(todo["category"]), unsafe_allow_html=True)
            with c4:
                if st.button("수정", key=f"edit_{todo_id}", use_container_width=True):
                    st.session_state.editing_id = todo_id
                    st.session_state.confirm_delete_id = None
                    st.rerun()
            with c5:
                if st.session_state.confirm_delete_id == todo_id:
                    if st.button(
                        "확인?", key=f"confirm_del_{todo_id}", use_container_width=True
                    ):
                        st.session_state.todos = [
                            t for t in st.session_state.todos if t["id"] != todo_id
                        ]
                        st.session_state.confirm_delete_id = None
                        save_todos(st.session_state.todos)
                        st.rerun()
                else:
                    if st.button(
                        "삭제", key=f"delete_{todo_id}", use_container_width=True
                    ):
                        st.session_state.confirm_delete_id = todo_id
                        st.rerun()
