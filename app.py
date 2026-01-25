import streamlit as st
import requests
import io
from PIL import Image
import base64

# Setup
st.set_page_config(page_title="The Costume Hunt – Try On", layout="centered")
st.title("👗 Virtual Try-On")
st.caption("Real AI clothing transfer - TheCostumeHunt.com")

if "used" not in st.session_state:
    st.session_state.used = False

# UI
st.subheader("1. Your Photo")
user_image = st.file_uploader("Full-body photo", type=["jpg", "png", "webp"])

st.subheader("2. Outfit Image")
cloth_url = st.text_input("Outfit URL from thecostumehunt.com")

# Convert image to base64
def image_to_base64(image_data):
    img = Image.open(image_data).convert("RGB")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

# MAIN TRY-ON
if st.button("✨ AI Virtual Try-On ✨", type="primary"):
    if st.session_state.used:
        st.error("Free try used! Refresh page.")
        st.stop()
    
    if not user_image or not cloth_url:
        st.error("Upload photo + enter outfit URL")
        st.stop()
    
    with st.spinner("🎨 AI processing (20-40s)..."):
        try:
            # Convert to base64
            person_b64 = image_to_base64(user_image)
            outfit_resp = requests.get(cloth_url, timeout=15)
            outfit_b64 = image_to_base64(io.BytesIO(outfit_resp.content))
            
            # ✅ FIXED: EXACT API parameters required
            FAL_URL = "https://fal.run/fal-ai/idm-vton"
            headers = {
                "Authorization": f"Key {st.secrets['FAL_KEY']}",
                "Content-Type": "application/json"
            }
            
            # ✅ CORRECT FIELD NAMES FROM ERROR
            payload = {
                "human_image_url": f"data:image/png;base64,{person_b64}",
                "garment_image_url": f"data:image/png;base64,{outfit_b64}",
                "description": "professional fashion model wearing daily wear outfit, full body, studio lighting, clean background"
            }
            
            response = requests.post(FAL_URL, json=payload, headers=headers)
            result = response.json()
            
            # Handle response
            if "images" in result and result["images"]:
                output_image = result["images"][0]
            elif "image" in result:
                output_image = result["image"]
            else:
                st.error("Unexpected response")
                st.json(result)
                st.stop()
            
            # Display result
            if output_image.startswith("http"):
                st.image(output_image, caption="✅ Your AI Try-On!", use_column_width=True)
            else:
                img_data = base64.b64decode(output_image)
                result_img = Image.open(io.BytesIO(img_data))
                st.image(result_img, caption="✅ Your AI Try-On!", use_column_width=True)
            
            st.success("🎉 Real clothing transfer complete!")
            st.balloons()
            st.session_state.used = True
            
            st.download_button("💾 Download", 
                             data=base64.b64decode(output_image) if not output_image.startswith("http") else requests.get(output_image).content,
                             file_name="tryon-result.png")
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.info("💡 Full-body photos + single garments")

st.markdown("---")
st.caption("🔒 Photos never stored")
