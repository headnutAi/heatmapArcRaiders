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
    "death": {"cmap": create_glow_map("#FF0033")}
}


def reset_filters():
    st.session_state.sel_cat_box = "None"
    st.session_state.sel_item_box = "None"


if st.session_state.show_success:
    st.toast(st.session_state.show_success, icon="✅")
    st.session_state.show_success = None


with st.sidebar:
    st.header("🎮 Controls")

    cat_val = st.session_state.get("sel_cat_box", "None")
    item_val = st.session_state.get("sel_item_box", "None")

    # 1. Category Selection
    active_event = st.selectbox(
        "1. Select Event Category",
        ["None", "loot", "fight", "death"],
        key="sel_cat_box",
        disabled=(item_val != "None"),
    )

    # 2. Item Selection
    selected_item = st.selectbox(
        "2. OR Select Specific Item",
        ["None", "Rusted gears", "Mushrooms", "Laboratory Reagents", "Antiseptics"],
        key="sel_item_box",
        disabled=(cat_val != "None" and cat_val != "loot"),
    )

    st.button("🔄 Reset All Filters", on_click=reset_filters, use_container_width=True)

    st.divider()
    st.subheader("Visual Tuning")
    sigma_val = st.slider("Heat Intensity (Blur)", 1, 25, 10)
    alpha_val = st.slider("Opacity", 0.1, 1.0, 0.75)
    show_dots = st.checkbox("Show Precise Points", value=False)

    st.divider()
    render_btn = st.button("🚀 Render Heatmap", use_container_width=True)


final_item = selected_item if selected_item != "None" else None
final_event = active_event if active_event != "None" else None


if final_item:
    final_event = "loot"

col1, col2 = st.columns([1, 1])


with col1:
    if not final_event:
        st.info("💡 Select an **Event Category** or an **Item** to log data.")
    else:
        display_label = final_item if final_item else final_event
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
                    "event_type": final_event,
                    "item_name": final_item if final_item else "General"
                }

                conn.table("events").insert(payload).execute()

                st.session_state.last_clicked_coords = value
                st.session_state.show_success = f"Logged {display_label} at {real_x}, {real_y}"
                st.rerun()
            except Exception as e:
                st.error(f"Save failed: {e}")


with col2:
    if final_event:
        st.subheader(f"Map for {(final_item if final_item else final_event).upper()}")


    if render_btn:
        if not final_event:
            st.error("Select a filter first!")
        else:
            try:
                response = conn.table("events").select("*").execute()
                raw_data = response.data if hasattr(response, 'data') else response

                if raw_data:
                    df = pd.DataFrame(raw_data)


                    subset = df[df["event_type"] == final_event].copy()


                    if final_item:
                        subset = subset[subset["item_name"] == final_item]

                    if not subset.empty:
                        subset['x'] = pd.to_numeric(subset['x'])
                        subset['y'] = pd.to_numeric(subset['y'])

                        heatmap, _, _ = np.histogram2d(
                            subset["x"], subset["y"],
                            bins=500, range=[[0, img_w], [0, img_h]]
                        )

                        heatmap_smooth = gaussian_filter(heatmap.T, sigma=sigma_val)
                        threshold = heatmap_smooth.max() * 0.02
                        heatmap_smooth = np.ma.masked_where(heatmap_smooth <= threshold, heatmap_smooth)

                        fig, ax = plt.subplots(figsize=(10, 10 * (img_h / img_w)))
                        plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
                        ax.axis("off")
                        ax.imshow(img, aspect='equal')

                        ax.imshow(
                            heatmap_smooth,
                            extent=[0, img_w, img_h, 0],
                            cmap=THEMES[final_event]["cmap"],
                            alpha=alpha_val,
                            origin='upper',
                            aspect='equal',
                            interpolation='bilinear',
                            norm=Normalize(vmin=threshold, vmax=heatmap_smooth.max())
                        )

                        if show_dots:
                            ax.scatter(subset["x"], subset["y"], c='#00FFFF', s=8, alpha=0.9)

                        st.pyplot(fig, use_container_width=True)
                    else:
                        st.info(f"No points found for {final_item if final_item else final_event}.")
            except Exception as e:
                st.error(f"Render Error: {e}")
    else:
        st.info("Click 'Render' to view the map.")