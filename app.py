import streamlit as st
import requests
import os
import time
import hashlib
import io
from PIL import Image

# ----------------------------------
# CONFIG
# ----------------------------------
st.set_page_config(
    page_title="The Costume Hunt – Try On",
    layout="centered"
)

BACKEND_URL = st.secrets.get(
    "BACKEND_URL",
    os.getenv("BACKEND_URL", "https://tryon-backend-5wf1.onrender.com")
)

FAL_KEY = st.secrets.get("FAL_KEY", os.getenv("FAL_KEY"))
FINGERPRINT = hashlib.sha256(f"{BACKEND_URL}".encode()).hexdigest()

# ----------------------------------
# PAGE HEADER
# ----------------------------------
st.title("👗 Try This Outfit On Yourself")
st.write("Upload your full-body photo and preview how a full outfit looks on you.")
st.caption("Powered by TheCostumeHunt.com • Photos are processed temporarily and deleted.")

# ----------------------------------
# 🔑 DEVICE TOKEN
# ----------------------------------
query_params = st.query_params

def init_device_safely():
    if "device_token" in query_params:
        token = query_params["device_token"][0]
        st.session_state.device_token = token
        return token

    if "device_token" in st.session_state:
        return st.session_state.device_token

    try:
        r = requests.get(f"{BACKEND_URL}/device/init", timeout=10)
        if r.status_code == 200:
            token = r.json().get("device_token")
            if token:
                st.session_state.device_token = token
                return token
    except:
        pass

    try:
        r = requests.get(
            f"{BACKEND_URL}/device/init",
            headers={"X-Fingerprint": FINGERPRINT},
            timeout=10
        )
        if r.status_code == 200:
            token = r.json().get("device_token")
            if token:
                st.query_params.clear()
                st.query_params["device_token"] = token
                st.session_state.device_token = token
                return token
    except:
        pass

    st.warning("⚠️ Anonymous mode – some features may be limited")
    return None

st.session_state.device_token = init_device_safely()

def api_headers():
    headers = {"X-Fingerprint": FINGERPRINT}
    if st.session_state.device_token:
        headers["Authorization"] = f"Bearer {st.session_state.device_token}"
    return headers

# ----------------------------------
# DEBUG
# ----------------------------------
if st.sidebar.checkbox("🛠 Debug"):
    st.sidebar.write("Device:", st.session_state.device_token)
    st.sidebar.write("Fingerprint:", FINGERPRINT)

# ----------------------------------
# FETCH CREDITS
# ----------------------------------
@st.cache_data(ttl=30)
def get_credits():
    try:
        r = requests.get(f"{BACKEND_URL}/credits", headers=api_headers(), timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

credits = get_credits()
if credits:
    st.info(f"💳 Credits left: {credits['credits']}")

# ----------------------------------
# SHOW LAST RESULT
# ----------------------------------
if "last_image" in st.session_state:
    st.subheader("🖼 Your last try-on")
    st.image(st.session_state.last_image, use_container_width=True)

# ----------------------------------
# USER INPUTS
# ----------------------------------
st.markdown("---")
st.subheader("1️⃣ Upload your photo")

user_image = st.file_uploader(
    "Full-body photo (JPG / PNG / WEBP)",
    type=["jpg", "jpeg", "png", "webp"]
)

st.subheader("2️⃣ Outfit image")
cloth_url = st.query_params.get("cloth", "")

if cloth_url:
    st.image(cloth_url, width=260)
else:
    cloth_url = st.text_input("Paste outfit image URL")

# ----------------------------------
# ✅ OFFICIAL FAL BACKGROUND REMOVAL
# ----------------------------------
def remove_background(image_bytes: bytes) -> bytes:
    """
    Background removal using OFFICIAL FAL rembg model.
    Independent and robust.
    """

    if not FAL_KEY:
        st.warning("⚠️ No FAL_KEY – skipping background removal")
        return image_bytes

    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        files = {
            "image": ("input.png", buffer, "image/png")
        }

        headers = {
            "Authorization": f"Key {FAL_KEY}"
        }

        st.info("🧹 Removing background...")

        r = requests.post(
            "https://fal.run/fal-ai/imageutils/rembg",
            headers=headers,
            files=files,
            timeout=120
        )

        r.raise_for_status()
        data = r.json()

        output_url = data["image"]["url"]
        result_img = requests.get(output_url, timeout=30)
        result_img.raise_for_status()

        st.success("✅ Background removed")
        return result_img.content

    except Exception as e:
        st.warning(f"⚠️ Background removal failed – using original")
        return image_bytes

# ----------------------------------
# COOLDOWN
# ----------------------------------
if "last_try_time" not in st.session_state:
    st.session_state.last_try_time = 0

cooldown = time.time() - st.session_state.last_try_time < 20

col1, col2 = st.columns([4, 1])
with col1:
    generate = st.button("✨ Generate Try-On", disabled=cooldown, use_container_width=True)
with col2:
    st.info("⏳ Wait" if cooldown else "Ready")

# ----------------------------------
# TRY-ON PIPELINE
# ----------------------------------
if generate:
    if not user_image:
        st.error("Please upload your photo")
        st.stop()

    if not cloth_url:
        st.error("Please provide outfit image URL")
        st.stop()

    if credits and credits["credits"] < 1:
        st.error("No credits remaining")
        st.stop()

    st.session_state.last_try_time = time.time()

    with st.spinner("🎨 Processing (~30–60s)..."):
        try:
            # STEP 1: Background removal
            processed_image = remove_background(user_image.getvalue())

            # Optional preview (comment out in production)
            # st.image(processed_image, caption="Processed image", width=300)

            # STEP 2: Try-on
            files = {
                "person_image": ("person.png", processed_image, "image/png")
            }
            params = {
                "garment_url": cloth_url.strip()
            }

            r = requests.post(
                f"{BACKEND_URL}/tryon",
                headers=api_headers(),
                params=params,
                files=files,
                timeout=300
            )

            if r.status_code == 200:
                image_url = r.json().get("image_url")
                if image_url:
                    st.session_state.last_image = image_url
                    st.success("🎉 Try-on generated!")
                    st.rerun()
                else:
                    st.error("No image URL returned")
            else:
                st.error(f"Backend error {r.status_code}")
                st.code(r.text[:500])

        except requests.exceptions.Timeout:
            st.error("⏰ Request timed out")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

# ----------------------------------
# FOOTER
# ----------------------------------
st.markdown("---")
st.markdown("🔒 Photos deleted after processing • 🩷 https://thecostumehunt.com")
