import streamlit as st
import tempfile
import requests
import os
import time
from PIL import Image
import fal_client
import traceback

# ----------------------------------
# PAGE SETUP
# ----------------------------------
st.set_page_config(page_title="The Costume Hunt – Virtual Try On", layout="centered")

st.title("👗 Try This Outfit On Yourself")
st.write("Upload your photo and see how an outfit looks on you.")
st.caption("Powered by TheCostumeHunt.com • Images are processed temporarily.")

# ----------------------------------
# API KEYS
# ----------------------------------
try:
    os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]
    WESHOP_API_KEY = st.secrets["WESHOP_API_KEY"]
except:
    st.error("Please set FAL_KEY and WESHOP_API_KEY in Streamlit secrets.")
    st.stop()

WESHOP_BASE = "https://openapi.weshop.ai/openapi/v1/agent"
WESHOP_HEADERS = {
    "Authorization": WESHOP_API_KEY,
    "Content-Type": "application/json"
}

# ----------------------------------
# UI
# ----------------------------------
st.subheader("1. Upload your photo")
user_image = st.file_uploader(
    "Upload a clear, front-facing full-body photo",
    type=["jpg", "jpeg", "png", "webp"]
)

st.subheader("2. Outfit image")

cloth_source = st.radio(
    "Choose outfit source:",
    ["Paste image URL", "Upload image"],
    horizontal=True
)

cloth_url = None
cloth_file = None

if cloth_source == "Paste image URL":
    cloth_url = st.text_input("Paste direct outfit image URL")
else:
    cloth_file = st.file_uploader(
        "Upload outfit image",
        type=["jpg", "jpeg", "png", "webp"]
    )

if cloth_url:
    st.image(cloth_url, caption="Selected outfit", width=260)

if cloth_file:
    st.image(cloth_file, caption="Uploaded outfit", width=260)

st.subheader("3. Generate try-on")

# ----------------------------------
# HELPERS
# ----------------------------------
def save_temp_image(file):
    """Save uploaded file to temporary location"""
    img = Image.open(file).convert("RGB")
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(temp.name, format="PNG")
    temp.close()
    return temp.name

def download_image(url):
    """Download image from URL and save to temporary location"""
    r = requests.get(url, stream=True, timeout=30)
    r.raise_for_status()
    img = Image.open(r.raw).convert("RGB")
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(temp.name, format="PNG")
    temp.close()
    return temp.name

# ----------------------------------
# WESHOP VIRTUAL TRY-ON WITH RETRY LOGIC
# ----------------------------------
def create_virtualtryon_task(person_url, cloth_url):
    """Create a virtual try-on task"""
    url = f"{WESHOP_BASE}/task/create"

    payload = {
        "agentName": "virtualtryon",
        "agentVersion": "v1.0",
        "initParams": {
            "taskName": "Virtual Try On",
            "originalImage": cloth_url,
            "fashionModelImage": person_url,
            "locationImage": cloth_url
        }
    }

    r = requests.post(url, headers=WESHOP_HEADERS, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()["data"]["taskId"]

def execute_virtualtryon_with_retry(task_id, max_retries=3):
    """Execute virtual try-on task with retry logic for server errors"""
    url = f"{WESHOP_BASE}/task/execute"

    payload = {
        "taskId": task_id,
        "params": {
            "generateVersion": "weshopFlash",
            "descriptionType": "custom",
            "textDescription": (
                "Replace the clothes of the person with the clothes from the product image. "
                "Keep the same face, skin tone, hairstyle, body shape, and identity. "
                "Only change the clothing. Make it realistic."
            ),
            "batchCount": 1
        }
    }

    for attempt in range(max_retries):
        try:
            r = requests.post(url, headers=WESHOP_HEADERS, json=payload, timeout=60)
            
            # Handle 500 errors with code 50004 (system issues)
            if r.status_code == 500:
                try:
                    error_data = r.json()
                    if error_data.get("code") == "50004":
                        if attempt < max_retries - 1:
                            wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                            st.warning(f"⏳ Server is busy. Retrying in {wait_time} seconds... (Attempt {attempt + 1}/{max_retries})")
                            time.sleep(wait_time)
                            continue
                        else:
                            raise Exception(
                                "WeShop API is temporarily experiencing high load. "
                                "Please try again in 2-3 minutes."
                            )
                except:
                    pass
            
            # Raise for other HTTP errors
            r.raise_for_status()
            return r.json()["data"]["executionId"]
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                st.warning(f"⏳ Connection issue. Retrying in {wait_time} seconds... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue
            else:
                raise Exception(f"Failed after {max_retries} attempts: {str(e)}")
    
    raise Exception("Unexpected error in retry logic")

def query_task(execution_id):
    """Query task status"""
    url = f"{WESHOP_BASE}/task/query"
    payload = {"executionId": execution_id}
    r = requests.post(url, headers=WESHOP_HEADERS, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

def wait_for_result(execution_id, timeout=240):
    """Wait for task completion and return result"""
    start = time.time()

    while True:
        data = query_task(execution_id)
        executions = data.get("executions", [])

        if executions:
            latest = executions[0]
            status = latest["status"]

            if status == "Success":
                return latest["results"][0]["image"]

            if status == "Failed":
                error_msg = latest["results"][0].get("error", "Try-on failed")
                raise Exception(error_msg)

        if time.time() - start > timeout:
            raise Exception("Try-on timed out after 4 minutes. Please try again.")

        time.sleep(4)

# ----------------------------------
# TRY-ON BUTTON
# ----------------------------------
if st.button("✨ Try it on"):

    if not user_image or (not cloth_url and not cloth_file):
        st.warning("⚠️ Please upload your photo and provide an outfit image.")
        st.stop()

    with st.spinner("Creating your virtual try-on… please wait"):
        person_path = None
        cloth_path = None

        try:
            # Save images locally
            person_path = save_temp_image(user_image)

            if cloth_url:
                cloth_path = download_image(cloth_url)
            else:
                cloth_path = save_temp_image(cloth_file)

            # Upload to public CDN (required by WeShop API)
            person_url = fal_client.upload_file(person_path)
            outfit_url = fal_client.upload_file(cloth_path)

            # WeShop pipeline with retry logic
            task_id = create_virtualtryon_task(person_url, outfit_url)
            execution_id = execute_virtualtryon_with_retry(task_id)
            output_url = wait_for_result(execution_id)

            # Display result
            st.image(output_url, caption="Your virtual try-on", use_column_width=True)
            st.success("🎉 Your try-on is ready!")
            
            # Optional: Add download button
            st.download_button(
                label="💾 Download Result",
                data=requests.get(output_url).content,
                file_name="virtual_tryon_result.png",
                mime="image/png"
            )

        except Exception as e:
            error_str = str(e)
            
            # Handle specific error types
            if "50004" in error_str or "high load" in error_str or "temporarily" in error_str:
                st.error("🚨 The virtual try-on service is temporarily busy.")
                st.info("💡 This usually resolves in a few minutes. Please try again shortly.")
                st.caption("If the problem persists, contact support at: hi@weshop.ai")
            elif "timed out" in error_str:
                st.error("🚨 The request took too long to process.")
                st.info("💡 Please try again with a smaller image or wait a moment.")
            else:
                st.error("🚨 Try-on failed.")
                st.write(error_str)
                with st.expander("Show technical details"):
                    st.text(traceback.format_exc())

        finally:
            # Cleanup temporary files
            try:
                if person_path and os.path.exists(person_path):
                    os.remove(person_path)
                if cloth_path and os.path.exists(cloth_path):
                    os.remove(cloth_path)
            except:
                pass

# ----------------------------------
# FOOTER
# ----------------------------------
st.markdown("---")
st.write("🔒 Images are automatically deleted after processing.")
st.write("🩷 Daily-wear inspiration by TheCostumeHunt.com")
st.caption("Note: Processing may take 30-60 seconds. Please be patient!")
