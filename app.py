import streamlit as st
import requests
import os
import streamlit.components.v1 as components

# ----------------------------------
# CONFIG
# ----------------------------------
st.set_page_config(page_title="The Costume Hunt – Try On", layout="centered")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

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
        if "device_token" in data:
            st.session_state.device_token = data["device_token"]
        st.session_state.device = data
    except:
        st.error("❌ Backend not reachable.")
        st.stop()

def api_headers():
    return {"Authorization": f"Bearer {st.session_state.device_token}"}

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
    st.download_button(
        "⬇️ Download image",
        data=requests.get(st.session_state.last_image).content,
        file_name="tryon.png",
        mime="image/png"
    )

# ----------------------------------
# FREE UNLOCK
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
            st.error("Unlock failed")

# ----------------------------------
# PAYMENT HELPERS
# ----------------------------------
def create_checkout(pack):
    try:
        r = requests.post(
            f"{BACKEND_URL}/lemon/create-link?pack={pack}",
            headers=api_headers(),
            timeout=10
        )
        return r.json().get("checkout_url")
    except:
        return None

# ----------------------------------
# BUY CREDITS UI
# ----------------------------------
if credits_data and credits_data["credits"] == 0:
    st.markdown("---")
    st.subheader("✨ Continue trying outfits")
    st.write("Buy credits to try more outfits on yourself.")

    c1, c2, c3 = st.columns(3)

    def redirect(link):
        components.html(
            f"""
            <html>
            <head>
            <script>
                window.top.location.href = "{link}";
            </script>
            </head>
            <body></body>
            </html>
            """,
            height=0,
        )

    with c1:
        if st.button("💳 5 tries – $2"):
            link = create_checkout(5)
            if link:
                st.success("Redirecting to checkout...")
                redirect(link)

    with c2:
        if st.button("💳 15 tries – $5"):
            link = create_checkout(15)
            if link:
                st.success("Redirecting to checkout...")
                redirect(link)

    with c3:
        if st.button("💳 100 tries – $20"):
            link = create_checkout(100)
            if link:
                st.success("Redirecting to checkout...")
                redirect(link)

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
cloth_url = query_params.get("cloth", None)

if cloth_url:
    st.image(cloth_url, caption="Selected outfit", width=260)
else:
    cloth_url = st.text_input("Paste outfit image URL")

st.subheader("3. Generate try-on")

# ----------------------------------
# TRY-ON
# ----------------------------------
if st.button("✨ Try it on"):
    if not user_image or not cloth_url:
        st.warning("Please upload your photo and provide outfit image.")
        st.stop()

    if not credits_data or credits_data["credits"] < 1:
        st.warning("You don't have credits.")
        st.stop()

    with st.spinner("Creating your virtual try-on…"):
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
            data = r.json()
            st.session_state.last_image = data["image_url"]
            st.success("🎉 Your try-on is ready!")
            st.rerun()
        else:
            st.error("Try-on failed")

# ----------------------------------
# FOOTER
# ----------------------------------
st.markdown("---")
st.write("🔒 Photos are automatically deleted after processing.")
st.write("🩷 TheCostumeHunt.com")
