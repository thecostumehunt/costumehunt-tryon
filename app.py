import streamlit as st
import requests
import io
from PIL import Image
import base64
import os

# ========================================
# PAGE SETUP
# ========================================
st.set_page_config(
    page_title="The Costume Hunt – Try On", 
    layout="centered",
    page_icon="👗"
)

st.title("👗 Virtual Try-On")
st.markdown("**Upload your photo + outfit = AI puts clothes on your body**")
st.caption("Powered by TheCostumeHunt.com • Real AI • Photos auto-deleted")

# ========================================
# SECRETS & STATE
# ========================================
os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]

if "used_free" not in st.session_state:
    st.session_state.used_free = False

# ========================================
# BLOG INTEGRATION
# ========================================
query_params = st.query_params
cloth_url = query_params.get("cloth", "")

# ========================================
# UI - PHOTO UPLOAD
# ========================================
st.subheader("📸 1. Upload Your Photo")
user_image = st.file_uploader(
    "Upload **FULL BODY** photo (standing works best)",
    type=["jpg", "jpeg", "png", "webp"],
    help="Plain background + full torso visible = best AI results"
)

# ========================================
# UI - OUTFIT IMAGE
# ========================================
st.subheader("👗 2. Outfit Image")
col1, col2 = st.columns([4, 1])

with col1:
    if cloth_url:
        try:
            st.image(cloth_url, caption="✅ Auto-loaded from blog", width=300)
        except:
            cloth_url = ""
            st.warning("Invalid image URL")
    else:
        cloth_url = st.text_input(
            "Paste outfit image URL from thecostumehunt.com",
            placeholder="https://thecostumehunt.com/wp-content/uploads/outfit.webp"
        )

with col2:
    st.info("💡 **Best Results:**\n• Single garment\n• Front-facing\n• Full top visible\n• Plain background")

# ========================================
# IMAGE HELPERS
# ========================================

def pad_to_square(img, bg_color=(255, 255, 255)):
    """Pad image to square to stabilize proportions"""
    w, h = img.size
    s = max(w, h)
    new_img = Image.new("RGB", (s, s), bg_color)
    new_img.paste(img, ((s - w) // 2, (s - h) // 2))
    return new_img

def normalize_image(image_data, max_side=1024):
    """Resize proportionally + square pad to reduce garment drift"""
    if hasattr(image_data, "seek"):
        image_data.seek(0)

    img = Image.open(image_data).convert("RGB")

    # Proportional resize
    w, h = img.size
    scale = max_side / max(w, h)
    if scale < 1:
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    # Square padding (important)
    img = pad_to_square(img)

    return img

def image_to_base64(image_data):
    img = normalize_image(image_data)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"

# ========================================
# AI TRY-ON BUTTON
# ========================================
if st.button("✨ **GENERATE AI TRY-ON** ✨", type="primary", use_container_width=True):

    if st.session_state.used_free:
        st.error("🆓 **Free try used!** Refresh page for 1 more free try.")
        st.markdown("### 🚀 **Unlimited Try-Ons Coming Soon**")
        st.stop()

    if not user_image:
        st.error("📸 **Upload your photo first**")
        st.stop()

    if not cloth_url:
        st.error("👗 **Enter outfit image URL**")
        st.stop()

    with st.spinner("🎨 **Preserving proportions & garment boundaries... 20–40s**"):
        try:
            # Prepare images
            person_b64 = image_to_base64(user_image)

            outfit_response = requests.get(cloth_url, timeout=20)
            outfit_response.raise_for_status()
            outfit_b64 = image_to_base64(io.BytesIO(outfit_response.content))

            # ====================================
            # FAL API CALL (GARMENT-BIASED MODE)
            # ====================================
            FAL_URL = "https://fal.run/fal-ai/idm-vton"
            headers = {
                "Authorization": f"Key {st.secrets['FAL_KEY']}",
                "Content-Type": "application/json"
            }

            payload = {
                "human_image_url": person_b64,
                "garment_image_url": outfit_b64,
                "description": (
                    "same person, preserve identity and pose, preserve body proportions, "
                    "transfer the exact garment from the reference image, "
                    "top length must match the reference garment, "
                    "hemline position must stay consistent, "
                    "do not crop the top, do not extend the top, "
                    "sleeve length must match the reference, "
                    "realistic try-on, no stylization, no beautification, no body reshaping"
                )
            }

            api_response = requests.post(FAL_URL, json=payload, headers=headers, timeout=120)
            api_response.raise_for_status()
            result = api_response.json()

            # ====================================
            # EXTRACT RESULT (ROBUST)
            # ====================================
            output_image = None

            if "images" in result and result["images"]:
                first = result["images"][0]
                if isinstance(first, dict) and "url" in first:
                    output_image = first["url"]
                else:
                    output_image = first

            elif "image" in result:
                if isinstance(result["image"], dict) and "url" in result["image"]:
                    output_image = result["image"]["url"]
                else:
                    output_image = result["image"]

            elif "output" in result:
                output_image = result["output"]

            if not output_image:
                st.error("No image returned from AI")
                st.json(result)
                st.stop()

            # ====================================
            # DISPLAY RESULT
            # ====================================
            image_bytes = None

            if isinstance(output_image, str):

                if output_image.startswith("http"):
                    st.image(output_image, caption="✅ **YOUR AI TRY-ON RESULT**", use_column_width=True)
                    image_bytes = requests.get(output_image).content

                elif "base64" in output_image:
                    image_bytes = base64.b64decode(output_image.split(",")[-1])
                    result_img = Image.open(io.BytesIO(image_bytes))
                    st.image(result_img, caption="✅ **YOUR AI TRY-ON RESULT**", use_column_width=True)

                else:
                    st.error("Unknown image format returned")
                    st.write(output_image[:200])
                    st.stop()

            else:
                st.error("Unsupported image format returned by AI")
                st.stop()

            # ====================================
            # SUCCESS UI
            # ====================================
            st.success("🎉 **Try-on complete — proportions & garment length biased**")
            st.balloons()

            st.session_state.used_free = True

            col1, col2, col3 = st.columns(3)
            with col1:
                if image_bytes:
                    st.download_button(
                        label="💾 Download Result",
                        data=image_bytes,
                        file_name="thecostumehunt-tryon.png",
                        mime="image/png"
