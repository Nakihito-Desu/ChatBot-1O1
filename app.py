import streamlit as st
from chatbot import ChatBot
import time
import re
from PIL import Image

# Page Config
st.set_page_config(
    page_title="Smart ChatBot v2.0",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Initialize ChatBot in session state
if "bot" not in st.session_state:
    try:
        st.session_state.bot = ChatBot()
    except Exception as e:
        st.error(f"Failed to initialize ChatBot: {e}")
        st.stop()

# Initialize chat history for UI
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize processing state (Fix for KeyError)
if "processing" not in st.session_state:
    st.session_state.processing = False

# Sidebar for controls
with st.sidebar:
    st.title("🤖 SmartBot")
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.messages = []
        if "bot" in st.session_state:
            st.session_state.bot.history = []
        st.rerun()

    st.divider()

    # Persona Selector (Restored)
    st.subheader("🎭 Persona")
    selected_persona = st.selectbox(
        "Choose Character:",
        options=list(st.session_state.bot.personas.keys()),
        index=0
    )
    st.session_state.bot.set_persona(selected_persona)

    # Regenerate Button (Restored)
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        if st.button("🔄 Regenerate Response", use_container_width=True):
            st.session_state.messages.pop() # Remove last assistant message
            st.rerun()

    st.divider()

# Custom CSS for better aesthetics
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background-color: #343541;
        color: #ECECF1;
    }
    
    /* Sidebar Background */
    [data-testid="stSidebar"] {
        background-color: #202123;
    }
    
    /* Input Box */
    .stTextInput > div > div > input {
        background-color: #40414F;
        color: white;
        border: 1px solid #565869;
        border-radius: 5px;
    }
    
    /* Chat Messages */
    .stChatMessage {
        background-color: transparent;
        border: none;
    }
    
    /* User Message Background */
    [data-testid="stChatMessage"]:nth-child(odd) {
        background-color: #343541; 
    }
    
    /* Assistant Message Background */
    [data-testid="stChatMessage"]:nth-child(even) {
        background-color: #444654;
    }
    
    /* Avatar Styling */
    .stChatMessage .st-emotion-cache-1p1m4tp {
        background-color: #19c37d; /* ChatGPT Green */
        color: white;
    }
    
    /* Typography */
    h1, h2, h3, p, li {
        font-family: 'Söhne', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Ubuntu', 'Cantarell', 'Noto Sans', sans-serif;
    }
    h1 { color: #ECECF1; }
    h2 { color: #D1D5DB; }
    h3 { color: #9CA3AF; }
    p, li { color: #ECECF1; line-height: 1.6; }
    
    /* Hide Streamlit Footer (Keep Header visible for Sidebar toggle) */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    /* header {visibility: hidden;}  <- Commented out to restore sidebar toggle */
    
</style>
""", unsafe_allow_html=True)


    
# --- File Uploader Logic (Main Area) ---
# Use a key that we can increment to reset the uploader
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# Popover for a cleaner "Plus Button" feel
with st.popover("➕", help="Add attachments / เพิ่มไฟล์"):
    uploaded_file = st.file_uploader(
        "Upload Image/Excel/CSV", 
        type=['png', 'jpg', 'jpeg', 'xlsx', 'xls', 'csv'], 
        key=f"file_uploader_{st.session_state.uploader_key}"
    )

# Attachment Preview (Show what's ready to send)
if uploaded_file:
    col1, col2 = st.columns([0.1, 0.9])
    with col1:
        st.write("📎")
    with col2:
        st.caption(f"Ready to send: **{uploaded_file.name}**")
        if uploaded_file.name.split('.')[-1].lower() in ['png', 'jpg', 'jpeg']:
            st.image(uploaded_file, width=100)

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"], unsafe_allow_html=True)

# Accept user input
if prompt := st.chat_input("Send a message...", disabled=st.session_state.processing):
    # 1. Display User Message Immediately
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Check for attached file (Current State)
    temp_file = None
    temp_file_type = None
    if uploaded_file:
        file_type = uploaded_file.name.split('.')[-1].lower()
        if file_type in ['png', 'jpg', 'jpeg']:
            temp_file = Image.open(uploaded_file)
            st.session_state.messages.append({"role": "user", "content": f"*[Attached Image: {uploaded_file.name}]*"})
            with st.chat_message("user"):
                st.markdown(f"*[Attached Image: {uploaded_file.name}]*")
            temp_file_type = file_type
        else:
            # Excel/CSV
            temp_file = uploaded_file
            st.session_state.messages.append({"role": "user", "content": f"*[Attached File: {uploaded_file.name}]*"})
            with st.chat_message("user"):
                st.markdown(f"*[Attached File: {uploaded_file.name}]*")
            temp_file_type = file_type

    # 2. Generate Response Immediately (No Rerun)
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        with st.spinner("Thinking..."):
            try:
                st.session_state.processing = True
                
                # Get response from bot
                response = st.session_state.bot.get_response(
                    prompt, 
                    file_data=temp_file, 
                    file_type=temp_file_type
                )
                
                if response is None:
                    response = "I'm sorry, I don't know the answer to that yet."
                
                # Post-processing
                html_response = st.session_state.bot.reformat_text(response)
                
                # Render
                message_placeholder.markdown(html_response, unsafe_allow_html=True)
                
                # Update history
                st.session_state.messages.append({"role": "assistant", "content": html_response})
                
            except Exception as e:
                st.error(f"An error occurred: {e}")
            finally:
                st.session_state.processing = False
                # Increment uploader key for next interaction to clear it visuals eventually, 
                # but NOT forcing rerun keeps the chat snappy.
                st.session_state.uploader_key += 1
