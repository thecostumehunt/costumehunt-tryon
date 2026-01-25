import streamlit as st
import tempfile
import requests
import os
from PIL import Image
import fal_client
import traceback

# ---------------------------
# PAGE SETUP
# ---------------------------
st.set_page_config(page_title="The Costume Hunt – Try On", layout="centered")

st.title("👗 Try This Outfit On Yourself")
st.write("Upload your full-body photo and preview how a full outfit looks on you.")
st.caption("Powered by TheCostumeHunt.com • Photos are processed temporarily and not stored.")

# ---------------------------
# API KEY
# ---------------------------
try:
    os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]
except:
    st.error("Please set FAL_KEY in Streamlit Secrets")
    st.stop()

# ---------------------------
# SESSION CONTROL (1 FREE TRY)
# ---------------------------
if "free_used" not in st.session_state:
    st.session_state.free_used = False

query_params = st.query_params
cloth_url = query_params.get("cloth", None)

st.subheader("1. Upload your photo")
user_image = st.file_uploader(
    "Full-body photo (standing pose, good light)",
    type=["jpg", "jpeg", "png", "webp"]
)

st.subheader("2. Outfit image (full outfit)")
if cloth_url:
    try:
        st.image(cloth_url, caption="Selected outfit", width=260)
    except:
        cloth_url = None
        st.warning("Could not load outfit image. Paste a direct image URL.")
else:
    cloth_url = st.text_input("Paste outfit image URL")

st.subheader("3. Generate try-on")

def save_temp_image(file):
    img = Image.open(file).convert("RGB")
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(temp.name, format="PNG")
    temp.close()
    return temp.name

def download_image(url):
    r = requests.get(url, stream=True, timeout=30)
    r.raise_for_status()
    img = Image.open(r.raw).convert("RGB")
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(temp.name, format="PNG")
    temp.close()
    return temp.name

if st.button("✨ Try it on"):
    if st.session_state.free_used:
        st.warning("Free try-on used. Try again later.")
        st.stop()

    if not user_image or not cloth_url:
        st.warning("Upload both your photo and an outfit image.")
        st.stop()

    with st.spinner("Processing… please wait"):
        person_path = None
        cloth_path = None

        try:
            person_path = save_temp_image(user_image)
            cloth_path = download_image(cloth_url)

            result = fal_client.run(
                "fal-ai/koloa-virtual-tryon",
                arguments={
                    "human_image": open(person_path, "rb"),
                    "garment_image": open(cloth_path, "rb"),
                    "category": "full",
                    "mode": "quality"
                }
            )

            # Show debug info
            st.write("👉 Raw API response:", result)

            if "image" not in result or "url" not in result["image"]:
                raise ValueError("Invalid result from FAL – no image URL")

            output_url = result["image"]["url"]
            st.image(output_url, caption="Your try-on result", use_column_width=True)
            st.success("🎉 Try-on complete!")
            st.session_state.free_used = True

        except Exception as e:
            st.error("🚨 Try-on processing failed.")
            st.write("**Error type:**", type(e).__name__)
            st.write("**Error message:**", str(e))
            st.write("**Traceback (debug):**")
            st.text(traceback.format_exc())

            st.info("""
                **Tips for success:**
                • Full body photo (head + feet visible)  
                • Clear outfit image with plain background  
                • Avoid text, logos, collages in outfit image
            """)

        finally:
            try:
                if person_path and os.path.exists(person_path):
                    os.remove(person_path)
                if cloth_path and os.path.exists(cloth_path):
                    os.remove(cloth_path)
            except:
                pass

st.markdown("---")
st.write("🔒 Photos are processed temporarily and auto-deleted.")
st.write("🩷 Daily inspiration by TheCostumeHunt.com")
