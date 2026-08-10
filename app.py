import json
import os
import uuid

import streamlit as st

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backpacking_checklist_data.json")

# Category: { id, name, items: Item[] }
# Item: { id, name, brand, model, price, weight: { value, unit }, packed: bool }


def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            parsed = json.load(f)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(st.session_state.categories, f, indent=2)
    except OSError as e:
        st.warning(f"Could not save checklist data: {e}")


def generate_id():
    return str(uuid.uuid4())


def find_category(category_id):
    for c in st.session_state.categories:
        if c["id"] == category_id:
            return c
    return None


def parse_number_or_none(text):
    if text is None:
        return None
    text = text.strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def oz_from_weight(weight):
    if not weight or weight.get("value") is None:
        return 0
    return weight["value"] * 16 if weight.get("unit") == "lb" else weight["value"]


def format_weight_oz(total_oz):
    return f"{total_oz / 16:.2f} lb"


def item_details_text(item):
    parts = [p for p in (item.get("brand"), item.get("model")) if p]
    text = " ".join(parts)
    if item.get("price") is not None:
        text += (" · " if text else "") + f"${item['price']:.2f}"
    weight = item.get("weight") or {}
    if weight.get("value") is not None:
        text += (" · " if text else "") + f"{weight['value']:g} {weight.get('unit', 'oz')}"
    return text


# ---- Session state ----

if "categories" not in st.session_state:
    st.session_state.categories = load_data()
if "editing_category_id" not in st.session_state:
    st.session_state.editing_category_id = None
if "editing_item_id" not in st.session_state:
    st.session_state.editing_item_id = None
if "open_add_item_ids" not in st.session_state:
    st.session_state.open_add_item_ids = set()


# ---- Confirmation dialogs ----

@st.dialog("Reset all checkboxes?")
def confirm_reset_dialog():
    st.write("This will mark every item as unpacked. Your gear list itself won't be deleted.")
    c1, c2 = st.columns(2)
    if c1.button("Reset", type="primary", use_container_width=True):
        for category in st.session_state.categories:
            for item in category["items"]:
                item["packed"] = False
        save_data()
        st.rerun()
    if c2.button("Cancel", use_container_width=True):
        st.rerun()


@st.dialog("Delete category?")
def confirm_delete_category_dialog(category_id, category_name):
    st.write(f'Delete category "{category_name}" and all its items? This cannot be undone.')
    c1, c2 = st.columns(2)
    if c1.button("Delete", type="primary", use_container_width=True):
        st.session_state.categories = [c for c in st.session_state.categories if c["id"] != category_id]
        save_data()
        st.rerun()
    if c2.button("Cancel", use_container_width=True):
        st.rerun()


# ---- Item rendering ----

def render_item_row(category, item):
    cols = st.columns([0.6, 3, 3, 0.7, 0.7])

    packed = cols[0].checkbox(
        "Packed", value=item["packed"], key=f"packed_{item['id']}", label_visibility="collapsed"
    )
    if packed != item["packed"]:
        item["packed"] = packed
        save_data()

    details = item_details_text(item)
    if item["packed"]:
        cols[1].markdown(f"~~**{item['name']}**~~")
        if details:
            cols[2].caption(f"~~{details}~~")
    else:
        cols[1].markdown(f"**{item['name']}**")
        if details:
            cols[2].caption(details)

    if cols[3].button("✏️", key=f"edit_item_{item['id']}", help="Edit item"):
        st.session_state.editing_item_id = item["id"]
        st.rerun()
    if cols[4].button("\U0001f5d1️", key=f"delete_item_{item['id']}", help="Delete item"):
        category["items"] = [i for i in category["items"] if i["id"] != item["id"]]
        save_data()
        st.rerun()


def render_item_edit_form(category, item):
    with st.form(f"edit_item_form_{item['id']}"):
        name = st.text_input("Item name", value=item["name"])
        c1, c2 = st.columns(2)
        brand = c1.text_input("Brand", value=item.get("brand") or "")
        model = c2.text_input("Model", value=item.get("model") or "")

        c3, c4, c5 = st.columns(3)
        price_default = "" if item.get("price") is None else str(item["price"])
        price_text = c3.text_input("Price ($)", value=price_default, placeholder="optional")
        weight = item.get("weight") or {}
        weight_default = "" if weight.get("value") is None else str(weight["value"])
        weight_text = c4.text_input("Weight", value=weight_default, placeholder="optional")
        unit_options = ["oz", "lb"]
        current_unit = weight.get("unit", "oz")
        weight_unit = c5.selectbox(
            "Unit", unit_options, index=unit_options.index(current_unit) if current_unit in unit_options else 0
        )

        s1, s2 = st.columns(2)
        save_clicked = s1.form_submit_button("Save")
        cancel_clicked = s2.form_submit_button("Cancel")

    if save_clicked:
        trimmed = name.strip()
        if not trimmed:
            st.error("Item name cannot be blank.")
        else:
            item["name"] = trimmed
            item["brand"] = brand.strip()
            item["model"] = model.strip()
            item["price"] = parse_number_or_none(price_text)
            item["weight"] = {"value": parse_number_or_none(weight_text), "unit": weight_unit}
            st.session_state.editing_item_id = None
            save_data()
            st.rerun()
    if cancel_clicked:
        st.session_state.editing_item_id = None
        st.rerun()


def render_add_item_form(category):
    with st.form(f"add_item_form_{category['id']}", clear_on_submit=True):
        name = st.text_input("Item name")
        c1, c2 = st.columns(2)
        brand = c1.text_input("Brand")
        model = c2.text_input("Model")
        c3, c4, c5 = st.columns(3)
        price_text = c3.text_input("Price ($)", placeholder="optional")
        weight_text = c4.text_input("Weight", placeholder="optional")
        weight_unit = c5.selectbox("Unit", ["oz", "lb"])

        s1, s2 = st.columns(2)
        add_clicked = s1.form_submit_button("Add Item")
        cancel_clicked = s2.form_submit_button("Cancel")

    if add_clicked:
        trimmed = name.strip()
        if not trimmed:
            st.error("Item name cannot be blank.")
        else:
            category["items"].append(
                {
                    "id": generate_id(),
                    "name": trimmed,
                    "brand": brand.strip(),
                    "model": model.strip(),
                    "price": parse_number_or_none(price_text),
                    "weight": {"value": parse_number_or_none(weight_text), "unit": weight_unit},
                    "packed": False,
                }
            )
            save_data()
            st.rerun()
    if cancel_clicked:
        st.session_state.open_add_item_ids.discard(category["id"])
        st.rerun()


# ---- Page ----

st.set_page_config(page_title="Backpacking Checklist", page_icon="\U0001f392", layout="centered")
st.title("\U0001f392 Backpacking Checklist")
st.caption("Data autosaves to a local file next to this script — no account or server needed.")

summary_container = st.container()
st.divider()

with st.form("add_category_form", clear_on_submit=True):
    new_category_name = st.text_input("New category name", placeholder="e.g. Shelter, Cooking")
    add_category_clicked = st.form_submit_button("+ Add Category")
if add_category_clicked:
    trimmed = new_category_name.strip()
    if not trimmed:
        st.error("Category name cannot be blank.")
    else:
        st.session_state.categories.append({"id": generate_id(), "name": trimmed, "items": []})
        save_data()
        st.rerun()

if not st.session_state.categories:
    st.info("No categories yet. Add one above to get started.")
else:
    for category in st.session_state.categories:
        packed_count = sum(1 for i in category["items"] if i["packed"])
        total_count = len(category["items"])
        editing_this_category = st.session_state.editing_category_id == category["id"]
        label = category["name"] if editing_this_category else f"{category['name']}  ({packed_count}/{total_count} packed)"

        with st.expander(label, expanded=True):
            if editing_this_category:
                with st.form(f"rename_category_form_{category['id']}"):
                    new_name = st.text_input("Category name", value=category["name"])
                    r1, r2 = st.columns(2)
                    rename_save_clicked = r1.form_submit_button("Save")
                    rename_cancel_clicked = r2.form_submit_button("Cancel")
                if rename_save_clicked:
                    trimmed = new_name.strip()
                    if not trimmed:
                        st.error("Category name cannot be blank.")
                    else:
                        category["name"] = trimmed
                        st.session_state.editing_category_id = None
                        save_data()
                        st.rerun()
                if rename_cancel_clicked:
                    st.session_state.editing_category_id = None
                    st.rerun()
            else:
                action_col1, action_col2, _ = st.columns([1, 1, 4])
                if action_col1.button("✏️ Rename", key=f"rename_cat_btn_{category['id']}"):
                    st.session_state.editing_category_id = category["id"]
                    st.rerun()
                if action_col2.button("\U0001f5d1️ Delete", key=f"delete_cat_btn_{category['id']}"):
                    confirm_delete_category_dialog(category["id"], category["name"])

            if not category["items"]:
                st.caption("No items in this category yet.")
            else:
                for item in category["items"]:
                    if st.session_state.editing_item_id == item["id"]:
                        render_item_edit_form(category, item)
                    else:
                        render_item_row(category, item)

            if category["id"] in st.session_state.open_add_item_ids:
                render_add_item_form(category)
            elif st.button("+ Add Item", key=f"open_add_item_{category['id']}"):
                st.session_state.open_add_item_ids.add(category["id"])
                st.rerun()

# Rendered last so it reflects any mutations made above during this run,
# but placed in a container reserved at the top of the page.
total_items = 0
total_packed = 0
total_oz = 0
total_price = 0.0
for category in st.session_state.categories:
    for item in category["items"]:
        total_items += 1
        if item["packed"]:
            total_packed += 1
        total_oz += oz_from_weight(item.get("weight"))
        if item.get("price") is not None:
            total_price += item["price"]

with summary_container:
    m1, m2, m3, m4, m5 = st.columns([1, 1, 1, 1, 1.4])
    m1.metric("Items", total_items)
    m2.metric("Packed", total_packed)
    m3.metric("Total Weight", format_weight_oz(total_oz))
    m4.metric("Total Cost", f"${total_price:.2f}")
    with m5:
        st.write("")
        if st.button("Reset All Checkboxes", use_container_width=True):
            confirm_reset_dialog()
