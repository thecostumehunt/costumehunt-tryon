import replicate
import tempfile
import requests
from PIL import Image
from rembg import remove
import os

os.environ["REPLICATE_API_TOKEN"] = st.secrets["REPLICATE_API_TOKEN"]

def save_temp_image(file):
    img = Image.open(file).convert("RGB")
    img = remove(img)  # background cleanup
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(temp.name)
    return temp.name

def download_image(url):
    r = requests.get(url)
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    temp.write(r.content)
    return temp.name

if st.button("Try it on"):
    if not user_image or not cloth_url:
        st.warning("Please upload your photo and provide an outfit image.")
        st.stop()

    with st.spinner("Creating your try-on…"):
        person_path = save_temp_image(user_image)
        cloth_path = download_image(cloth_url)

        output = replicate.run(
            "tencentarc/try-on-diffusion",
            input={
                "person_image": open(person_path, "rb"),
                "clothing_image": open(cloth_path, "rb")
            }
        )

        st.image(output[0], caption="Your try-on result", use_container_width=True)

        os.remove(person_path)
        os.remove(cloth_path)
