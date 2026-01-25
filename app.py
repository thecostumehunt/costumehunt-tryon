import streamlit as st
import tempfile
import requests
import os
from PIL import Image
import io
import base64

# ========================================
# SETUP
# ========================================
st.set_page_config(page_title="The Costume Hunt – Try On", layout="centered")
os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]

st.title("👗 Virtual Try-On")
st.caption("Real AI clothing transfer")

if "used" not in st.session_state:
    st.session_state.used = False

# ========================================
# UI
# ========================================
st.subheader("1. Your Photo")
user_image = st.file_uploader("Full-body photo", type=["jpg", "png", "webp"])

st.subheader("2. Outfit Image")
cloth_url = st.text_input("Outfit URL")

# ========================================
# FIXED IMAGE PROCESSING - NO FILE OBJECTS
# ========================================
def image_to_base64(img_path):
    """Convert image to base64 - Fal.ai compatible"""
    with open(img_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def process_uploaded_image(upload):
    """Save uploaded image as temp file"""
    img = Image.open(upload).convert("RGB")
    temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(temp_path)
    return temp_path

def download_outfit(url):
    """Download URL to temp file"""
    r = requests.get(url, timeout=15)
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(temp_path)
    return temp_path

# ========================================
# MAIN TRY-ON BUTTON
# ========================================
if st.button("✨ AI Try-On", type="primary"):
    if st.session_state.used:
        st.error("Free try used!")
        st.stop()
    
    if not user_image or not cloth_url:
        st.error("Upload photo + enter URL")
        st.stop()
    
    with st.spinner("🎨 AI processing (15-25s)..."):
        person_path = None
        outfit_path = None
        
        try:
            # Process images to temp files
            person_path = process_uploaded_image(user_image)
            outfit_path = download_outfit(cloth_url)
            
            # ✅ FIXED: Use base64 instead of file objects
            person_b64 = image_to_base64(person_path)
            outfit_b64 = image_to_base64(outfit_path)
            
            # FAL.AI CALL - JSON SERIALIZABLE
            import fal_client
            result = fal_client.run(
                "fal-ai/idm-vton/fast-sdxl",
                arguments={
                    "person_image": person_b64,
                    "garment_image": outfit_b64,
                    "person_image_format": "base64",
                    "garment_image_format": "base64"
                }
            )
            
            # Display result
            st.image(result["images"][0], caption="✅ Your AI Try-On!", use_column_width=True)
            st.success("🎉 Real clothing transfer complete!")
            st.session_state.used = True
            
            st.download_button("💾 Download", data=result["images"][0], file_name="tryon.png")
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)[:100]}")
            st.info("Use full-body photos + single garments")
        
        finally:
            # Cleanup
            for path in [person_path, outfit_path]:
                if path and os.path.exists(path):
                    os.remove(path)

st.markdown("---")
st.caption("🔒 Photos auto-deleted")
