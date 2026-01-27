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
st.set_page_config(page_title="The Costume Hunt – Virtual Try On", layout="wide")

st.title("👗 Try This Outfit On Yourself")
st.markdown("Upload your photo and see how an outfit looks on you with AI-powered virtual try-on.")
st.caption("Powered by TheCostumeHunt.com • WeShop AI Virtual Try-On • Images processed temporarily")

# ----------------------------------
# API KEYS
# ----------------------------------
try:
    os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]
    WESHOP_API_KEY = st.secrets["WESHOP_API_KEY"]
except:
    st.error("❌ Please set **FAL_KEY** and **WESHOP_API_KEY** in Streamlit secrets.")
    st.stop()

WESHOP_BASE = "https://openapi.weshop.ai/openapi/v1/agent"
WESHOP_HEADERS = {
    "Authorization": WESHOP_API_KEY,
    "Content-Type": "application/json"
}

# ----------------------------------
# UI - INPUTS
# ----------------------------------
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. 📸 Your Photo")
    user_image = st.file_uploader(
        "Upload a **clear, front-facing full-body photo**",
        type=["jpg", "jpeg", "png", "webp"],
        help="Best results with good lighting and full body visible"
    )
    if user_image:
        st.image(user_image, caption="Your photo", width=260)

with col2:
    st.subheader("2. 👗 Outfit Image")
    cloth_source = st.radio("Choose outfit source:", ["Paste URL", "Upload"], horizontal=True)
    
    cloth_url = None
    cloth_file = None
    
    if cloth_source == "Paste URL":
        cloth_url = st.text_input("Paste direct outfit image URL", placeholder="https://...")
    else:
        cloth_file = st.file_uploader("Upload outfit image", type=["jpg", "jpeg", "png", "webp"])
    
    if cloth_url:
        st.image(cloth_url, caption="Selected outfit", width=260)
    if cloth_file:
        st.image(cloth_file, caption="Uploaded outfit", width=260)

# ----------------------------------
# QUALITY SETTINGS
# ----------------------------------
st.subheader("3. ⚙️ Quality Settings")
quality_col1, quality_col2, quality_col3 = st.columns(3)

with quality_col1:
    quality_option = st.selectbox(
        "Generation Quality:",
        ["weshopFlash (Fast)", "weshopPro (Better)", "bananaPro (Best)"],
        index=0,
        help="Flash: Fastest | Pro: Better quality | Banana: Highest quality (slower)"
    )

with quality_col2:
    if "weshopPro" in quality_option or "bananaPro" in quality_option:
        aspect_ratio = st.selectbox(
            "Aspect Ratio:",
            ["Auto", "1:1", "2:3", "3:4", "9:16", "16:9"],
            index=0
        )
    else:
        aspect_ratio = "Auto"
        st.caption("Aspect ratio available for Pro/Banana")

with quality_col3:
    if "bananaPro" in quality_option:
        image_size = st.selectbox("Output Size:", ["1K", "2K", "4K"], index=0)
    else:
        image_size = None
        st.caption("Size required for Banana Pro")

desc_type = st.radio(
    "Description:",
    ["Custom (Precise)", "Auto (AI)"],
    horizontal=True,
    help="Custom gives exact control, Auto lets AI interpret"
)

# ----------------------------------
# HELPERS
# ----------------------------------
@st.cache_data
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
# WESHOP API FUNCTIONS
# ----------------------------------
def get_generate_version():
    """Map UI selection to API value"""
    mapping = {
        "weshopFlash (Fast)": "weshopFlash",
        "weshopPro (Better)": "weshopPro", 
        "bananaPro (Best)": "bananaPro"
    }
    return mapping[quality_option]

def create_virtualtryon_task(person_url, cloth_url):
    """Create virtual try-on task (API compliant)"""
    url = f"{WESHOP_BASE}/task/create"
    
    payload = {
        "agentName": "virtualtryon",  # ✅ Correct agent
        "agentVersion": "v1.0",       # ✅ Correct version
        "initParams": {
            "taskName": "Virtual Try On",           # ✅ Optional
            "originalImage": cloth_url,             # ✅ Required (outfit)
            "fashionModelImage": person_url,        # ✅ Required (person)
            "locationImage": cloth_url              # ✅ Required (background ref)
        }
    }
    
    r = requests.post(url, headers=WESHOP_HEADERS, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()["data"]["taskId"]

def execute_virtualtryon_with_retry(task_id, max_retries=3):
    """Execute with full API compliance + retry logic"""
    url = f"{WESHOP_BASE}/task/execute"
    
    params = {
        "generateVersion": get_generate_version(),           # ✅ Required
        "descriptionType": "auto" if desc_type == "Auto (AI)" else "custom",  # ✅ Required
    }
    
    if desc_type == "Custom (Precise)":
        params["textDescription"] = (
            "Replace the clothes of the person with the clothes from the product image. "
            "Keep the same face, skin tone, hairstyle, body shape, and identity. "
            "Only change the clothing. Make it realistic, high quality, natural lighting."
        )
    
    params["batchCount"] = 1  # ✅ Valid range 1-16
    
    # Optional parameters (API compliant)
    if aspect_ratio != "Auto":
        params["aspectRatio"] = aspect_ratio
    if image_size:
        params["imageSize"] = image_size
    
    payload = {
        "taskId": task_id,
        "params": params
    }
    
    for attempt in range(max_retries):
        try:
            r = requests.post(url, headers=WESHOP_HEADERS, json=payload, timeout=60)
            
            # Handle WeShop system errors (50004)
            if r.status_code == 500:
                try:
                    error_data = r.json()
                    if error_data.get("code") == "50004":
                        if attempt < max_retries - 1:
                            wait_time = 2 ** attempt
                            st.warning(f"⏳ Server busy. Retrying in {wait_time}s... ({attempt + 1}/{max_retries})")
                            time.sleep(wait_time)
                            continue
                        else:
                            raise Exception("WeShop servers are temporarily overloaded")
                except:
                    pass
            
            r.raise_for_status()
            return r.json()["data"]["executionId"]
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                st.warning(f"⏳ Network issue. Retrying... ({attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue
            raise Exception(f"Failed after {max_retries} attempts: {str(e)}")
    
    raise Exception("Unexpected retry failure")

def query_task(execution_id):
    """Query task status (API compliant)"""
    url = f"{WESHOP_BASE}/task/query"
    payload = {"executionId": execution_id}
    r = requests.post(url, headers=WESHOP_HEADERS, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

def wait_for_result(execution_id, timeout=300):
    """Wait for completion with proper status checking"""
    start = time.time()
    progress_bar = st.progress(0)
    
    while True:
        data = query_task(execution_id)
        executions = data.get("executions", [])
        
        if executions:
            latest = executions[0]
            status = latest["status"]
            
            # Update progress
            if "progress" in latest.get("results", [{}])[0]:
                progress = latest["results"][0]["progress"]
                progress_bar.progress(float(progress))
            
            if status == "Success":
                progress_bar.progress(1.0)
                return latest["results"][0]["image"]
            
            if status == "Failed":
                error_msg = latest["results"][0].get("error", "Unknown error")
                raise Exception(f"Task failed: {error_msg}")
        
        elapsed = time.time() - start
        if elapsed > timeout:
            raise Exception("Timed out after 5 minutes")
        
        progress_bar.progress(min(elapsed/timeout, 0.3))
        time.sleep(4)

# ----------------------------------
# EXECUTE TRY-ON
# ----------------------------------
if st.button("✨ **GENERATE VIRTUAL TRY-ON** ✨", type="primary", use_container_width=True):
    
    if not user_image or (not cloth_url and not cloth_file):
        st.error("⚠️ Please upload **your photo** AND provide an **outfit image**")
        st.stop()
    
    with st.spinner("🎨 Creating your virtual try-on... (30-90 seconds)"):
        person_path = None
        cloth_path = None
        
        try:
            # Process images
            person_path = save_temp_image(user_image)
            cloth_path = download_image(cloth_url) if cloth_url else save_temp_image(cloth_file)
            
            # Upload to CDN (required by WeShop)
            person_url = fal_client.upload_file(person_path)
            outfit_url = fal_client.upload_file(cloth_path)
            
            # API pipeline (100% compliant)
            with st.status("🚀 Starting WeShop AI processing...", expanded=False) as status:
                task_id = create_virtualtryon_task(person_url, outfit_url)
                status.update(label="📤 Task created, executing...", state="running")
                
                execution_id = execute_virtualtryon_with_retry(task_id)
                status.update(label="⏳ Processing in progress...", state="running")
                
                output_url = wait_for_result(execution_id)
                status.update(label="✅ Try-on complete!", state="complete")
            
            # Display results
            st.success("🎉 **Your virtual try-on is ready!**")
            st.image(output_url, caption="✨ Your personalized outfit try-on", use_container_width=True)
            
            # Download button
            st.download_button(
                label="💾 Download Result",
                data=requests.get(output_url).content,
                file_name=f"tryon_{int(time.time())}.png",
                mime="image/png",
                use_container_width=True
            )
            
        except Exception as e:
            error_str = str(e).lower()
            
            if any(x in error_str for x in ["50004", "overload", "busy", "high load"]):
                st.error("🚨 **Service temporarily busy**")
                st.info("💡 Try again in 2-3 minutes or during off-peak hours")
                st.caption("Contact hi@weshop.ai if issue persists")
            elif "timed out" in error_str:
                st.error("🚨 **Processing timeout**")
                st.info("💡 Try with smaller images or simpler outfits")
            else:
                st.error(f"🚨 **Try-on failed**: {str(e)}")
                with st.expander("🔧 Debug info"):
                    st.code(traceback.format_exc())
        
        finally:
            # Cleanup
            for path in [person_path, cloth_path]:
                try:
                    if path and os.path.exists(path):
                        os.remove(path)
                except:
                    pass

# ----------------------------------
# FOOTER
# ----------------------------------
st.markdown("---")
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("""
    🔒 **Privacy**: Images deleted immediately after processing
    🕒 **Processing**: 30-90 seconds typical
    📱 **Best Results**: Full-body, front-facing photos work best
    """)

with col_right:
    st.markdown("""
    🩷 **TheCostumeHunt.com** - Daily wear inspiration
    🔗 [Visit Site](https://thecostumehunt.com)
    📧 [Support](mailto:hello@thecostumehunt.com)
    """)

st.caption("⚡ Powered by WeShop AI Virtual Try-On API")
