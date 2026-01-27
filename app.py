import streamlit as st
import requests
import time
import os
import tempfile
from PIL import Image
import fal_client
import traceback

# Page setup
st.set_page_config(page_title="Virtual Try-On", layout="wide")
st.title("👗 Virtual Try-On - Fixed Version")
st.markdown("Upload your photo + outfit → See instant results")

# API Configuration
@st.cache_resource
def get_api_config():
    try:
        os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]
        WESHOP_API_KEY = st.secrets["WESHOP_API_KEY"]
        return {
            "key": WESHOP_API_KEY,
            "base": "https://openapi.weshop.ai/openapi/v1/agent",
            "headers": {
                "Authorization": WESHOP_API_KEY,
                "Content-Type": "application/json"
            }
        }
    except:
        st.error("❌ Add FAL_KEY and WESHOP_API_KEY to Streamlit secrets")
        st.stop()

config = get_api_config()

# UI Layout
col1, col2 = st.columns(2)

with col1:
    st.subheader("🧍 Your Photo")
    person_file = st.file_uploader("Upload **your photo** (full body, front-facing)", 
                                  type=['png','jpg','jpeg'], key="person")
    
with col2:
    st.subheader("👗 Outfit Photo") 
    cloth_file = st.file_uploader("Upload **outfit image** (model wearing clothes)", 
                                 type=['png','jpg','jpeg'], key="cloth")

# Quality settings
st.subheader("⚙️ Settings")
quality = st.selectbox("Quality", ["Fast", "Pro"], index=0)
desc_type = st.radio("AI Mode", ["Auto", "Precise"], horizontal=True)

# Helper functions
def save_image(file):
    img = Image.open(file).convert('RGB')
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    img.save(temp_file.name)
    temp_file.close()
    return temp_file.name

def upload_to_cdn(local_path):
    """Upload to fal.ai CDN for WeShop"""
    with open(local_path, 'rb') as f:
        url = fal_client.upload_file(f.name)
    return url

# FIXED WeShop API Functions
def create_task(person_url, cloth_url):
    """Create task with **aimodel** agent (CORRECT agent)"""
    url = f"{config['base']}/task/create"
    
    payload = {
        "agentName": "aimodel",  # ✅ FIXED: Use aimodel, not virtualtryon
        "agentVersion": "v1.0",
        "initParams": {
            "taskName": "TryOn Task",
            "originalImage": cloth_url  # Outfit as original
        }
    }
    
    resp = requests.post(url, json=payload, headers=config['headers'], timeout=30)
    st.write("**Task Creation Response:**", resp.json())  # DEBUG
    
    if resp.status_code == 200:
        return resp.json()["data"]["taskId"]
    raise Exception(f"Task creation failed: {resp.text}")

def execute_task(task_id):
    """Execute with **CORRECT** aimodel parameters"""
    url = f"{config['base']}/task/execute"
    
    params = {
        "generatedContent": "freeCreation",
        "maskType": "autoApparelSegment",  # Keep clothing, change model
        "fashionModelId": None,  # We'll test without first
        "pose": "freePose",
        "batchCount": 1
    }
    
    payload = {"taskId": task_id, "params": params}
    
    resp = requests.post(url, json=payload, headers=config['headers'], timeout=60)
    st.write("**Execute Response:**", resp.json())  # DEBUG
    
    if resp.status_code == 200:
        return resp.json()["data"]["executionId"]
    raise Exception(f"Execute failed: {resp.text}")

def poll_task(execution_id, max_wait=300):
    """Poll until result with FULL DEBUG"""
    url = f"{config['base']}/task/query"
    
    start_time = time.time()
    progress_bar = st.progress(0)
    
    while time.time() - start_time < max_wait:
        payload = {"executionId": execution_id}
        resp = requests.post(url, json=payload, headers=config['headers'], timeout=20)
        data = resp.json()
        
        # FULL DEBUG OUTPUT
        with st.expander("🔍 **RAW API RESPONSE** (Click to see)"):
            st.json(data)
        
        # Parse executions
        executions = data.get("executions", [])
        if executions:
            exec_data = executions[0]
            status = exec_data.get("status")
            results = exec_data.get("results", [])
            
            st.write(f"**Status:** {status}")
            
            # Update progress
            if results and "progress" in results[0]:
                progress = float(results[0]["progress"])
                progress_bar.progress(progress)
                st.write(f"**Progress:** {progress*100:.0f}%")
            
            # SUCCESS - Extract ALL images
            if status == "Success" and results:
                images = []
                for i, result in enumerate(results):
                    if "image" in result:
                        img_url = result["image"]
                        images.append(img_url)
                        st.write(f"**✅ IMAGE {i+1} FOUND:** {img_url}")
                        
                        # Test download
                        try:
                            img_resp = requests.head(img_url, timeout=10)
                            st.success(f"✅ Image {i+1} accessible (Status: {img_resp.status_code})")
                        except:
                            st.error(f"❌ Image {i+1} not accessible")
                
                progress_bar.progress(1.0)
                return images
        
        elif status == "Failed":
            error = results[0].get("error", "Unknown error")
            raise Exception(f"Task failed: {error}")
        
        time.sleep(3)
        progress_bar.progress(min((time.time()-start_time)/max_wait, 0.9))
    
    raise Exception("Timeout - no result after 5 minutes")

# MAIN EXECUTION
if st.button("🚀 **GENERATE TRY-ON**", type="primary", use_container_width=True):
    if not person_file or not cloth_file:
        st.error("⚠️ Upload **BOTH** photos")
        st.stop()
    
    with st.spinner("🎨 Processing..."):
        try:
            # Save local files
            person_path = save_image(person_file)
            cloth_path = save_image(cloth_file)
            
            # Upload to CDN
            st.info("📤 Uploading to CDN...")
            person_url = upload_to_cdn(person_path)
            cloth_url = upload_to_cdn(cloth_path)
            
            st.success(f"✅ Person: {person_url}")
            st.success(f"✅ Outfit: {cloth_url}")
            
            # WeShop Pipeline
            with st.status("🤖 WeShop AI Processing", expanded=True) as status:
                status.update(label="📋 Creating task...", state="running")
                task_id = create_task(person_url, cloth_url)
                
                status.update(label="⚡ Executing AI...", state="running")
                exec_id = execute_task(task_id)
                
                status.update(label="⏳ Waiting for result...", state="running")
                image_urls = poll_task(exec_id)
            
            # DISPLAY RESULTS
            st.success("🎉 **RESULTS READY!**")
            
            for i, img_url in enumerate(image_urls):
                st.subheader(f"✨ **Result {i+1}**")
                st.image(img_url, use_container_width=True)
                
                # Download button
                try:
                    img_data = requests.get(img_url, timeout=30).content
                    st.download_button(
                        label=f"💾 Download Image {i+1}",
                        data=img_data,
                        file_name=f"tryon_result_{i+1}.png",
                        mime="image/png"
                    )
                except Exception as e:
                    st.error(f"❌ Download failed for image {i+1}: {e}")
            
        except Exception as e:
            st.error(f"🚨 **Failed**: {str(e)}")
            st.error("Check the debug expander above for API responses")
            
            with st.expander("Full Error"):
                st.code(traceback.format_exc())
        
        finally:
            # Cleanup
            for path in [person_path, cloth_path]:
                try:
                    if path and os.path.exists(path):
                        os.unlink(path)
                except: pass

# Footer
st.markdown("---")
st.caption("🔧 **Debug Mode**: Raw API responses shown in expanders")
st.caption("✅ **Fixed**: Uses `aimodel` agent + full response parsing")
