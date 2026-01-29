import streamlit as st
import requests
import os
import time

# ----------------------------------
# CONFIG
# ----------------------------------
st.set_page_config(page_title="The Costume Hunt – Try On", layout="centered")

BACKEND_URL = os.getenv("BACKEND_URL", "https://tryon-backend-5wf1.onrender.com")

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
@st.cache_data(ttl=30)
def get_credits():
    try:
        r = requests.get(f"{BACKEND_URL}/credits", headers=api_headers(), timeout=10)
        return r.json() if r.status_code == 200 else None
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
        img_bytes = requests.get(st.session_state.last_image).content
        st.download_button(
            "⬇️ Download image",
            data=img_bytes,
            file_name="tryon.png",
            mime="image/png"
        )
    except:
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
                headers={**api_headers(), "Content-Type": "application/json"},
                json={"email": email},
                timeout=10
            )
            if r.status_code == 200:
                st.success("✅ Free try unlocked!")
                st.rerun()
            else:
                st.error(f"Unlock failed: {r.text[:100]}")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# ----------------------------------
# PAYMENT SYSTEM (ORIGINAL + ROBUST)
# ----------------------------------
def create_checkout(pack):
    """Create LemonSqueezy checkout link via backend"""
    try:
        url = f"{BACKEND_URL}/lemon/create-link"
        payload = {"pack": pack}
        
        r = requests.post(
            url,
            headers={**api_headers(), "Content-Type": "application/json"},
            json=payload,
            timeout=15
        )
        
        if r.status_code == 200:
            data = r.json()
            return data.get("checkout_url")
        else:
            st.error(f"Backend error {r.status_code}: {r.text[:150]}")
            return None
            
    except requests.exceptions.Timeout:
        st.error("Backend timeout - payment service slow")
        return None
    except Exception as e:
        st.error(f"Payment error: {str(e)[:100]}")
        return None

# Cache checkout links for 5 minutes
@st.cache_data(ttl=300)
def get_cached_checkout(pack):
    return create_checkout(pack)

# ----------------------------------
# BUY CREDITS UI (ORIGINAL FLOW)
# ----------------------------------
if credits_data and credits_data["credits"] == 0:

    st.markdown("---")
    st.subheader("✨ Buy Credits")
    st.write("Get instant credits via LemonSqueezy (webhooks auto-sync)")

    # Payment packages
    packages = [
        {"name": "Starter", "credits": 5, "price": "$2", "key": "pkg5"},
        {"name": "Popular", "credits": 15, "price": "$5", "key": "pkg15"},
        {"name": "Pro", "credits": 100, "price": "$20", "key": "pkg100"}
    ]

    cols = st.columns(3)
    
    for i, pkg in enumerate(packages):
        with cols[i]:
            st.markdown(f"**{pkg['credits']} tries**")
            st.markdown(f"*{pkg['price']}*")
            
            # Generate link on button click
            if st.button(f"💳 Buy {pkg['credits']} credits", 
                        key=f"buy_{pkg['key']}", 
                        use_container_width=True):
                
                with st.spinner(f"🔄 Creating {pkg['credits']}-credit checkout..."):
                    link = get_cached_checkout(pkg['credits'])
                    
                    if link:
                        st.success(f"✅ Checkout ready for {pkg['credits']} credits!")
                        st.link_button(
                            f"👉 Pay {pkg['price']} Now", 
                            link, 
                            use_container_width=True,
                            type="primary",
                            help="Opens LemonSqueezy checkout (new tab)"
                        )
                        
                        # Show link info
                        st.info(f"💡 After payment, **refresh this page** to see credits")
                        
                    else:
                        st.error("❌ Backend payment service failed")
                        st.info("👨‍💻 Contact support or try again in 1 minute")

    st.markdown("---")

# ----------------------------------
# USER INPUTS
# ----------------------------------
st.subheader("1. Upload your photo")
user_image = st.file_uploader(
    "Upload a clear, full-body photo (standing, good lighting)",
    type=["jpg", "jpeg", "png", "webp"],
    help="Best results: full body, front-facing, plain background"
)

st.subheader("2. Outfit image")
query_params = st.query_params
cloth_url = query_params.get("cloth")

if cloth_url:
    st.image(cloth_url, caption="Selected outfit from blog", width=260, use_column_width=True)
else:
    cloth_url = st.text_input(
        "Paste outfit image URL", 
        placeholder="https://example.com/outfit.jpg",
        help="Works with any clothing image URL"
    )

st.subheader("3. Generate try-on")

# ----------------------------------
# TRY-ON BUTTON
# ----------------------------------
if st.button("✨ Try it on me!", use_container_width=True, type="primary"):

    # Validation
    if not user_image:
        st.warning("👆 Upload your photo first")
        st.stop()
    
    if not cloth_url:
        st.warning("👆 Enter outfit image URL")
        st.stop()
    
    if not credits_data or credits_data["credits"] < 1:
        st.warning("⛔ No credits! Buy credits above or unlock free try")
        st.stop()

    # Process try-on
    with st.spinner("🎨 Generating virtual try-on... (~30 seconds)"):
        try:
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
                st.success("🎉 Your virtual try-on is ready!")
                st.rerun()
            else:
                st.error(f"Try-on failed: {r.status_code}")
                st.info(f"Debug: {r.text[:200]}")
                
        except Exception as e:
            st.error(f"Processing error: {str(e)}")

# ----------------------------------
# FOOTER
# ----------------------------------
st.markdown("---")
st.markdown("*🔒 Your photos are processed temporarily and **deleted immediately after***")
st.markdown("*🩷 Powered by TheCostumeHunt.com*")
