import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from st_supabase_connection import SupabaseConnection
from streamlit_image_coordinates import streamlit_image_coordinates
from scipy.ndimage import gaussian_filter
from matplotlib.colors import LinearSegmentedColormap, Normalize

st.set_page_config(layout="wide", page_title="DAM Battlegrounds Heatmap")

if "last_clicked_coords" not in st.session_state:
    st.session_state.last_clicked_coords = None
if "show_success" not in st.session_state:
    st.session_state.show_success = None

st.markdown("""
    <style>
    [data-testid="stHorizontalBlock"] { align-items: flex-start !important; }
    .main { background-color: #0e1117; color: white; }
    h3 { font-family: 'Courier New', Courier, monospace; color: #00FF66; }
    </style>
    """, unsafe_allow_html=True)

st.title("Dam Battlegrounds Heatmap")

MAP_IMAGE = "DamBattlegrounds.png"
img = plt.imread(MAP_IMAGE)
img_h, img_w = img.shape[:2]

conn = st.connection("supabase", type=SupabaseConnection)


def create_glow_map(base_color):
    return LinearSegmentedColormap.from_list("glow", ["#00000000", base_color, "#FFFFFF"])


THEMES = {
    "loot": {"cmap": create_glow_map("#00FF66")},
    "fight": {"cmap": create_glow_map("#FFCC00")},
    "death": {"cmap": create_glow_map("#FF0033")},
    "plant_mode": {"cmap": create_glow_map("#AFEEEE")}
}


def reset_filters():
    st.session_state.sel_cat_box = "None"
    st.session_state.sel_item_box = "None"
    st.session_state.sel_plant_box = "None"


if st.session_state.show_success:
    st.toast(st.session_state.show_success, icon="✅")
    st.session_state.show_success = None

with st.sidebar:
    st.header("🎮 Controls")

    cat_val = st.session_state.get("sel_cat_box", "None")
    item_val = st.session_state.get("sel_item_box", "None")
    plant_val = st.session_state.get("sel_plant_box", "None")

    active_event = st.selectbox(
        "1. Select a Event",
        ["None", "loot 💰", "fight ⚔️", "death 💀"],
        key="sel_cat_box",
        disabled=(item_val != "None" or plant_val != "None"),
    )

    selected_item = st.selectbox(
        "2. Select a Specific Item",
        [
            "None",
            "Rusted gears ⚙️",
            "Laboratory Reagents 🧪",
            "Antiseptics 🧼",
            "Power Rods 🔋",
            "Advanced electrical components ⚡",
            "Mechanical components 🛠️",
            "Batteries 🔋",
            "Key cards 💳",
            "Industrial chargers 🔌",
            "Industrial magnets 🧲"
        ],
        key="sel_item_box",
        disabled=(cat_val != "None" and "loot" not in cat_val) or (plant_val != "None"),
    )

    selected_plant = st.selectbox(
        "2. Select a Specific Plant",
        [
            "None",
            "Mushrooms 🍄",
            "Prickly Pears 🌵",
            "Great Mullein 🌿",
            "Agave 🌵",
            "Candleberries 🕯️",
            "Moss 🟢"
        ],
        key="sel_plant_box",
        disabled=(cat_val != "None" or item_val != "None"),
    )

    st.button("🔄 Reset All Filters", on_click=reset_filters, use_container_width=True)

    st.divider()
    st.subheader("Visual Tuning")
    overlay_fight = st.checkbox("Overlay 'Fight' Events ⚔️", value=False)
    sigma_val = st.slider("Heat Intensity (Blur)", 1, 25, 10)
    alpha_val = st.slider("Opacity", 0.1, 1.0, 0.75)
    show_dots = st.checkbox("Show Precise Points", value=False)

    st.divider()
    render_btn = st.button("🚀 Render Heatmap", use_container_width=True)

    st.divider()
    st.caption("""
            **Disclaimer:** This is an early-version fan tool. Map image is by the Metaforge Team.

            • Data is crowdsourced and may be inaccurate.
            • Not affiliated with Embark Studios.
            • Locations may change after game updates.
            • No personal data is collected
        """)
    st.caption("""
               **Version** 0.1.1 
           """)

clean_item = selected_item.split(" ")[0] if " " in selected_item else selected_item
clean_plant = selected_plant.split(" ")[0] if " " in selected_plant else selected_plant
clean_event = active_event.split(" ")[0] if " " in active_event else active_event

final_item = clean_item if clean_item != "None" else None
final_plant = clean_plant if clean_plant != "None" else None
final_event = clean_event if clean_event != "None" else None

if final_plant:
    current_mode = "plant_mode"
elif final_event:
    current_mode = final_event
else:
    current_mode = None

if final_item:
    final_event = "loot"
    current_mode = "loot"

col1, col2 = st.columns([1, 1])

with col1:
    if not current_mode:
        st.info("💡 Select an **Event**, **Item** or a **plant** to log data.")
    else:
        display_label = selected_plant if final_plant else (selected_item if final_item else active_event)
        st.subheader(f"You can now log {display_label.upper()}")

        value = streamlit_image_coordinates(MAP_IMAGE, key="map_logger", use_column_width=True)

        if value is not None and value != st.session_state.last_clicked_coords:
            scale_x = img_w / value["width"]
            scale_y = img_h / value["height"]
            real_x = int(value["x"] * scale_x)
            real_y = int(value["y"] * scale_y)

            try:
                payload = {
                    "x": real_x,
                    "y": real_y,
                    "event_type": final_event if final_event else "None",
                    "item_name": final_item if final_item else "None",
                    "plant": final_plant if final_plant else "None"
                }

                conn.table("events").insert(payload).execute()

                st.session_state.last_clicked_coords = value
                st.session_state.show_success = f"Logged {display_label} at {real_x}, {real_y}"
                st.rerun()
            except Exception as e:
                st.error(f"Save failed: {e}")

with col2:
    if current_mode:
        title_suffix = " + FIGHT OVERLAY ⚔️" if overlay_fight else ""
        st.subheader(f"Map for {display_label.upper()}{title_suffix}")

    if render_btn:
        if not current_mode:
            st.error("Select a filter first!")
        else:
            try:
                response = conn.table("events").select("*").execute()
                raw_data = response.data if hasattr(response, 'data') else response

                if raw_data:
                    df = pd.DataFrame(raw_data)

                    fig, ax = plt.subplots(figsize=(10, 10 * (img_h / img_w)))
                    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
                    ax.axis("off")
                    ax.imshow(img, aspect='equal')


                    def plot_heat(data_subset, mode_key):
                        if not data_subset.empty:
                            data_subset['x'] = pd.to_numeric(data_subset['x'])
                            data_subset['y'] = pd.to_numeric(data_subset['y'])
                            h, _, _ = np.histogram2d(
                                data_subset["x"], data_subset["y"],
                                bins=500, range=[[0, img_w], [0, img_h]]
                            )
                            h_smooth = gaussian_filter(h.T, sigma=sigma_val)
                            thresh = h_smooth.max() * 0.02
                            h_smooth = np.ma.masked_where(h_smooth <= thresh, h_smooth)
                            ax.imshow(
                                h_smooth,
                                extent=[0, img_w, img_h, 0],
                                cmap=THEMES[mode_key]["cmap"],
                                alpha=alpha_val,
                                origin='upper',
                                aspect='equal',
                                interpolation='bilinear',
                                norm=Normalize(vmin=thresh, vmax=h_smooth.max())
                            )
                            if show_dots:
                                ax.scatter(data_subset["x"], data_subset["y"], c='#00FFFF', s=8, alpha=0.9)
                            return True
                        return False


                    if final_plant:
                        primary_subset = df[df["plant"] == final_plant].copy()
                    else:
                        primary_subset = df[df["event_type"] == final_event].copy()
                        if final_item:
                            primary_subset = primary_subset[primary_subset["item_name"] == final_item]

                    has_primary = plot_heat(primary_subset, current_mode)

                    if overlay_fight and current_mode != "fight":
                        fight_subset = df[df["event_type"] == "fight"].copy()
                        plot_heat(fight_subset, "fight")

                    if has_primary:
                        st.pyplot(fig, use_container_width=True)
                    else:
                        st.info(f"No points found for {display_label}.")
            except Exception as e:
                st.error(f"Render Error: {e}")
    else:
        st.info("Click 'Render' to view the map.")