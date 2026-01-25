import streamlit as st
import tempfile
import requests
import os
from PIL import Image
import io
import base64

# Setup
st.set_page_config(page_title="The Costume Hunt – Try On", layout="centered")
os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]

st.title("👗 Virtual Try-On")
st.caption("🔥 Real AI clothing transfer - TheCostumeHunt.com")

if "used" not in st.session_state:
    st.session_state.used = False

# UI
st.subheader("1. Your Photo")
user_image = st.file_uploader("Full-body photo", type=["jpg", "png", "webp"])

st.subheader("2. Outfit Image") 
cloth_url = st.text_input("Outfit URL from thecostumehunt.com")

# Helper functions - FIXED for JSON serialization
def save_image_temp(img_data):
    """Save image data to temp file"""
    img = Image.open(img_data).convert("RGB")
    temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(temp_path)
    return temp_path

def download_outfit(url):
    """Download outfit to temp file"""
    r = requests.get(url, timeout=15)
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(temp_path)
    return temp_path

# MAIN TRY-ON
if st.button("✨ AI Virtual Try-On ✨", type="primary"):
    if st.session_state.used:
        st.error("🆓 Free try used! Refresh for more.")
        st.stop()
    
    if not user_image or not cloth_url:
        st.error("📸 Photo + 👗 Outfit URL required")
        st.stop()
    
    with st.spinner("🎨 Real AI clothing transfer (20-40s)..."):
        person_path = None
        outfit_path = None
        
        try:
            # Process images
            person_path = save_image_temp(user_image)
            outfit_path = download_outfit(cloth_url)
            
            # ✅ FIXED MODEL PATH - REAL VTON MODEL
            import fal_client
            result = fal_client.run(
                "fal-ai/tryon-v1.5",  # ✅ CORRECT VTON MODEL
                arguments={
                    "person_image": open(person_path, "rb"),
                    "garment_image": open(outfit_path, "rb")
                }
            )
            
            # Display result
            st.image(result["images"][0], caption="✅ Your AI Try-On Result!", use_column_width=True)
            st.success("🎉 Perfect! Real clothing transfer complete!")
            st.balloons()
            st.session_state.used = True
            
            # Download
            st.download_button("💾 Save Result", data=result["images"][0], file_name="tryon-result.png")
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)[:120]}")
            st.info("""
            **💡 Best Results:**
            • Full-body standing photos
            • Single garment (top/dress)
            • Front-facing outfit images
            """)
        
        finally:
            # Cleanup
            for path in [person_path, outfit_path]:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass

# Footer
st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**🔒 Privacy**")
    st.caption("• Photos auto-deleted\n• No storage")
with col2:
    st.markdown("**🚀 Powered by**")
    st.caption("• Fal.ai Virtual Try-On\n• TheCostumeHunt.com")
