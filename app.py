import streamlit as st
import requests
import os
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# ----------------------------------
# CONFIG
# ----------------------------------
st.set_page_config(page_title="The Costume Hunt – Try On", layout="centered")

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
# DEVICE INIT (PERSIST VIA URL)
# ----------------------------------
query_params = st.query_params

if "device_token" in query_params:
    # Returning from Lemon or reload
    st.session_state.device_token = query_params["device_token"]
else:
    # First visit
    if "device_token" not in st.session_state:
        try:
            r = requests.get(f"{BACKEND_URL}/device/init", timeout=10)
            data = r.json()
            token = data["device_token"]

            st.session_state.device_token = token

            # persist device in URL
            st.query_params["device_token"] = token

        except Exception:
            st.error("❌ Backend not reachable.")
            st.stop()

def api_headers():
    return {
        "Authorization": f"Bearer {st.session_state.device_token}",
        "Content-Type": "application/json"
    }

# ----------------------------------
# PAYMENT SUCCESS MESSAGE
# ----------------------------------
if query_params.get("checkout") == "success":
    st.success("🎉 Payment successful! Credits have been added.")

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
# FREE UNLOCK
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
            st.error(f"Error: {str(e)}")

# ----------------------------------
# PAYMENT HELPER (🔑 FIX IS HERE)
# ----------------------------------
def create_checkout(pack: int):
    try:
        r = requests.post(
            f"{BACKEND_URL}/lemon/create-link?pack={pack}",
            headers=api_headers(),
            timeout=20
        )

        if r.status_code == 200:
            checkout_url = r.json().get("checkout_url")

            # 🔑 APPEND DEVICE TOKEN TO RETURN URL
            parsed = urlparse(checkout_url)
            qs = parse_qs(parsed.query)
            qs["device_token"] = st.session_state.device_token
            qs["checkout"] = "success"

            new_query = urlencode(qs, doseq=True)
            final_url = urlunparse(parsed._replace(query=new_query))

            return final_url

        st.error("❌ Backend error while creating checkout")
        st.code(r.text)
        return None

    except Exception as e:
        st.error("❌ Connection error")
        st.code(str(e))
        return None

# ----------------------------------
# BUY CREDITS UI (UNCHANGED UX)
# ----------------------------------
if credits_data and credits_data["credits"] == 0:

    st.markdown("---")
    st.subheader("✨ Buy Credits")
    st.write("You’ll complete payment on a secure checkout page and return here.")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("**5 tries**")
        st.markdown("$2")
        if st.button("💳 Buy 5 credits", key="buy5", use_container_width=True):
            link = create_checkout(5)
            if link:
                st.link_button("👉 Pay $2 Now", link, use_container_width=True, type="primary")

    with c2:
        st.markdown("**15 tries**")
        st.markdown("$5")
        if st.button("💳 Buy 15 credits", key="buy15", use_container_width=True):
            link = create_checkout(15)
            if link:
                st.link_button("👉 Pay $5 Now", link, use_container_width=True, type="primary")

    with c3:
        st.markdown("**100 tries**")
        st.markdown("$20")
        if st.button("💳 Buy 100 credits", key="buy100", use_container_width=True):
            link = create_checkout(100)
            if link:
                st.link_button("👉 Pay $20 Now", link, use_container_width=True, type="primary")

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
