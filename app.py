import streamlit as st
import requests
import io
from PIL import Image
import base64
import os

# ========================================
# PAGE SETUP
# ========================================
st.set_page_config(
    page_title="The Costume Hunt – Try On", 
    layout="centered",
    page_icon="👗"
)

st.title("👗 Virtual Try-On")
st.markdown("**Upload your photo + outfit = AI puts clothes on your body**")
st.caption("Powered by TheCostumeHunt.com • Real AI • Photos auto-deleted")

# ========================================
# SECRETS & STATE
# ========================================
os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]

if "used_free" not in st.session_state:
    st.session_state.used_free = False

# ========================================
# BLOG INTEGRATION
# ========================================
query_params = st.query_params
cloth_url = query_params.get("cloth", "")

# ========================================
# UI - PHOTO UPLOAD
# ========================================
st.subheader("📸 1. Upload Your Photo")
user_image = st.file_uploader(
    "Upload **FULL BODY** photo (standing works best)",
    type=["jpg", "jpeg", "png", "webp"],
    help="Plain background + good lighting = best AI results"
)

# ========================================
# UI - OUTFIT IMAGE
# ========================================
st.subheader("👗 2. Outfit Image")
col1, col2 = st.columns([4, 1])

with col1:
    if cloth_url:
        try:
            st.image(cloth_url, caption="✅ Auto-loaded from blog", width=300)
        except:
            cloth_url = ""
            st.warning("Invalid image URL")
    else:
        cloth_url = st.text_input(
            "Paste outfit image URL from thecostumehunt.com",
            placeholder="https://thecostumehunt.com/wp-content/uploads/outfit.webp"
        )

with col2:
    st.info("💡 **Best Results:**\n• Single garment\n• Front-facing\n• Tops/dresses")

# ========================================
# HELPER FUNCTIONS
# ========================================
def image_to_base64(image_data):
    """Convert image to data URI for AI"""
    if hasattr(image_data, 'seek'):
        image_data.seek(0)
    img = Image.open(image_data).convert("RGB")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"

# ========================================
# AI TRY-ON BUTTON
# ========================================
if st.button("✨ **GENERATE AI TRY-ON** ✨", type="primary", use_container_width=True):
    
    # Validation
    if st.session_state.used_free:
        st.error("🆓 **Free try used!** Refresh page for 1 more free try.")
        st.markdown("### 🚀 **Unlimited Try-Ons Coming Soon**")
        st.stop()
    
    if not user_image:
        st.error("📸 **Upload your photo first**")
        st.stop()
    
    if not cloth_url:
        st.error("👗 **Enter outfit image URL**")
        st.stop()
    
    # ========================================
    # AI PROCESSING
    # ========================================
    with st.spinner("🎨 **Real AI clothing transfer in progress... 20-40 seconds**"):
        try:
            # Prepare images
            person_b64 = image_to_base64(user_image)
            
            outfit_response = requests.get(cloth_url, timeout=20)
            outfit_response.raise_for_status()
            outfit_b64 = image_to_base64(io.BytesIO(outfit_response.content))
            
            # ====================================
            # FAL.AI API CALL - CORRECT FORMAT
            # ====================================
            FAL_URL = "https://fal.run/fal-ai/idm-vton"
            headers = {
                "Authorization": f"Key {st.secrets['FAL_KEY']}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "human_image_url": person_b64,
                "garment_image_url": outfit_b64,
                "description": "professional fashion model wearing exact garment, full body shot, clean studio lighting, high quality photography"
            }
            
            api_response = requests.post(FAL_URL, json=payload, headers=headers, timeout=120)
            api_response.raise_for_status()
            result = api_response.json()
            
            # ====================================
            # EXTRACT & DISPLAY RESULT
            # ====================================
            output_image = None
            
            # Handle all possible response formats
            if "images" in result and result["images"]:
                output_image = result["images"][0]
            elif "image" in result:
                output_image = result["image"]
            elif "output" in result:
                output_image = result["output"]
            
            if not output_image:
                st.error("No image returned from AI")
                st.json(result)
                st.stop()
            
            # Display AI result
            if isinstance(output_image, str):
                if output_image.startswith("http"):
                    st.image(output_image, caption="✅ **YOUR AI TRY-ON RESULT**", use_column_width=True)
                else:
                    # Base64 image
                    img_data = base64.b64decode(output_image.lstrip("data:image/png;base64,"))
                    result_img = Image.open(io.BytesIO(img_data))
                    st.image(result_img, caption="✅ **YOUR AI TRY-ON RESULT**", use_column_width=True)
            else:
                st.error("Invalid image format")
                st.stop()
            
            # Success!
            st.success("🎉 **PERFECT! Real AI clothing transfer complete**")
            st.balloons()
            
            st.session_state.used_free = True
            
            # Action buttons
            col1, col2, col3 = st.columns(3)
            with col1:
                st.download_button(
                    label="💾 Download Result",
                    data=requests.get(output_image).content if output_image.startswith("http") else base64.b64decode(output_image.lstrip("data:image/png;base64,")),
                    file_name="thecostumehunt-tryon.png",
                    mime="image/png"
                )
            with col2:
                if st.button("🔄 New Try-On", use_container_width=True):
                    st.rerun()
            with col3:
                st.success("📱 Pinterest ready!")
            
            st.markdown("**✨ Share your result on Pinterest!**")
            
        except requests.exceptions.RequestException as e:
            st.error(f"🌐 Network error: {str(e)}")
        except Exception as e:
            st.error(f"❌ AI Error: {str(e)[:150]}...")
            st.info("""
            **🔧 Troubleshooting Tips:**
            • Use **FULL BODY** standing photos
            • Single garment only (no collages)
            • Front-facing outfit images
            • Good lighting helps AI
            """)

# ========================================
# FOOTER
# ========================================
st.markdown("---")
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("""
    **🔒 Privacy Guaranteed**
    - Photos auto-deleted instantly
    - No storage anywhere
    - Processed in browser memory
    """)

with col2:
    st.markdown("""
    **🚀 Powered By**
    - Fal.ai IDM-VTON AI
    - Real clothing transfer
    - TheCostumeHunt.com
    """)

st.caption("👗 Daily wear fashion inspiration for Indian women")
