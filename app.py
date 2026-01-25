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
    """Convert any image (jpg/png/webp) to base64 PNG"""
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
    with st.spinner("🎨 **Real AI clothing transfer in progress... 20–40 seconds**"):
        try:
            # Prepare images
            person_b64 = image_to_base64(user_image)

            outfit_response = requests.get(cloth_url, timeout=20)
            outfit_response.raise_for_status()
            outfit_b64 = image_to_base64(io.BytesIO(outfit_response.content))

            # ====================================
            # FAL API CALL
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
            # EXTRACT RESULT (ROBUST)
            # ====================================
            output_image = None

            if "images" in result and result["images"]:
                first = result["images"][0]
                if isinstance(first, dict) and "url" in first:
                    output_image = first["url"]
                else:
                    output_image = first

            elif "image" in result:
                if isinstance(result["image"], dict) and "url" in result["image"]:
                    output_image = result["image"]["url"]
                else:
                    output_image = result["image"]

            elif "output" in result:
                output_image = result["output"]

            if not output_image:
                st.error("No image returned from AI")
                st.json(result)
                st.stop()

            # ====================================
            # DISPLAY RESULT
            # ====================================
            image_bytes = None

            if isinstance(output_image, str):

                if output_image.startswith("http"):
                    st.image(output_image, caption="✅ **YOUR AI TRY-ON RESULT**", use_column_width=True)
                    image_bytes = requests.get(output_image).content

                elif "base64" in output_image:
                    image_bytes = base64.b64decode(output_image.split(",")[-1])
                    result_img = Image.open(io.BytesIO(image_bytes))
                    st.image(result_img, caption="✅ **YOUR AI TRY-ON RESULT**", use_column_width=True)

                else:
                    st.error("Unknown image format returned")
                    st.write(output_image[:200])
                    st.stop()

            else:
                st.error("Unsupported image format returned by AI")
                st.stop()

            # ====================================
            # SUCCESS UI
            # ====================================
            st.success("🎉 **PERFECT! Real AI clothing transfer complete**")
            st.balloons()

            st.session_state.used_free = True

            col1, col2, col3 = st.columns(3)
            with col1:
                if image_bytes:
                    st.download_button(
                        label="💾 Download Result",
                        data=image_bytes,
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
            **🔧 Tips**
            • Full body standing photos  
            • Single garment images  
            • Front-facing clothes  
            • Good lighting helps  
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
    - No storage  
    - Browser-memory processing  
    """)

with col2:
    st.markdown("""
    **🚀 Powered By**
    - Fal.ai IDM-VTON  
    - Real clothing transfer  
    - TheCostumeHunt.com  
    """)

st.caption("👗 Daily wear fashion inspiration for women")
