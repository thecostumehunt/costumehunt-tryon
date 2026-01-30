import streamlit as st
import requests
import os

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
# DEVICE INIT
# ----------------------------------
if "device_token" not in st.session_state:
    try:
        r = requests.get(f"{BACKEND_URL}/device/init", timeout=10)
        data = r.json()
        st.session_state.device_token = data["device_token"]
    except Exception:
        st.error("❌ Backend not reachable.")
        st.stop()

def api_headers():
    return {
        "Authorization": f"Bearer {st.session_state.device_token}",
        "Content-Type": "application/json"
    }

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
    credits_data = r.json()
except Exception:
    st.warning("⚠️ Could not fetch credits.")

if credits_data:
    st.info(f"💳 Credits left: {credits_data['credits']}")

# ----------------------------------
# PAYMENT HELPER (AUTO REDIRECT)
# ----------------------------------
def redirect_to_checkout(pack: int):
    try:
        r = requests.post(
            f"{BACKEND_URL}/lemon/create-link?pack={pack}",
            headers=api_headers(),
            timeout=20
        )

        if r.status_code == 200:
            checkout_url = r.json()["checkout_url"]

            st.success("🔁 Redirecting to secure checkout...")
            st.markdown(
                f"""
                <meta http-equiv="refresh" content="0;url={checkout_url}">
                """,
                unsafe_allow_html=True
            )
            st.stop()

        st.error("❌ Payment could not be initiated")
        st.code(r.text)

    except Exception as e:
        st.error("❌ Payment error")
        st.code(str(e))

# ----------------------------------
# BUY CREDITS UI (AUTO REDIRECT)
# ----------------------------------
if credits_data and credits_data["credits"] == 0:

    st.markdown("---")
    st.subheader("✨ Buy Credits")
    st.write("You’ll be redirected to a secure checkout page.")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("### 5 Tries")
        st.markdown("**$2**")
        if st.button("Buy 5 Credits", use_container_width=True):
            redirect_to_checkout(5)

    with c2:
        st.markdown("### 15 Tries")
        st.markdown("**$5**")
        if st.button("Buy 15 Credits", use_container_width=True):
            redirect_to_checkout(15)

    with c3:
        st.markdown("### 100 Tries")
        st.markdown("**$20**")
        if st.button("Buy 100 Credits", use_container_width=True):
            redirect_to_checkout(100)

    st.caption("💡 After payment, you’ll be redirected back and credits will appear automatically.")

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
# USER INPUTS
# ----------------------------------
st.subheader("1. Upload your photo")
user_image = st.file_uploader(
    "Upload a clear, full-body photo",
    type=["jpg", "jpeg", "png", "webp"]
)

st.subheader("2. Outfit image")
query_params = st.query_params
cloth_url = query_params.get("cloth")

if cloth_url:
    st.image(cloth_url, caption="Selected outfit", width=260)
else:
    cloth_url = st.text_input("Paste outfit image URL")

st.subheader("3. Generate try-on")

# ----------------------------------
# TRY-ON
# ----------------------------------
if st.button("✨ Try it on", use_container_width=True):

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
