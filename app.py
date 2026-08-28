import streamlit as st
import json
import os
import re
from github import Github

# Setup layout and styling
st.set_page_config(page_title="Cloud Focus Tracker", layout="wide")
st.title("🎯 My Cloud Focus Playlist")

# --- GITHUB CLOUD STORAGE SETUP ---
# Securely connect to your GitHub account using secret tokens
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
REPO_NAME = st.secrets.get("REPO_NAME", "")

def load_progress_from_cloud():
    # If not on the web yet, read locally
    if not GITHUB_TOKEN or not REPO_NAME:
        if os.path.exists("progress.json"):
            with open("progress.json", "r") as f:
                return json.load(f)
        return {}
    
    # If on the web, fetch directly from GitHub repository
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        file_content = repo.get_contents("progress.json", ref="main")
        return json.loads(file_content.decoded_content.decode())
    except:
        return {}

def save_progress_to_cloud(data):
    # Save locally first
    with open("progress.json", "w") as f:
        json.dump(data, f)
        
    # If on the web, push the update directly up to GitHub
    if GITHUB_TOKEN and REPO_NAME:
        try:
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(REPO_NAME)
            try:
                contents = repo.get_contents("progress.json", ref="main")
                repo.update_file(contents.path, "Update progress data", json.dumps(data), contents.sha, branch="main")
            except:
                repo.create_file("progress.json", "Create progress data", json.dumps(data), branch="main")
        except Exception as e:
            st.error(f"Cloud Save Failed: {e}")

# --- PLAYLIST PROCESSING ---
def get_video_id(url):
    match = re.search(r'(?:v=|\/embed\/|\/1\/|\/v\/|https:\/\/youtu\.be\/)([^"&?\/\s]{11})', url)
    return match.group(1) if match else None

if not os.path.exists("playlist.txt") or os.path.getsize("playlist.txt") == 0:
    with open("playlist.txt", "w") as f:
        f.write("https://youtube.com\n")

videos = []
with open("playlist.txt", "r") as f:
    for line in f:
        url = line.strip()
        if url:
            v_id = get_video_id(url)
            if v_id:
                videos.append({"url": url, "id": v_id})

progress_data = load_progress_from_cloud()

for v in videos:
    if v["id"] not in progress_data:
        progress_data[v["id"]] = {"completed": False, "saved_seconds": 0}

# --- SIDEBAR INTERFACE ---
st.sidebar.header("📋 Video List")
total_videos = len(videos)
completed_videos = sum(1 for v in videos if progress_data[v["id"]]["completed"])
completion_rate = completed_videos / total_videos if total_videos > 0 else 0

st.sidebar.write(f"**Overall Progress: {completed_videos}/{total_videos}**")
st.sidebar.progress(completion_rate)
st.sidebar.write("---")

if "current_index" not in st.session_state:
    st.session_state.current_index = 0

for i, video in enumerate(videos):
    status = "✅" if progress_data[video["id"]]["completed"] else "⬜"
    button_label = f"▶️ {status} Video {i+1}" if i == st.session_state.current_index else f"{status} Video {i+1}"
    if st.sidebar.button(button_label, key=f"btn_{video['id']}"):
        st.session_state.current_index = i

# --- MAIN FOCUS SCREEN ---
active_video = videos[st.session_state.current_index]
video_state = progress_data[active_video["id"]]
current_start_time = video_state.get("saved_seconds", 0)

minutes = current_start_time // 60
seconds = current_start_time % 60
if current_start_time > 0:
    st.info(f"⏳ Resuming video from **{minutes}m {seconds}s**")

st.video(active_video["url"], start_time=current_start_time)
st.write("---")

# --- SAVE CONTROLS ---
st.subheader("⏱️ Save Your Playback Position")
col1, col2, col3 = st.columns()
with col1:
    input_minutes = st.number_input("Minutes", min_value=0, max_value=600, value=int(minutes), step=1)
with col2:
    input_seconds = st.number_input("Seconds", min_value=0, max_value=59, value=int(seconds), step=1)
with col3:
    st.write(" ")
    st.write(" ")
    if st.button("💾 Lock current time position", use_container_width=True):
        total_seconds = (input_minutes * 60) + input_seconds
        progress_data[active_video["id"]]["saved_seconds"] = total_seconds
        save_progress_to_cloud(progress_data)
        st.toast("✅ Time saved directly to the cloud tracker!", icon="💾")
        st.rerun()

st.write("---")
is_done = video_state["completed"]
if st.button("🎉 Mark Video as Completely Finished" if not is_done else "🔄 Reset Video to Uncompleted", type="primary"):
    progress_data[active_video["id"]]["completed"] = not is_done
    if not is_done:
        progress_data[active_video["id"]]["saved_seconds"] = 0
    save_progress_to_cloud(progress_data)
    st.rerun()
