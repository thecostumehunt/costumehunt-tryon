import streamlit as st
import requests
import os
from streamlit_cookies_manager import EncryptedCookieManager

# ----------------------------------
# CONFIG
# ----------------------------------
st.set_page_config(page_title="The Costume Hunt – Try On", layout="centered")

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

# ----------------------------------
# COOKIE MANAGER (PERSIST DEVICE)
# ----------------------------------
cookies = EncryptedCookieManager(
    prefix="tryon_",
    password="CHANGE_THIS_TO_A_LONG_RANDOM_SECRET_123!@#"
)

if not cookies.ready():
    st.stop()

# ----------------------------------
# PAGE HEADER
# ----------------------------------
st.title("👗 Try This Outfit On Yourself")
st.write("Upload your full-body photo and preview how a full outfit looks on you.")
st.caption("Powered by TheCostumeHunt.com • Photos are processed temporarily and deleted.")

# ----------------------------------
# DEVICE INIT (PERSISTENT)
# ----------------------------------
if "device_token" not in st.session_state:
    saved_token = cookies.get("device_token")

    if saved_token:
        st.session_state.device_token = saved_token
    else:
        try:
            r = requests.get(f"{BACKEND_URL}/device/init", timeout=10)
            data = r.json()

            if "device_token" in data:
                st.session_state.device_token = data["device_token"]
                cookies["device_token"] = data["device_token"]
                cookies.save()

            st.session_state.device = data

        except:
            st.error("❌ Backend not reachable. Please try again later.")
            st.stop()


def api_headers():
    return {
        "Authorization": f"Bearer {st.session_state.device_token}"
    }

# ----------------------------------
# HELPER — CREATE LEMON CHECKOUT
# ----------------------------------
def create_checkout(pack):
    try:
        r = requests.post(
            f"{BACKEND_URL}/lemon/create-link?pack={pack}",
            headers=api_headers(),
            timeout=10
        )
        data = r.json()
        st.write("Checkout response:", data)
        return data.get("checkout_url")
    except:
        st.error("Payment service not reachable.")
        return None

# ----------------------------------
# FETCH CREDITS
# ----------------------------------
credits_data = None
try:
    r = requests.get(f"{BACKEND_URL}/credits", headers=api_headers(), timeout=10)
    credits_data = r.json()
except:
    st.warning("⚠️ Could not fetch credits.")

if credits_data:
    st.info(f"💳 Credits left: {credits_data['credits']}")

# ----------------------------------
# SHOW LAST RESULT
# ----------------------------------
if "last_image" in st.session_state:
    st.subheader("🖼 Your last try-on result")
    st.image(st.session_state.last_image, use_container_width=True)

# ----------------------------------
# FREE UNLOCK UI
# ----------------------------------
if credits_data and credits_data["credits"] == 0 and not credits_data["free_used"]:
    st.subheader("🎁 Get your free try")
    email = st.text_input("Enter your email to unlock your free try")

    if st.button("Unlock free try"):
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
            st.error(r.json().get("detail", "Unlock failed"))

# ----------------------------------
# BUY CREDITS UI
# ----------------------------------
if credits_data and credits_data["credits"] == 0:

    st.markdown("---")
    st.subheader("✨ Continue trying outfits")
    st.write("You’ve used your free try. Get more credits to try different outfits on yourself.")

    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("💳 5 tries – $2"):
            link = create_checkout(5)
            if link:
                st.markdown(f"<meta http-equiv='refresh' content='0;url={link}'>", unsafe_allow_html=True)

    with c2:
        if st.button("💳 15 tries – $5"):
            link = create_checkout(15)
            if link:
                st.markdown(f"<meta http-equiv='refresh' content='0;url={link}'>", unsafe_allow_html=True)

    with c3:
        if st.button("💳 100 tries – $20"):
            link = create_checkout(100)
            if link:
                st.markdown(f"<meta http-equiv='refresh' content='0;url={link}'>", unsafe_allow_html=True)

    st.caption("🔒 Credits are added instantly after payment and saved on this device.")

# ----------------------------------
# USER INPUTS
# ----------------------------------
st.subheader("1. Upload your photo")
user_image = st.file_uploader(
    "Upload a clear, full-body photo (standing pose, head to feet visible)",
    type=["jpg", "jpeg", "png", "webp"]
)

st.subheader("2. Outfit image")

query_params = st.query_params
cloth_url = query_params.get("cloth", None)

if cloth_url:
    try:
        st.image(cloth_url, caption="Selected outfit", width=260)
    except:
        cloth_url = None
        st.warning("Could not load image. Please paste a direct image URL.")
else:
    cloth_url = st.text_input("Paste outfit image URL")

st.subheader("3. Generate try-on")

# ----------------------------------
# TRY-ON BUTTON
# ----------------------------------
if st.button("✨ Try it on"):

    if not user_image or not cloth_url:
        st.warning("Please upload your photo and provide an outfit image.")
        st.stop()

    if not credits_data or credits_data["credits"] < 1:
        st.warning("You don't have credits. Unlock free try or purchase credits.")
        st.stop()

    with st.spinner("Creating your virtual try-on… please wait 30–60 seconds"):
        try:
            files = {
                "person_image": user_image.getvalue()
            }

            params = {
                "garment_url": cloth_url
            }

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
                st.success("🎉 Your try-on is ready!")
                st.rerun()
            else:
                st.error(r.json().get("detail", "Try-on failed"))

        except Exception as e:
            st.error("🚨 Try-on failed.")
            st.write(str(e))

# ----------------------------------
# FOOTER
# ----------------------------------
st.markdown("---")
st.caption("🔒 Credits are saved on this device. Clearing site data will remove access.")
st.caption("🩷 Daily-wear inspiration by TheCostumeHunt.com")
