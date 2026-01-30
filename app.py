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

# FAL Key (add to Streamlit secrets or environment)
FAL_KEY = st.secrets.get("FAL_KEY", os.getenv("FAL_KEY"))

# Generate stable browser fingerprint
FINGERPRINT = hashlib.sha256(f"{BACKEND_URL}".encode()).hexdigest()

# ----------------------------------
# PAGE HEADER
# ----------------------------------
st.title("👗 Try This Outfit On Yourself")
st.write("Upload your full-body photo and preview how a full outfit looks on you.")
st.caption("Powered by TheCostumeHunt.com • Photos are processed temporarily and deleted.")

# ----------------------------------
# 🔑 DEVICE TOKEN — ROBUST & BACKWARDS COMPATIBLE
# ----------------------------------
query_params = st.query_params

def init_device_safely():
    # 1️⃣ token already in URL (preserve old flow)
    if "device_token" in query_params:
        token = query_params["device_token"][0]
        st.session_state.device_token = token
        return token

    # 2️⃣ token already in session
    if "device_token" in st.session_state:
        return st.session_state.device_token

    # 3️⃣ try old simple flow first (backwards compatible)
    try:
        r = requests.get(f"{BACKEND_URL}/device/init", timeout=10)
        r.raise_for_status()
        data = r.json()
        if "device_token" in data:
            token = data["device_token"]
            st.session_state.device_token = token
            return token
    except:
        pass  # fall through to fingerprint flow

    # 4️⃣ new fingerprint flow
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
    except Exception as e:
        pass

    # 5️⃣ graceful fallback - let backend handle recognition
    st.warning("🔄 Using anonymous mode - some features may be limited")
    return None

try:
    st.session_state.device_token = init_device_safely()
except Exception as e:
    st.error(f"❌ Device initialization failed: {str(e)[:100]}")
    st.stop()

def api_headers(token=None):
    headers = {}
    if token or st.session_state.device_token:
        headers["Authorization"] = f"Bearer {token or st.session_state.device_token}"
    headers["X-Fingerprint"] = FINGERPRINT
    return headers

# DEBUG INFO (remove after testing)
if st.sidebar.checkbox("🛠️ Debug Info"):
    st.sidebar.write(f"🔑 Device Token: {st.session_state.device_token[:10]}..." if st.session_state.device_token else "None")
    st.sidebar.write(f"🖐️ Fingerprint: {FINGERPRINT}")

# ----------------------------------
# PAYMENT SUCCESS MESSAGE
# ----------------------------------
if query_params.get("checkout") == "success":
    st.success("🎉 Payment successful! Credits added.")
    st.rerun()

# ----------------------------------
# FETCH CREDITS (SOURCE OF TRUTH)
# ----------------------------------
@st.cache_data(ttl=30)
def get_credits():
    try:
        r = requests.get(
            f"{BACKEND_URL}/credits",
            headers=api_headers(),
            timeout=10
        )
        r.raise_for_status()
        return r.json()
    except:
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

    try:
        img_bytes = requests.get(st.session_state.last_image, timeout=10).content
        st.download_button(
            "⬇️ Download image",
            data=img_bytes,
            file_name="tryon.png",
            mime="image/png"
        )
    except:
        st.info("💾 Download unavailable")

# ----------------------------------
# FREE UNLOCK (BACKEND ENFORCED)
# ----------------------------------
if credits_data and credits_data["credits"] == 0 and not credits_data.get("free_used", True):
    st.subheader("🎁 Get your free try")
    email = st.text_input("Enter your email to unlock your free try")

    if st.button("Unlock free try", use_container_width=True):
        try:
            r = requests.post(
                f"{BACKEND_URL}/free/unlock",
                headers={**api_headers(), "Content-Type": "application/json"},
                json={"email": email},
                timeout=10
            )
            if r.status_code == 200:
                st.success("✅ Free try unlocked!")
                st.rerun()
            else:
                st.error(f"❌ Unlock failed: {r.text[:100]}")
        except Exception as e:
            st.error(f"❌ Network error: {str(e)}")

# ----------------------------------
# BUY CREDITS UI (HYBRID APPROACH)
# ----------------------------------
if credits_data and credits_data["credits"] == 0:
    st.markdown("---")
    st.subheader("✨ Buy Credits")
    st.write("Secure checkout via LemonSqueezy")

    c1, c2, c3 = st.columns(3)

    @st.cache_data(ttl=60)
    def create_checkout(pack: int):
        try:
            r = requests.post(
                f"{BACKEND_URL}/lemon/create-link?pack={pack}",
                headers=api_headers(),
                timeout=20
            )
            if r.status_code == 200:
                return r.json().get("checkout_url") or r.json().get("url")
            return None
        except:
            return None

    with c1:
        if st.button("💳 5 credits ($2)", use_container_width=True):
            link = create_checkout(5)
            if link:
                st.link_button("👉 Checkout →", link, type="primary", use_container_width=True)

    with c2:
        if st.button("💳 15 credits ($5)", use_container_width=True):
            link = create_checkout(15)
            if link:
                st.link_button("👉 Checkout →", link, type="primary", use_container_width=True)

    with c3:
        if st.button("💳 100 credits ($20)", use_container_width=True):
            link = create_checkout(100)
            if link:
                st.link_button("👉 Checkout →", link, type="primary", use_container_width=True)

# ----------------------------------
# USER INPUTS
# ----------------------------------
st.markdown("---")
st.subheader("1. Upload your photo")
user_image = st.file_uploader(
    "Upload a clear, full-body photo (JPG/PNG)",
    type=["jpg", "jpeg", "png", "webp"],
    help="Must show full body, front-facing, good lighting"
)

st.subheader("2. Outfit image")
cloth_url = st.query_params.get("cloth", "")

if cloth_url:
    try:
        st.image(cloth_url, caption="Selected outfit", width=260)
    except:
        st.warning("❌ Invalid outfit image URL")
        cloth_url = ""
else:
    cloth_url = st.text_input(
        "Paste outfit image URL", 
        placeholder="https://example.com/outfit.jpg",
        help="Direct link to clothing image (full outfit preferred)"
    )

def remove_background(image_bytes):
    """
    Correct + supported FAL usage:
    - image must be a public URL
    """
    if not FAL_KEY:
        st.error("❌ FAL_KEY not configured")
        return None

    try:
        # 1️⃣ Upload image to YOUR backend (temporary storage)
        upload = requests.post(
            f"{BACKEND_URL}/upload/temp-image",
            files={"file": ("person.png", image_bytes, "image/png")},
            timeout=30
        )
        upload.raise_for_status()
        image_url = upload.json()["url"]  # must be publicly accessible

        # 2️⃣ Call FAL with image_url (THIS IS WHAT THEY SUPPORT)
        headers = {
            "Authorization": f"Key {FAL_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "input": {
                "image_url": image_url
            }
        }

        r = requests.post(
            "https://fal.run/fal-ai/imageutils/rembg",
            json=payload,
            headers=headers,
            timeout=60
        )
        r.raise_for_status()

        # 3️⃣ Result is immediate for rembg
        result = r.json()
        output_url = result["image"]["url"]

        # 4️⃣ Download final image
        final = requests.get(output_url, timeout=30)
        final.raise_for_status()
        return final.content

    except Exception as e:
        st.error(f"❌ Background removal failed: {str(e)}")
        return None


# ----------------------------------
# CLIENT-SIDE COOLDOWN & TRY-ON
# ----------------------------------
if "last_try_time" not in st.session_state:
    st.session_state.last_try_time = 0

now = time.time()
cooldown = now - st.session_state.last_try_time < 20

col1, col2 = st.columns([4, 1])
with col1:
    generate_btn = st.button("✨ Generate Try-On", use_container_width=True, disabled=cooldown)
with col2:
    st.info(f"⏳ {int(20-(now-st.session_state.last_try_time)) if cooldown else 'Ready'}s")

st.subheader("3. Processing...")

if generate_btn:
    # VALIDATION
    if not user_image:
        st.error("👆 Please upload your photo first")
        st.stop()
    
    if not cloth_url or cloth_url.strip() == "":
        st.error("👆 Please provide outfit image URL")
        st.stop()
    
    if credits_data and credits_data["credits"] < 1:
        st.error("💳 No credits remaining. Buy credits above!")
        st.stop()

    # UPDATE COOLDOWN
    st.session_state.last_try_time = now

    with st.spinner("🎨 Creating virtual try-on (~30-60s)..."):
        try:
            # STEP 1: Remove background
            st.info("🧹 Step 1/2: Removing background...")
            original_image_bytes = user_image.getvalue()
            clean_image_bytes = remove_background(original_image_bytes)
            
            if not clean_image_bytes:
                st.error("❌ Background removal failed. Cannot proceed.")
                st.stop()

            # STEP 2: Send cleaned image to backend
            st.info("👗 Step 2/2: Generating try-on...")
            files = {"person_image": ("clean_image.png", clean_image_bytes, "image/png")}
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
                image_url = data.get("image_url")
                
                if image_url:
                    st.session_state.last_image = image_url
                    st.success("🎉 Try-on generated successfully!")
                    st.rerun()
                else:
                    st.error("❌ No image URL in response")
                    st.code(r.text[:500])
            else:
                st.error(f"❌ Backend error {r.status_code}")
                st.code(r.text[:1000])
                
        except requests.exceptions.Timeout:
            st.error("⏰ Request timed out (backend busy)")
        except Exception as e:
            st.error(f"❌ Network error: {str(e)}")

# ----------------------------------
# FOOTER
# ----------------------------------
st.markdown("---")
st.markdown("🔒 Photos deleted after processing • 🩷 [TheCostumeHunt.com](https://thecostumehunt.com)")
