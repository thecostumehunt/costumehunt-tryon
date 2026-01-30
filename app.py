import streamlit as st
import requests
import os
import time
import hashlib
import io
from PIL import Image
import fal_client  # pip install fal-client

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

# ⚠️ ADD YOUR FAL.AI KEY
FAL_API_KEY = st.secrets.get("FAL_API_KEY", os.getenv("FAL_API_KEY"))
if not FAL_API_KEY:
    st.error("❌ FAL_API_KEY not found in secrets! Add it to Streamlit secrets.")
    st.stop()

fal_client.api_key = FAL_API_KEY

# Generate stable browser fingerprint
FINGERPRINT = hashlib.sha256(f"{BACKEND_URL}".encode()).hexdigest()

# ----------------------------------
# PAGE HEADER
# ----------------------------------
st.title("👗 Try This Outfit On Yourself")
st.write("Upload your full-body photo → **Auto-remove background** → Preview outfit!")
st.caption("Powered by TheCostumeHunt.com + FAL.ai • Photos deleted after use")

# ----------------------------------
# 🔑 DEVICE TOKEN — ROBUST
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
        r.raise_for_status()
        data = r.json()
        if "device_token" in data:
            token = data["device_token"]
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
        r.raise_for_status()
        data = r.json()
        token = data.get("device_token")
        if token:
            st.query_params.clear()
            st.query_params["device_token"] = token
            st.session_state.device_token = token
            return token
    except:
        pass

    st.warning("🔄 Anonymous mode")
    return None

try:
    st.session_state.device_token = init_device_safely()
except:
    st.error("❌ Device init failed")
    st.stop()

def api_headers():
    headers = {}
    if st.session_state.device_token:
        headers["Authorization"] = f"Bearer {st.session_state.device_token}"
    headers["X-Fingerprint"] = FINGERPRINT
    return headers

# ----------------------------------
# 🖼️ BACKGROUND REMOVAL FUNCTION
# ----------------------------------
@st.cache_data(ttl=300)
def remove_background(image_bytes):
    """Remove background using FAL.ai and return transparent PNG bytes"""
    try:
        with fal_client.Queue("fal-ai/imageutils/rembg") as queue:
            result = queue.submit(
                input={
                    "image_url": None,  # We use raw input instead
                    "image_base64": None
                },
                input_type="bytes",  # Raw bytes input
                input_bytes=image_bytes
            )
            return result.output_bytes
    except Exception as e:
        st.error(f"❌ Background removal failed: {str(e)[:100]}")
        return image_bytes  # Return original if failed

# Alternative sync version (slower but simpler)
def remove_background_sync(image_bytes):
    """Sync version using fal_client directly"""
    try:
        result = fal_client.run("fal-ai/imageutils/rembg", {
            "image_url": None,
            "image": image_bytes
        })
        # Convert result to bytes if needed
        if isinstance(result, Image.Image):
            img_byte_arr = io.BytesIO()
            result.save(img_byte_arr, format='PNG')
            return img_byte_arr.getvalue()
        return result
    except Exception as e:
        st.error(f"❌ Background removal failed: {str(e)[:100]}")
        return image_bytes

# ----------------------------------
# FETCH CREDITS
# ----------------------------------
@st.cache_data(ttl=30)
def get_credits():
    try:
        r = requests.get(f"{BACKEND_URL}/credits", headers=api_headers(), timeout=10)
        r.raise_for_status()
        return r.json()
    except:
        return None

credits_data = get_credits()
if credits_data:
    st.info(f"💳 Credits: {credits_data['credits']}")

# ----------------------------------
# SHOW LAST RESULT
# ----------------------------------
if "last_image" in st.session_state:
    st.subheader("🖼️ Last Try-On Result")
    st.image(st.session_state.last_image, use_container_width=True)
    
    try:
        img_bytes = requests.get(st.session_state.last_image, timeout=10).content
        st.download_button("⬇️ Download", img_bytes, "tryon.png", "image/png")
    except:
        pass

# ----------------------------------
# FREE/PAYMENT UI (unchanged)
# ----------------------------------
if credits_data and credits_data["credits"] == 0 and not credits_data.get("free_used", True):
    st.subheader("🎁 Free Try")
    email = st.text_input("Email:")
    if st.button("Unlock Free Try"):
        r = requests.post(f"{BACKEND_URL}/free/unlock", 
                         headers={**api_headers(), "Content-Type": "application/json"},
                         json={"email": email}, timeout=10)
        if r.status_code == 200:
            st.success("✅ Unlocked!")
            st.rerun()

if credits_data and credits_data["credits"] == 0:
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1: 
        if st.button("💳 5 credits ($2)"): st.info("Buy credits first")
    with c2: 
        if st.button("💳 15 credits ($5)"): st.info("Buy credits first") 
    with c3: 
        if st.button("💳 100 credits ($20)"): st.info("Buy credits first")

# ----------------------------------
# 🔥 MAIN UI WITH BACKGROUND REMOVAL
# ----------------------------------
st.markdown("---")
st.subheader("1️⃣ Upload Your Photo")

# File uploader
user_image = st.file_uploader(
    "Upload full-body photo", 
    type=["jpg", "jpeg", "png", "webp"],
    help="Clear, front-facing, full body"
)

# PREVIEW & AUTO BACKGROUND REMOVAL
if user_image:
    # Show original
    col1, col2 = st.columns(2)
    
    with col1:
        st.image(user_image, caption="📸 Original", width=250)
    
    # AUTO REMOVE BACKGROUND
    with col2:
        if "processed_image" not in st.session_state or st.session_state.get("current_image_hash") != hashlib.md5(user_image.getvalue()).hexdigest():
            with st.spinner("✨ Removing background..."):
                processed_bytes = remove_background_sync(user_image.getvalue())
                st.session_state.processed_image = processed_bytes
                st.session_state.current_image_hash = hashlib.md5(user_image.getvalue()).hexdigest()
        
        st.image(st.session_state.processed_image, caption="🧹 Background Removed", width=250)
        
        # Show download for processed image
        st.download_button(
            "💾 Download Clean Photo", 
            st.session_state.processed_image,
            "clean-person.png",
            "image/png"
        )

st.subheader("2️⃣ Outfit Image")
cloth_url = st.query_params.get("cloth", "")
if cloth_url:
    try:
        st.image(cloth_url, caption="👗 Outfit", width=260)
    except:
        cloth_url = ""
        st.warning("Invalid URL")
else:
    cloth_url = st.text_input("Outfit image URL", placeholder="https://...")

# ----------------------------------
# 🎯 GENERATE TRY-ON BUTTON
# ----------------------------------
if "last_try_time" not in st.session_state:
    st.session_state.last_try_time = 0

now = time.time()
cooldown = now - st.session_state.last_try_time < 25

col1, col2 = st.columns([4,1])
with col1:
    if st.button("🚀 Generate Try-On", use_container_width=True, disabled=cooldown):
        pass
with col2:
    st.info(f"⏳ {max(0, int(25-(now-st.session_state.last_try_time)))}s")

if st.button("🚀 Generate Try-On", disabled=cooldown, use_container_width=True):
    if not user_image:
        st.error("👆 Upload photo first")
        st.stop()
    
    if not cloth_url.strip():
        st.error("👆 Enter outfit URL")
        st.stop()
    
    if credits_data and credits_data["credits"] < 1:
        st.error("💳 Need credits!")
        st.stop()

    st.session_state.last_try_time = now
    
    with st.spinner("🎨 Processing (~45s)..."):
        try:
            # Use PROCESSED IMAGE with transparent background
            files = {"person_image": st.session_state.processed_image}
            params = {"garment_url": cloth_url.strip()}

            r = requests.post(
                f"{BACKEND_URL}/tryon",
                headers=api_headers(),
                params=params,
                files=files,
                timeout=300
            )

            if r.status_code == 200:
                data = r.json()
                st.session_state.last_image = data["image_url"]
                st.success("🎉 Ready!")
                st.rerun()
            else:
                st.error(f"❌ Error {r.status_code}")
                st.code(r.text[:500])
                
        except Exception as e:
            st.error(f"❌ Failed: {str(e)}")

# ----------------------------------
# FOOTER
# ----------------------------------
st.markdown("---")
st.markdown("🔒 Photos auto-deleted • ✨ Powered by FAL.ai + TheCostumeHunt")
