import streamlit as st
import tempfile
import requests
import os
from PIL import Image
import replicate

# ----------------------------------
# PAGE SETUP
# ----------------------------------
st.set_page_config(page_title="The Costume Hunt – Try On", layout="centered")

st.title("👗 Try This Outfit On Yourself")
st.write("Upload your full-body photo and preview how daily outfits look on you.")
st.caption("Powered by TheCostumeHunt.com • Photos are processed temporarily and not stored.")

# ----------------------------------
# API KEY
# ----------------------------------
os.environ["REPLICATE_API_TOKEN"] = st.secrets["REPLICATE_API_TOKEN"]

# ----------------------------------
# SESSION CONTROL (1 FREE TRY)
# ----------------------------------
if "free_used" not in st.session_state:
    st.session_state.free_used = False

# ----------------------------------
# GET OUTFIT FROM BLOG LINK
# ----------------------------------
query_params = st.query_params
cloth_url = query_params.get("cloth", None)

# ----------------------------------
# UI INPUTS
# ----------------------------------
st.subheader("1. Upload your photo")
user_image = st.file_uploader(
    "Upload a clear, full-body photo (standing, good light, simple background works best)",
    type=["jpg", "jpeg", "png", "webp"]
)

st.subheader("2. Outfit image")

if cloth_url:
    st.image(cloth_url, caption="Outfit selected from The Costume Hunt", width=250)
else:
    cloth_url = st.text_input("Paste outfit image URL from thecostumehunt.com")

st.subheader("3. Generate try-on")

# ----------------------------------
# HELPER FUNCTIONS
# ----------------------------------
def save_temp_image(file):
    img = Image.open(file).convert("RGB")
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(temp.name)
    return temp.name

def download_image(url):
    r = requests.get(url, stream=True, timeout=20)
    r.raise_for_status()
    img = Image.open(r.raw).convert("RGB")
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(temp.name)
    return temp.name

# ----------------------------------
# TRY-ON ACTION
# ----------------------------------
if st.button("✨ Try it on"):
    if st.session_state.free_used:
        st.warning("You’ve already used your free try-on. Unlimited daily try-ons coming soon.")
        st.stop()

    if not user_image or not cloth_url:
        st.warning("Please upload your photo and provide an outfit image.")
        st.stop()

    with st.spinner("Creating your try-on… please wait 10–30 seconds"):
        person_path = None
        cloth_path = None

        try:
            person_path = save_temp_image(user_image)
            cloth_path = download_image(cloth_url)

            output = replicate.run(
                "yisol/virtual-try-on",
                input={
                    "person_image": open(person_path, "rb"),
                    "cloth_image": open(cloth_path, "rb")
                }
            )

            st.image(output[0], caption="Your try-on result", use_container_width=True)
            st.success("🎉 Your try-on is ready!")
            st.session_state.free_used = True

        except Exception as e:
            st.error("Something went wrong while generating your try-on. Please try different images.")
            st.code(str(e))

        finally:
            try:
                if person_path and os.path.exists(person_path):
                    os.remove(person_path)
                if cloth_path and os.path.exists(cloth_path):
                    os.remove(cloth_path)
            except:
                pass

# ----------------------------------
# FOOTER / TRUST
# ----------------------------------
st.markdown("---")
st.write("🔒 Photos are processed temporarily and automatically deleted.")
st.write("🩷 Daily-wear fashion inspiration by TheCostumeHunt.com")
