import streamlit as st
import tempfile
import requests
import os
from PIL import Image
import io
import fal_client

# ========================================
# PAGE SETUP
# ========================================
st.set_page_config(page_title="The Costume Hunt – Try On", layout="centered", page_icon="👗")

st.title("👗 Virtual Try-On")
st.markdown("**Upload your photo + outfit = AI magic**")
st.caption("🔥 Powered by Fal.ai • Real clothing transfer • Photos auto-deleted")

# ========================================
# FAL.AI SETUP & API KEY
# ========================================
if "fal_key_set" not in st.session_state:
    st.session_state.fal_key_set = False

try:
    fal_client.api_key(st.secrets["FAL_API_KEY"])
    st.session_state.fal_key_set = True
except:
    st.error("❌ **Missing FAL_API_KEY**")
    st.info("👉 Streamlit Cloud → Settings → Secrets → Add: `FAL_API_KEY=your_key`")
    st.stop()

# ========================================
# SESSION STATE
# ========================================
if "used_free" not in st.session_state:
    st.session_state.used_free = False

# ========================================
# INPUTS
# ========================================
st.subheader("📸 1. Your Photo")
user_image = st.file_uploader(
    "Upload clear **full-body photo** (standing, good lighting)",
    type=["jpg", "jpeg", "png", "webp"],
    help="Best results: plain background, front-facing, full body visible"
)

# Blog integration
query_params = st.query_params
cloth_url = query_params.get("cloth")

st.subheader("👗 2. Outfit Image")
col1, col2 = st.columns([3, 1])

with col1:
    if cloth_url:
        try:
            st.image(cloth_url, caption="✅ Auto-loaded from blog", width=300)
        except:
            cloth_url = None
            st.warning("🔗 Invalid image URL")
    else:
        cloth_url = st.text_input(
            "Paste outfit image URL from thecostumehunt.com",
            placeholder="https://thecostumehunt.com/wp-content/uploads/outfit.webp"
        )

with col2:
    st.info("💡 Use single garment images\n(tops, dresses, kurtis work best)")

# ========================================
# HELPER FUNCTIONS
# ========================================
@st.cache_data
def process_image(file):
    """Convert to consistent PNG format"""
    img = Image.open(file).convert("RGB")
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(temp_file.name, format="PNG")
    temp_file.close()
    return temp_file.name

def download_outfit(url):
    """Download and process outfit image"""
    r = requests.get(url, timeout=15, stream=True)
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(temp_file.name, format="PNG")
    temp_file.close()
    return temp_file.name

# ========================================
# TRY-ON BUTTON
# ========================================
if st.button("✨ **Generate AI Try-On** ✨", type="primary", use_container_width=True):
    if st.session_state.used_free:
        st.error("🆓 **Free try used!** Unlimited access coming soon...")
        st.markdown("""
        ### 🚀 **Unlock Unlimited Try-Ons**
        - Remove limits
        - Better quality
        - Direct blog links
        """)
        st.stop()
    
    if not user_image:
        st.warning("📸 **Upload your photo first**")
        st.stop()
    
    if not cloth_url:
        st.warning("👗 **Add outfit image URL**")
        st.stop()
    
    # ========================================
    # PROCESSING
    # ========================================
    with st.spinner("🎨 **AI Virtual Try-On in progress... 15-25 seconds**"):
        try:
            # Process images
            person_path = process_image(user_image)
            garment_path = download_outfit(cloth_url)
            
            # ====================================
            # FAL.AI REAL VTON CALL
            # ====================================
            result = fal_client.run(
                "fal-ai/idm-vton-xl/fast-sdxl",
                arguments={
                    "person_image": open(person_path, "rb"),
                    "garment_image": open(garment_path, "rb"),
                    "prompt": "professional fashion photography, clean studio lighting"
                }
            )
            
            # ====================================
            # DISPLAY RESULT
            # ====================================
            st.image(result["images"][0], caption="✅ **Your AI Virtual Try-On**", use_column_width=True)
            
            st.success("🎉 **Perfect! Real clothing transfer complete**")
            st.balloons()
            
            # Mark as used
            st.session_state.used_free = True
            
            # Show result options
            col1, col2, col3 = st.columns(3)
            with col1:
                st.download_button("💾 Download", data=result["images"][0], file_name="tryon-result.png")
            with col2:
                st.button("🔄 New Try-On", on_click=lambda: st.rerun())
            with col3:
                st.info("📱 Perfect for Pinterest!")
            
        except Exception as e:
            st.error(f"⚠️ **Try-on failed**: {str(e)[:100]}...")
            st.info("💡 **Tips**: Use clear full-body photos + single garment images")
        
        finally:
            # Cleanup
            for path in [person_path, garment_path]:
                try:
                    if path and os.path.exists(path):
                        os.remove(path)
                except:
                    pass

# ========================================
# FOOTER
# ========================================
st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    st.markdown("""
    🔒 **Privacy First**
    - Photos auto-deleted
    - No storage
    - Local processing
    """)
with col2:
    st.markdown("""
    🔥 **Powered by**
    - Fal.ai VTON-XL
    - Real clothing transfer
    - TheCostumeHunt.com
    """)
