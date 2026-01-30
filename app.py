import streamlit as st
import requests
import os
import time
import hashlib

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

# Generate stable browser fingerprint
FINGERPRINT = hashlib.sha256(f"{BACKEND_URL}".encode()).hexdigest()

# ----------------------------------
# PAGE HEADER
# ----------------------------------
st.title("👗 Try This Outfit On Yourself")
st.write("Upload your full-body photo and preview how a full outfit looks on you.")
st.caption("Powered by TheCostumeHunt.com • Photos are processed temporarily and deleted.")

# ----------------------------------
# 🔑 DEVICE TOKEN — SAFE & DEFENSIVE
# ----------------------------------
query_params = st.query_params

def init_device_safely():
    # 1️⃣ token already in URL
    if "device_token" in query_params:
        return query_params["device_token"]

    # 2️⃣ token already in session
    if "device_token" in st.session_state:
        return st.session_state.device_token

    # 3️⃣ ask backend (with fingerprint)
    r = requests.get(
        f"{BACKEND_URL}/device/init", 
        headers={"X-Fingerprint": FINGERPRINT},
        timeout=10
    )
    r.raise_for_status()
    data = r.json()

    token = data.get("device_token")

    # ✅ if backend returned token → persist it
    if token:
        st.query_params.clear()
        st.query_params["device_token"] = token
        return token

    # ✅ if backend did NOT return token
    # this means backend already recognizes device
    # frontend just continues WITHOUT crashing
    raise RuntimeError(
        "Device exists but no device_token returned. "
        "Please refresh once."
    )

try:
    st.session_state.device_token = init_device_safely()
except Exception as e:
    st.error("❌ Device initialization failed")
    st.code(str(e))
    st.stop()

def api_headers():
    return {
        "Authorization": f"Bearer {st.session_state.device_token}",
        "Content-Type": "application/json",
        "X-Fingerprint": FINGERPRINT  # Always include fingerprint
    }

# ----------------------------------
# PAYMENT SUCCESS MESSAGE (UI ONLY)
# ----------------------------------
if query_params.get("checkout") == "success":
    st.success("🎉 Payment successful! Credits have been added.")
    st.rerun()  # Auto-refresh credits display

# ----------------------------------
# FETCH CREDITS (SOURCE OF TRUTH)
# ----------------------------------
credits_data = None
try:
    r = requests.get(
        f"{BACKEND_URL}/credits",
        headers=api_headers(),
        timeout=10
    )
    r.raise_for_status()
    credits_data = r.json()
except Exception as e:
    st.error("❌ Failed to fetch credits")
    st.code(str(e))

if credits_data:
    st.info(f"💳 Credits left: {credits_data['credits']}")

# ----------------------------------
# SHOW LAST RESULT
# ----------------------------------
if "last_image" in st.session_state:
    st.subheader("🖼 Your last try-on result")
    st.image(st.session_state.last_image, use_container_width=True)

    try:
        img_bytes = requests.get(st.session_state.last_image).content
        st.download_button(
            "⬇️ Download image",
            data=img_bytes,
            file_name="tryon.png",
            mime="image/png"
        )
    except Exception:
        pass

# ----------------------------------
# FREE UNLOCK (BACKEND ENFORCED)
# ----------------------------------
if credits_data and credits_data["credits"] == 0 and not credits_data.get("free_used", True):
    st.subheader("🎁 Get your free try")
    email = st.text_input("Enter your email to unlock your free try")

    if st.button("Unlock free try"):
        r = requests.post(
            f"{BACKEND_URL}/free/unlock",
            headers=api_headers(),
            json={"email": email},
            timeout=10
        )

        if r.status_code == 200:
            st.success("✅ Free try unlocked!")
            st.rerun()
        else:
            st.error("❌ Unlock failed")
            st.code(r.text)

# ----------------------------------
# PAYMENT HELPER
# ----------------------------------
def create_checkout(pack: int):
    r = requests.post(
        f"{BACKEND_URL}/lemon/create-link?pack={pack}",
        headers=api_headers(),
        timeout=20
    )

    if r.status_code == 200:
        return r.json().get("checkout_url")

    st.error("❌ Backend error while creating checkout")
    st.code(r.text)
    return None

# ----------------------------------
# BUY CREDITS UI
# ----------------------------------
if credits_data and credits_data["credits"] == 0:
    st.markdown("---")
    st.subheader("✨ Buy Credits")
    st.write("Secure checkout via LemonSqueezy")

    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("💳 Buy 5 credits ($2)", use_container_width=True):
            link = create_checkout(5)
            if link:
                st.link_button("👉 Continue to checkout", link, type="primary")

    with c2:
        if st.button("💳 Buy 15 credits ($5)", use_container_width=True):
            link = create_checkout(15)
            if link:
                st.link_button("👉 Continue to checkout", link, type="primary")

    with c3:
        if st.button("💳 Buy 100 credits ($20)", use_container_width=True):
            link = create_checkout(100)
            if link:
                st.link_button("👉 Continue to checkout", link, type="primary")

# ----------------------------------
# USER INPUTS
# ----------------------------------
st.subheader("1. Upload your photo")
user_image = st.file_uploader(
    "Upload a clear, full-body photo",
    type=["jpg", "jpeg", "png", "webp"]
)

st.subheader("2. Outfit image")
cloth_url = query_params.get("cloth")

if cloth_url:
    st.image(cloth_url, caption="Selected outfit", width=260)
else:
    cloth_url = st.text_input("Paste outfit image URL")

st.subheader("3. Generate try-on")

# ----------------------------------
# CLIENT-SIDE COOLDOWN
# ----------------------------------
now = time.time()
last_try = st.session_state.get("last_try_time", 0)

if st.button("✨ Try it on", use_container_width=True):

    if now - last_try < 20:
        st.warning("⏳ Please wait a few seconds before trying again.")
        st.stop()

    st.session_state.last_try_time = now

    if not user_image or not cloth_url:
        st.warning("Please upload your photo and provide outfit image.")
        st.stop()

    if not credits_data or credits_data["credits"] < 1:
        st.warning("You need credits to continue.")
        st.stop()

    with st.spinner("🎨 Creating virtual try-on (~30s)..."):
        files = {"person_image": user_image.getvalue()}
        params = {"garment_url": cloth_url}

        r = requests.post(
            f"{BACKEND_URL}/tryon",
            headers=api_headers(),
            params=params,
            files=files,
            timeout=300
        )

        if r.status_code == 200:
            st.session_state.last_image = r.json()["image_url"]
            st.success("🎉 Try-on ready!")
            st.rerun()
        else:
            st.error("❌ Try-on failed")
            st.code(r.text)

# ----------------------------------
# FOOTER
# ----------------------------------
st.markdown("---")
st.write("🔒 Photos deleted after processing")
st.write("🩷 TheCostumeHunt.com")
