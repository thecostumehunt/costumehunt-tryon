import streamlit as st
import requests
import io
from PIL import Image
import base64
import os

# Setup
st.set_page_config(page_title="The Costume Hunt – Try On", layout="centered")
os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]

st.title("👗 Virtual Try-On")
st.caption("Real AI clothing transfer - TheCostumeHunt.com")

if "used" not in st.session_state:
    st.session_state.used = False

# UI
st.subheader("1. Your Photo")
user_image = st.file_uploader("Full-body photo", type=["jpg", "png", "webp"])

st.subheader("2. Outfit Image")
cloth_url = st.text_input("Outfit URL")

# FIXED: Convert images to base64 (JSON serializable)
def image_to_base64(image_data):
    """Convert PIL image or bytes to base64"""
    if hasattr(image_data, 'read'):  # File-like object
        image_data.seek(0)
        img = Image.open(image_data).convert("RGB")
    else:  # Uploaded file
        img = Image.open(image_data).convert("RGB")
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return img_str

# MAIN TRY-ON BUTTON
if st.button("✨ AI Virtual Try-On ✨", type="primary"):
    if st.session_state.used:
        st.error("🆓 Free try used! Refresh for more.")
        st.stop()
    
    if not user_image or not cloth_url:
        st.error("📸 Photo + 👗 Outfit URL required")
        st.stop()
    
    with st.spinner("🎨 Real AI clothing transfer (20-40s)..."):
        try:
            # ✅ FIXED: Convert to base64 - NO file objects
            person_b64 = image_to_base64(user_image)
            
            # Download outfit as base64
            outfit_response = requests.get(cloth_url, timeout=15)
            outfit_b64 = image_to_base64(io.BytesIO(outfit_response.content))
            
            # ✅ HTTP API CALL - JSON SERIALIZABLE
            FAL_URL = "https://fal.run/fal-ai/tryon-v1.5"
            headers = {
                "Authorization": f"Key {st.secrets['FAL_KEY']}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "input": {
                    "person_image": person_b64,
                    "garment_image": outfit_b64
                }
            }
            
            response = requests.post(FAL_URL, json=payload, headers=headers)
            result = response.json()
            
            # Display result
            result_image = Image.open(io.BytesIO(base64.b64decode(result["images"][0])))
            st.image(result_image, caption="✅ Your AI Try-On!", use_column_width=True)
            st.success("🎉 Real clothing transfer complete!")
            st.balloons()
            st.session_state.used = True
            
            # Download
            st.download_button("💾 Save Result", 
                             data=result["images"][0], 
                             file_name="tryon-result.png",
                             mime="image/png")
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)[:120]}")
            st.info("💡 Full-body photos + single garments work best")

# Footer
st.markdown("---")
st.caption("🔒 Photos processed in memory • TheCostumeHunt.com")
