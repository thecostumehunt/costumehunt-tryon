import streamlit as st
import tempfile
import requests
import os
from PIL import Image
import io

# ========================================
# SECRETS SETUP - CORRECT WAY
# ========================================
st.set_page_config(page_title="The Costume Hunt – Try On", layout="centered")

# Set Fal.ai environment variable from secrets
os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]

# Test secrets
try:
    test_key = st.secrets["FAL_KEY"]
    st.success(f"✅ FAL_KEY loaded: {len(test_key)} chars")
except:
    st.error("❌ Add FAL_KEY to Streamlit Secrets")
    st.info("Streamlit Cloud → Settings → Secrets → `FAL_KEY = \"fal_sk_xxxxx\"`")
    st.stop()

# ========================================
# FAL.AI IMPORT & TEST
# ========================================
try:
    import fal_client
    st.success("✅ fal_client imported successfully")
except ImportError:
    st.error("❌ Install `fal-client` in requirements.txt")
    st.stop()

# ========================================
# MAIN APP
# ========================================
st.title("👗 Virtual Try-On")
st.markdown("**Real AI clothing transfer**")

if "used" not in st.session_state:
    st.session_state.used = False

# UI Inputs
st.subheader("1. Your Photo")
user_image = st.file_uploader("Full-body photo", type=["jpg", "png", "webp"])

st.subheader("2. Outfit Image")
cloth_url = st.text_input("Outfit URL from thecostumehunt.com")

# Helper functions
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

# Main button
if st.button("✨ AI Try-On", type="primary"):
    if st.session_state.used:
        st.error("Free try used! Refresh page.")
        st.stop()
    
    if not user_image or not cloth_url:
        st.error("Upload photo + enter outfit URL")
        st.stop()
    
    with st.spinner("🎨 AI Virtual Try-On (15-25s)..."):
        person_path = None
        outfit_path = None
        
        try:
            # Process images
            person_path = process_image(user_image)
            outfit_path = download_image(cloth_url)
            
            # FAL.AI CALL (CORRECT SYNTAX - NO api_key() method)
            result = fal_client.run(
                "fal-ai/idm-vton/fast-sdxl",
                arguments={
                    "person_image": open(person_path, "rb"),
                    "garment_image": open(outfit_path, "rb")
                }
            )
            
            # Display result
            st.image(result["images"][0], caption="✅ Your AI Try-On!", use_column_width=True)
            st.success("🎉 Real clothing transfer complete!")
            st.session_state.used = True
            
            # Download button
            st.download_button("💾 Download", data=result["images"][0], file_name="tryon.png")
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)[:100]}...")
            st.info("💡 Use full-body photos + single garment images")
        
        finally:
            # Cleanup
            for path in [person_path, outfit_path]:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass

st.markdown("---")
st.caption("🔒 Photos auto-deleted • TheCostumeHunt.com")
