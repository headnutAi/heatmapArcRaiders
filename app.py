import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from st_supabase_connection import SupabaseConnection
from streamlit_image_coordinates import streamlit_image_coordinates
from scipy.ndimage import gaussian_filter
from matplotlib.colors import LinearSegmentedColormap, Normalize

# ======================
# 1. PAGE SETUP & CSS
# ======================
st.set_page_config(layout="wide", page_title="DAM Battlegrounds Heatmap")

# CSS for perfect alignment, dark theme, and neon accents
st.markdown("""
    <style>
    [data-testid="stHorizontalBlock"] { align-items: flex-start !important; }
    .main { background-color: #0e1117; color: white; }
    div.block-container { padding-top: 1rem; }
    h3 { margin-top: 0rem !important; padding-top: 0rem !important; font-family: 'Courier New', Courier, monospace; color: #00FF66; }
    </style>
    """, unsafe_allow_html=True)

st.title("Dam Battlegrounds Heatmap")

MAP_IMAGE = "DamBattlegrounds.png"
img = plt.imread(MAP_IMAGE)
img_h, img_w = img.shape[:2]


# ======================
# 2. PRO NEON VISUALS
# ======================
# Custom function to create a highly saturated glow from transparent to neon to white-hot
def create_glow_map(base_color):
    return LinearSegmentedColormap.from_list("glow", ["#00000000", base_color, "#FFFFFF"])


THEMES = {
    "loot": {"cmap": create_glow_map("#00FF66"), "label": "loot"},  # Neon Green
    "fight": {"cmap": create_glow_map("#FFCC00"), "label": "fight"},  # Electric Gold
    "death": {"cmap": create_glow_map("#FF0033"), "label": "death"}  # Vivid Blood Red
}

conn = st.connection("supabase", type=SupabaseConnection)

with st.sidebar:
    st.header("🎮 Controls")
    active_event = st.selectbox("Event Category", ["Loot", "Fight", "Death"])

    st.divider()
    st.subheader("Visual Tuning")
    sigma_val = st.slider("Heat Intensity (Blur)", 1, 25, 10)
    alpha_val = st.slider("Opacity", 0.1, 1.0, 0.75)
    show_dots = st.checkbox("Show Precise Points", value=False)

    st.divider()
    render_btn = st.button("🚀 Render/Refresh Heatmap", use_container_width=True)

    st.markdown("---")  # A horizontal line for separation
    st.markdown("### ℹ️ About")
    st.caption("""
            **Disclaimer:** This is a fan-made tool created for the community. 
            It is not affiliated with, endorsed, or sponsored by **Embark Studios**. 
            All game assets, including map imagery, are the property of Embark Studios.
        """)

    st.caption("""
            **Credits:** Map image and zone titles sourced from 
            [MetaForge](https://metaforge.app).
        """)
    st.caption("""
        **Version 0.1.0 (Early Access)** This tool is a community passion project. I am currently in active development 
        using free hosting—if things feel a bit slow during peak raid hours, 
        thanks for your patience!
    """)

# ======================
# 3. LAYOUT (SIDE-BY-SIDE)
# ======================
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader(f"Log your {active_event.upper()}")

    # Capture clicks and scale them accurately
    value = streamlit_image_coordinates(MAP_IMAGE, key="map_logger", use_column_width=True)

    if value:
        scale_x = img_w / value["width"]
        scale_y = img_h / value["height"]
        real_x = int(value["x"] * scale_x)
        real_y = int(value["y"] * scale_y)

        try:
            conn.table("events").insert({
                "x": real_x, "y": real_y, "event_type": active_event
            }).execute()
            st.toast(f"Logged {active_event} at {real_x}, {real_y}", icon="✅")
        except Exception as e:
            st.error(f"Save failed: {e}")

with col2:
    st.subheader("Community map")

    if render_btn:
        try:
            response = conn.table("events").select("*").execute()
            raw_data = response.data if hasattr(response, 'data') else response

            if raw_data:
                df = pd.DataFrame(raw_data)
                subset = df[df["event_type"] == active_event].copy()

                if not subset.empty:
                    subset['x'] = pd.to_numeric(subset['x'])
                    subset['y'] = pd.to_numeric(subset['y'])

                    # 1. Generate High-Res Histogram
                    heatmap, _, _ = np.histogram2d(
                        subset["x"], subset["y"],
                        bins=500,  # High detail for smooth circles
                        range=[[0, img_w], [0, img_h]]
                    )

                    # 2. Smooth & Aggressive Masking
                    heatmap_smooth = gaussian_filter(heatmap.T, sigma=sigma_val)

                    # Thresholding at 2% of peak to remove blurry edges
                    threshold = heatmap_smooth.max() * 0.02
                    heatmap_smooth = np.ma.masked_where(heatmap_smooth <= threshold, heatmap_smooth)

                    # 3. Create Figure (No padding, matches map aspect ratio)
                    fig, ax = plt.subplots(figsize=(10, 10 * (img_h / img_w)))
                    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
                    ax.axis("off")

                    # 4. Draw Background Map
                    ax.imshow(img, aspect='equal')

                    # 5. Draw Saturated Neon Heat
                    ax.imshow(
                        heatmap_smooth,
                        extent=[0, img_w, img_h, 0],
                        cmap=THEMES[active_event]["cmap"],
                        alpha=alpha_val,
                        origin='upper',
                        aspect='equal',
                        interpolation='bilinear',  # Key for smooth neon glow
                        norm=Normalize(vmin=threshold, vmax=heatmap_smooth.max())
                    )

                    if show_dots:
                        # Cyan dots with black glow for visibility
                        ax.scatter(subset["x"], subset["y"], c='#00FFFF', s=8, alpha=0.9, edgecolors='black',
                                   linewidth=0.5)

                    # 6. Render
                    st.pyplot(fig, use_container_width=True)
                    st.caption(f"Visualizing {len(subset)} data points for {active_event.upper()}")
                else:
                    st.info(f"No {active_event} points found yet.")
            else:
                st.warning("Database is empty.")
        except Exception as e:
            st.error(f"Render Error: {e}")
    else:
        # Visual placeholder so the UI doesn't jump
        st.info("Configuration set. Click 'Render' to generate heatmap.")