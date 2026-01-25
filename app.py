import streamlit as st
import tempfile
import requests
import os
from PIL import Image
import io

# ========================================
# DEBUG SECRETS FIRST (REMOVE LATER)
# ========================================
st.set_page_config(page_title="The Costume Hunt – Try On", layout="centered")

# TEST SECRETS ACCESS
try:
    test_key = st.secrets["FAL_API_KEY"]
    st.success(f"✅ SECRETS OK! Key length: {len(test_key)} chars")
except Exception as e:
    st.error(f"❌ SECRETS ERROR: {str(e)}")
    st.info("""
    **FIX SECRETS:**
    1. Streamlit Cloud → Settings → Secrets
    2. DELETE all FAL_API_KEY lines
    3. Add EXACTLY: `FAL_API_KEY = "fal_sk_xxxxx"`
    4. Click SAVE
    """)
    st.stop()

# ========================================
# FAL.AI CLIENT SETUP
# ========================================
try:
    import fal_client
    fal_client.api_key(st.secrets["FAL_API_KEY"])
    st.success("✅ FAL.AI Connected!")
except ImportError:
    st.error("❌ Install `fal-client` in requirements.txt")
    st.stop()
except Exception as e:
    st.error(f"❌ FAL.AI Error: {str(e)}")
    st.stop()

# ========================================
# MAIN APP
# ========================================
st.title("👗 Virtual Try-On")
st.markdown("**Real AI clothing transfer**")

if "used" not in st.session_state:
    st.session_state.used = False

# UI
st.subheader("1. Your Photo")
user_image = st.file_uploader("Full-body photo", type=["jpg", "png", "webp"])

st.subheader("2. Outfit Image")
cloth_url = st.text_input("Outfit URL from thecostumehunt.com")

if st.button("✨ AI Try-On", type="primary"):
    if st.session_state.used:
        st.error("Free try used! Refresh for reset.")
        st.stop()
    
    if not user_image or not cloth_url:
        st.error("Upload photo + enter outfit URL")
        st.stop()
    
    with st.spinner("AI processing... 15-25s"):
        try:
            # Process images
            person_path = process_image(user_image)
            outfit_path = download_image(cloth_url)
            
            # FAL.AI CALL
            result = fal_client.run(
                "fal-ai/idm-vton/fast-sdxl",
                arguments={
                    "person_image": open(person_path, "rb"),
                    "garment_image": open(outfit_path, "rb")
                }
            )
            
            st.image(result["images"][0], caption="✅ Your Try-On!", use_column_width=True)
            st.success("🎉 Real AI clothing transfer complete!")
            st.session_state.used = True
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
        finally:
            cleanup(person_path, outfit_path)

# Helpers (simplified)
def process_image(file):
    img = Image.open(file).convert("RGB")
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(temp.name)
    temp.close()
    return temp.name

def download_image(url):
    r = requests.get(url, timeout=15)
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(temp.name)
    temp.close()
    return temp.name

def cleanup(p1, p2):
    for path in [p1, p2]:
        if path and os.path.exists(path):
            os.remove(path)

st.markdown("---")
st.caption("🔒 Photos auto-deleted • TheCostumeHunt.com")
