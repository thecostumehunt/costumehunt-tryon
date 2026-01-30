import streamlit as st
import requests
import os
import time
import hashlib
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
# DEVICE TOKEN
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
        if r.status_code == 200 and "device_token" in r.json():
            st.session_state.device_token = r.json()["device_token"]
            return r.json()["device_token"]
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

    st.warning("🔄 Running in anonymous mode")
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
if st.sidebar.checkbox("🛠 Debug Info"):
    st.sidebar.write("Device:", st.session_state.device_token)
    st.sidebar.write("Fingerprint:", FINGERPRINT)

# ----------------------------------
# PAYMENT SUCCESS
# ----------------------------------
if query_params.get("checkout") == "success":
    st.success("🎉 Payment successful! Credits added.")
    st.rerun()

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

credits_data = get_credits()
if credits_data:
    st.info(f"💳 Credits left: {credits_data['credits']}")

# ----------------------------------
# SHOW LAST RESULT
# ----------------------------------
if "last_image" in st.session_state:
    st.subheader("🖼 Your last try-on result")
    st.image(st.session_state.last_image, use_container_width=True)

# ----------------------------------
# USER INPUTS
# ----------------------------------
st.markdown("---")
st.subheader("1. Upload your photo")

user_image = st.file_uploader(
    "Upload a clear, full-body photo",
    type=["jpg", "jpeg", "png", "webp"]
)

st.subheader("2. Outfit image")

cloth_url = st.query_params.get("cloth", "")
if cloth_url:
    st.image(cloth_url, caption="Selected outfit", width=260)
else:
    cloth_url = st.text_input(
        "Paste outfit image URL",
        placeholder="https://example.com/outfit.jpg"
    )

# ----------------------------------
# FAL HELPERS
# ----------------------------------
def upload_to_fal(image_bytes):
    headers = {"Authorization": f"Key {FAL_KEY}"}
    files = {"file": ("image.png", image_bytes, "image/png")}

    r = requests.post(
        "https://fal.run/storage/upload",
        headers=headers,
        files=files,
        timeout=30
    )
    r.raise_for_status()
    return r.json()["url"]

def remove_background(image_bytes):
    if not FAL_KEY:
        st.error("❌ FAL_KEY missing")
        return None

    try:
        image_url = upload_to_fal(image_bytes)

        headers = {
            "Authorization": f"Key {FAL_KEY}",
            "Content-Type": "application/json"
        }

        start = requests.post(
            "https://fal.run/fal-ai/imageutils/rembg/subscribe",
            headers=headers,
            json={"input": {"image_url": image_url}},
            timeout=30
        )
        start.raise_for_status()

        request_id = start.json()["request_id"]
        status_url = f"https://fal.run/fal-ai/imageutils/rembg/requests/{request_id}"

        for _ in range(60):
            time.sleep(2)
            poll = requests.get(status_url, headers=headers, timeout=15)
            poll.raise_for_status()
            data = poll.json()

            if data["status"] == "COMPLETED":
                output_url = data["response"]["image"]["url"]
                final = requests.get(output_url, timeout=30)
                final.raise_for_status()
                return final.content

            if data["status"] == "FAILED":
                raise RuntimeError("Background removal failed")

        raise TimeoutError("Background removal timed out")

    except Exception as e:
        st.error(f"❌ Background removal error: {e}")
        return None

# ----------------------------------
# TRY-ON
# ----------------------------------
if "last_try_time" not in st.session_state:
    st.session_state.last_try_time = 0

cooldown = time.time() - st.session_state.last_try_time < 20

st.markdown("---")
generate_btn = st.button("✨ Generate Try-On", disabled=cooldown, use_container_width=True)

if generate_btn:
    if not user_image:
        st.error("Upload your photo")
        st.stop()

    if not cloth_url:
        st.error("Provide outfit image URL")
        st.stop()

    if credits_data and credits_data["credits"] < 1:
        st.error("No credits remaining")
        st.stop()

    st.session_state.last_try_time = time.time()

    with st.spinner("🧹 Removing background..."):
        clean_bytes = remove_background(user_image.getvalue())

    if not clean_bytes:
        st.stop()

    with st.spinner("👗 Generating try-on..."):
        r = requests.post(
            f"{BACKEND_URL}/tryon",
            headers=api_headers(),
            params={"garment_url": cloth_url},
            files={
                "person_image": ("person.png", clean_bytes, "image/png")
            },
            timeout=300
        )

    if r.status_code == 200:
        data = r.json()
        if data.get("image_url"):
            st.session_state.last_image = data["image_url"]
            st.success("🎉 Try-on generated!")
            st.rerun()
        else:
            st.error("No image returned")
    else:
        st.error(f"Backend error {r.status_code}")
        st.code(r.text)

# ----------------------------------
# FOOTER
# ----------------------------------
st.markdown("---")
st.markdown("🔒 Photos deleted after processing • 🩷 https://thecostumehunt.com")
