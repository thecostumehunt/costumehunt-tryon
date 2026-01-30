import streamlit as st
import requests
import os
import time

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

# ----------------------------------
# PAGE HEADER
# ----------------------------------
st.title("👗 Try This Outfit On Yourself")
st.write("Upload your full-body photo and preview how a full outfit looks on you.")
st.caption("Powered by TheCostumeHunt.com • Photos are processed temporarily and deleted.")

# ----------------------------------
# 🔑 DEVICE TOKEN — SINGLE SOURCE OF TRUTH
# ----------------------------------
query_params = st.query_params


def get_or_create_device_token():
    # 1️⃣ Token in URL (highest priority)
    if "device_token" in query_params:
        return query_params["device_token"]

    # 2️⃣ Token already in session
    if "device_token" in st.session_state:
        return st.session_state.device_token

    # 3️⃣ Ask backend to initialize device
    r = requests.get(f"{BACKEND_URL}/device/init", timeout=10)
    r.raise_for_status()
    data = r.json()

    # Backend only returns device_token when a NEW device is created
    token = data.get("device_token")

    if token:
        # persist token in URL for refresh & payment return
        st.query_params.clear()
        st.query_params["device_token"] = token
        return token

    # If we reach here, backend recognized device
    # but frontend had no token → this is a hard error
    raise RuntimeError(
        "Backend recognized device but no device_token present in frontend"
    )


# ---- initialize device ----
try:
    st.session_state.device_token = get_or_create_device_token()
except Exception as e:
    st.error("❌ Device initialization failed")
    st.code(str(e))
    st.stop()


def api_headers():
    return {
        "Authorization": f"Bearer {st.session_state.device_token}",
        "Content-Type": "application/json",
    }

# ----------------------------------
# PAYMENT SUCCESS MESSAGE (UI ONLY)
# ----------------------------------
if query_params.get("checkout") == "success":
    st.success("🎉 Payment successful! Credits have been added.")

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
        try:
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
        except Exception as e:
            st.error("❌ Request failed")
            st.code(str(e))

# ----------------------------------
# PAYMENT HELPER
# ----------------------------------
def create_checkout(pack: int):
    try:
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

    except Exception as e:
        st.error("❌ Connection error")
        st.code(str(e))
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
# CLIENT-SIDE COOLDOWN (UX ONLY)
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
            headers={"Authorization": api_headers()["Authorization"]},
            params=params,
            files=files,
            timeout=300
        )

        if r.status_code == 200:
            data = r.json()
            st.session_state.last_image = data["image_url"]
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
