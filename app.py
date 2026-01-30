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

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "https://tryon-backend-5wf1.onrender.com"
)

# ----------------------------------
# PAGE HEADER
# ----------------------------------
st.title("👗 Try This Outfit On Yourself")
st.write("Upload your full-body photo and preview how a full outfit looks on you.")
st.caption("Powered by TheCostumeHunt.com • Photos are processed temporarily and deleted.")

# ----------------------------------
# 🔑 DEVICE TOKEN (SINGLE SOURCE OF TRUTH)
# ----------------------------------
query_params = st.query_params


def get_device_token():
    # 1️⃣ URL token
    if "device_token" in query_params:
        return query_params["device_token"]

    # 2️⃣ Session token
    if "device_token" in st.session_state:
        return st.session_state.device_token

    # 3️⃣ Force backend to create device
    r = requests.get(f"{BACKEND_URL}/device/init", timeout=10)
    r.raise_for_status()
    data = r.json()

    token = data.get("device_token")
    if not token:
        # THIS SHOULD NEVER HAPPEN WITH YOUR BACKEND
        raise RuntimeError("Backend did not issue device_token")

    # persist everywhere
    st.session_state.device_token = token
    st.query_params.clear()
    st.query_params["device_token"] = token

    return token


try:
    device_token = get_device_token()
except Exception as e:
    st.error("❌ Device initialization failed")
    st.code(str(e))
    st.stop()


def api_headers():
    return {
        "Authorization": f"Bearer {device_token}",
        "Content-Type": "application/json",
    }

# ----------------------------------
# PAYMENT SUCCESS MESSAGE
# ----------------------------------
if query_params.get("checkout") == "success":
    st.success("🎉 Payment successful! Credits added.")

# ----------------------------------
# FETCH CREDITS
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
    st.error("❌ Could not fetch credits")
    st.code(str(e))

if credits_data:
    st.info(f"💳 Credits left: {credits_data['credits']}")

# ----------------------------------
# FREE UNLOCK
# ----------------------------------
if credits_data and credits_data["credits"] == 0 and not credits_data["free_used"]:
    st.subheader("🎁 Get your free try")
    email = st.text_input("Enter your email")

    if st.button("Unlock free try"):
        r = requests.post(
            f"{BACKEND_URL}/free/unlock",
            headers=api_headers(),
            json={"email": email},
            timeout=10
        )
        if r.status_code == 200:
            st.success("✅ Free try unlocked")
            st.rerun()
        else:
            st.error("❌ Unlock failed")
            st.code(r.text)

# ----------------------------------
# PAYMENT
# ----------------------------------
def create_checkout(pack: int):
    r = requests.post(
        f"{BACKEND_URL}/lemon/create-link?pack={pack}",
        headers=api_headers(),
        timeout=20
    )
    if r.status_code == 200:
        return r.json()["checkout_url"]
    st.error("❌ Checkout error")
    st.code(r.text)
    return None


if credits_data and credits_data["credits"] == 0:
    st.markdown("---")
    st.subheader("✨ Buy Credits")

    if st.button("💳 Buy 5 credits ($2)"):
        link = create_checkout(5)
        if link:
            st.link_button("Continue to checkout", link)

# ----------------------------------
# TRY-ON
# ----------------------------------
st.subheader("Upload photo")
user_image = st.file_uploader("Photo", type=["jpg", "png", "jpeg", "webp"])
cloth_url = st.text_input("Outfit image URL")

if st.button("✨ Try it on"):
    if not user_image or not cloth_url:
        st.warning("Missing image")
        st.stop()

    if credits_data["credits"] < 1:
        st.warning("No credits")
        st.stop()

    with st.spinner("Generating..."):
        r = requests.post(
            f"{BACKEND_URL}/tryon",
            headers={"Authorization": f"Bearer {device_token}"},
            files={"person_image": user_image.getvalue()},
            params={"garment_url": cloth_url},
            timeout=300
        )

        if r.status_code == 200:
            st.image(r.json()["image_url"])
        else:
            st.error("Try-on failed")
            st.code(r.text)

# ----------------------------------
# FOOTER
# ----------------------------------
st.markdown("---")
st.write("🩷 TheCostumeHunt.com")
