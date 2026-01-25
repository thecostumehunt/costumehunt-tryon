import streamlit as st
import requests
import io
from PIL import Image
import base64

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
            # Convert images
            person_b64 = image_to_base64(user_image)
            outfit_resp = requests.get(cloth_url, timeout=15)
            outfit_b64 = image_to_base64(io.BytesIO(outfit_resp.content))
            
            # API call
            FAL_URL = "https://fal.run/fal-ai/idm-vton"
            headers = {
                "Authorization": f"Key {st.secrets['FAL_KEY']}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "human_image_url": f"data:image/png;base64,{person_b64}",
                "garment_image_url": f"data:image/png;base64,{outfit_b64}",
                "description": "professional fashion model wearing daily wear outfit, full body, studio lighting"
            }
            
            response = requests.post(FAL_URL, json=payload, headers=headers)
            result = response.json()
            
            # ✅ FIXED: Proper response parsing for DICT objects
            output_image = None
            
            # Handle dict response properly
            if isinstance(result, dict):
                # Try common image locations
                if "images" in result and isinstance(result["images"], list) and len(result["images"]) > 0:
                    output_image = result["images"][0]
                elif "image" in result:
                    output_image = result["image"]
                elif "output" in result:
                    output_image = result["output"]
                elif "result" in result:
                    output_image = result["result"]
            
            if not output_image:
                st.error("No image in API response")
                st.json(result)  # Debug
                st.stop()
            
            # ✅ FIXED: Check type before startswith
            if isinstance(output_image, str):
                if output_image.startswith("http"):
                    st.image(output_image, caption="✅ Your AI Try-On!", use_column_width=True)
                    img_data = requests.get(output_image).content
                else:  # base64
                    img_data = base64.b64decode(output_image)
                    result_img = Image.open(io.BytesIO(img_data))
                    st.image(result_img, caption="✅ Your AI Try-On!", use_column_width=True)
            else:
                st.error("Image data invalid type")
                st.stop()
            
            st.success("🎉 Real clothing transfer complete!")
            st.balloons()
            st.session_state.used = True
            
            # Fixed download
            st.download_button("💾 Download Result", 
                             data=img_data, 
                             file_name="tryon-result.png")
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.info("💡 Full-body photos + single garment images work best")

st.markdown("---")
st.caption("🔒 Photos processed in memory only")
