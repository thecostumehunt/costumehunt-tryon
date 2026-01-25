import streamlit as st

st.set_page_config(page_title="The Costume Hunt – Try On", layout="centered")

st.title("👗 Try This Outfit On Yourself")
st.write("Upload your full-body photo and preview how daily outfits look on you.")

# Read clothing image from URL parameter
query_params = st.query_params
cloth_url = query_params.get("cloth", None)

st.subheader("1. Upload your photo")
user_image = st.file_uploader("Upload a clear full-body photo", type=["jpg", "jpeg", "png"])

st.subheader("2. Outfit image")
if cloth_url:
    st.image(cloth_url, caption="Selected outfit from The Costume Hunt", width=250)
else:
    cloth_url = st.text_input("Paste outfit image URL from thecostumehunt.com")

st.subheader("3. Generate try-on")

if st.button("Try it on"):
    if not user_image or not cloth_url:
        st.warning("Please upload your photo and provide an outfit image.")
    else:
        st.success("✅ App is working. AI try-on will be added here next.")
        st.image(user_image, caption="Your uploaded photo", width=250)
        st.image(cloth_url, caption="Outfit image", width=250)

st.markdown("---")
st.caption("Powered by TheCostumeHunt.com • Photos are not stored.")
