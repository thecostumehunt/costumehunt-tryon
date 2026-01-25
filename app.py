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
# SESSION CONTROL
# ---------------------------
if "free_used" not in st.session_state:
    st.session_state.free_used = False

query_params = st.query_params
cloth_url = query_params.get("cloth", None)

# ---------------------------
# UI
# ---------------------------
st.subheader("1. Upload your photo")
user_image = st.file_uploader(
    "Upload a clear full-body photo (head to feet visible)",
    type=["jpg", "jpeg", "png", "webp"]
)

st.subheader("2. Outfit image (full outfit: top + bottom / dress)")

if cloth_url:
    try:
        st.image(cloth_url, caption="Selected outfit", width=260)
    except:
        cloth_url = None
        st.warning("Could not load image. Paste a direct image URL.")
else:
    cloth_url = st.text_input("Paste outfit image URL")

st.subheader("3. Generate try-on")

# ---------------------------
# HELPERS
# ---------------------------
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

# ---------------------------
# TRY-ON
# ---------------------------
if st.button("✨ Try it on"):
    if st.session_state.free_used:
        st.warning("You've already used your free try-on. More coming soon.")
        st.stop()

    if not user_image or not cloth_url:
        st.warning("Please upload your photo and provide an outfit image.")
        st.stop()

    with st.spinner("Creating your virtual try-on… please wait"):
        person_path = None
        cloth_path = None

        try:
            # Prepare images
            person_path = save_temp_image(user_image)
            cloth_path = download_image(cloth_url)

            # ✅ Upload images to FAL
            person_upload = fal_client.upload_file(person_path)
            cloth_upload = fal_client.upload_file(cloth_path)

            # ✅ Run Kolors Virtual Try-On
            result = fal_client.run(
                "fal-ai/koloa-virtual-tryon",
                arguments={
                    "human_image": person_upload,
                    "garment_image": cloth_upload,
                    "category": "full",   # upper | lower | dress | full
                    "mode": "quality"     # fast | quality
                }
            )

            if "image" not in result or "url" not in result["image"]:
                raise ValueError("Invalid response from FAL API")

            output_url = result["image"]["url"]

            st.image(output_url, caption="Your real virtual try-on", use_column_width=True)
            st.success("🎉 Your try-on is ready!")
            st.session_state.free_used = True

        except Exception as e:
            st.error("🚨 Try-on failed.")
            st.write("Error:", str(e))
            st.text(traceback.format_exc())
            st.info("""
Tips for best results:
• Full-body standing photo  
• Outfit on clean/plain background  
• Avoid collages and screenshots
""")

        finally:
            try:
                if person_path and os.path.exists(person_path):
                    os.remove(person_path)
                if cloth_path and os.path.exists(cloth_path):
                    os.remove(cloth_path)
            except:
                pass

# ---------------------------
# FOOTER
# ---------------------------
st.markdown("---")
st.write("🔒 Photos are processed temporarily and deleted automatically.")
st.write("🩷 Daily-wear inspiration by TheCostumeHunt.com")
