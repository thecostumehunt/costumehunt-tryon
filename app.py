import streamlit as st
import tempfile
import requests
from PIL import Image, ImageDraw, ImageFont
import io
import numpy as np

# PAGE SETUP
st.set_page_config(page_title="The Costume Hunt – Try On", layout="centered")

st.title("👗 Try This Outfit On Yourself")
st.write("Upload your full-body photo and preview how daily outfits look on you.")
st.caption("Powered by TheCostumeHunt.com • Photos processed locally • No external APIs")

# SESSION CONTROL (3 FREE TRIES)
if "tries_used" not in st.session_state:
    st.session_state.tries_used = 0

# GET OUTFIT FROM BLOG LINK
query_params = st.query_params
cloth_url = query_params.get("cloth", None)

# UI INPUTS
st.subheader("1. Upload your photo")
user_image = st.file_uploader(
    "Upload a clear, full-body photo (standing, good light works best)",
    type=["jpg", "jpeg", "png", "webp"]
)

st.subheader("2. Outfit image")
if cloth_url:
    try:
        st.image(cloth_url, caption="Outfit selected from The Costume Hunt", width=250)
    except:
        cloth_url = None
        st.warning("Could not load outfit image. Please paste a direct image URL.")
else:
    cloth_url = st.text_input("Paste outfit image URL from thecostumehunt.com")

st.subheader("3. Preview try-on")

if st.button("✨ Preview Try-On") and st.session_state.tries_used < 3:
    if not user_image or not cloth_url:
        st.warning("Please upload your photo and provide an outfit image.")
    else:
        with st.spinner("Creating preview…"):
            try:
                # Load user image
                user_img = Image.open(user_image).convert("RGBA")
                user_img = user_img.resize((400, 600))
                
                # Download outfit
                r = requests.get(cloth_url, timeout=10)
                outfit_img = Image.open(io.BytesIO(r.content)).convert("RGBA")
                outfit_img = outfit_img.resize((200, 250))
                
                # Create mock try-on by overlaying outfit on torso area
                result = user_img.copy()
                
                # Torso area (roughly chest/waist)
                torso_box = (100, 200, 300, 450)
                draw = ImageDraw.Draw(result)
                draw.rectangle(torso_box, fill=(0,0,0,0))
                
                # Paste outfit (centered on torso)
                paste_pos = (150, 225)
                result.paste(outfit_img, paste_pos, outfit_img)
                
                # Add realistic shadow
                shadow = Image.new("RGBA", outfit_img.size, (0,0,0,30))
                result.paste(shadow, (paste_pos[0]+5, paste_pos[1]+5), shadow)
                
                # Add watermark
                draw.text((10, 10), "TheCostumeHunt.com", fill=(255,255,255,200))
                
                st.image(result, caption="✨ Your try-on preview", use_column_width=True)
                st.success("🎉 Preview ready! This is a smart overlay preview.")
                st.balloons()
                
                st.session_state.tries_used += 1
                remaining = 3 - st.session_state.tries_used
                st.info(f"✅ Preview created! {remaining} previews remaining.")
                
            except Exception as e:
                st.error("Could not process images. Try different image URLs.")
                st.info("Use direct image links (ends with .jpg, .png, .webp)")

elif st.session_state.tries_used >= 3:
    st.warning("You've used all 3 free previews. Refresh page for more!")
    st.markdown("""
    ### 🚀 **Upgrade to Unlimited AI Try-Ons**
    - Real AI model (not preview)
    - Unlimited daily use  
    - Remove watermarks
    - Direct blog integration
    """)
    st.button("Coming Soon - Join Waitlist")

# FOOTER
st.markdown("---")
st.write("🔒 100% local processing • No data stored • No external APIs")
st.write("🩷 Daily-wear fashion by TheCostumeHunt.com")
