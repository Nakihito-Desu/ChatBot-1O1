import streamlit as st
from chatbot import ChatBot
import time
import re
from PIL import Image

# Page Config
st.set_page_config(
    page_title="Smart ChatBot v2.0",
    page_icon="🤖",
    layout="centered"
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

    # Chat History Summary (New Feature)
    st.subheader("🕑 History Log")
    if st.session_state.messages:
        for i, msg in enumerate(st.session_state.messages):
            if msg["role"] == "user":
                # Show first 20 chars of user messages
                st.caption(f"You: {msg['content'][:20]}...")
    else:
        st.caption("No history yet.")

    st.divider()

    st.header("⚙️ Settings")
    
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
    
    /* Hide Streamlit Header/Footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
</style>
""", unsafe_allow_html=True)


    
# --- File Uploader Logic (Main Area) ---
# Use a key that we can increment to reset the uploader
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

with st.expander("📎 Attach File / แนบไฟล์ (Image, Excel, CSV)", expanded=False):
    uploaded_file = st.file_uploader(
        "Upload a file", 
        type=['png', 'jpg', 'jpeg', 'xlsx', 'xls', 'csv'], 
        key=f"file_uploader_{st.session_state.uploader_key}"
    )

# Accept user input
if prompt := st.chat_input("Send a message...", disabled=st.session_state.processing):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Check for attached file
    if uploaded_file:
        file_type = uploaded_file.name.split('.')[-1].lower()
        if file_type in ['png', 'jpg', 'jpeg']:
            image = Image.open(uploaded_file)
            st.session_state.messages.append({"role": "user", "content": f"*[Attached Image: {uploaded_file.name}]*"})
            # Store temporarily for processing
            st.session_state.temp_file = image
            st.session_state.temp_file_type = file_type
        else:
            # Excel/CSV
            st.session_state.messages.append({"role": "user", "content": f"*[Attached File: {uploaded_file.name}]*"})
            st.session_state.temp_file = uploaded_file
            st.session_state.temp_file_type = file_type
    else:
        st.session_state.temp_file = None
        st.session_state.temp_file_type = None

    st.session_state.processing = True
    st.rerun() 

# Generate response if last message is from user
# We need to detect if we should generate. 
# Logic: If last msg is user OR (second to last is user and last is attachment note).
# Actually, we appending prompt THEN attachment note above. So last msg is attachment note if file exists.
# If no file, last msg is prompt.
# Detection logic:
should_generate = False
if st.session_state.messages:
    last_msg = st.session_state.messages[-1]
    if last_msg["role"] == "user":
        should_generate = True

if should_generate:
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # Find the actual text prompt (it might be the last message, or the one before the attachment note)
        user_text = "..."
        for msg in reversed(st.session_state.messages):
            if msg["role"] == "user" and not msg["content"].startswith("*[Attached"):
                user_text = msg["content"]
                break
        
        with st.spinner("Thinking..."):
            try:
                # Get response from bot
                response = st.session_state.bot.get_response(
                    user_text, 
                    file_data=st.session_state.get("temp_file"), 
                    file_type=st.session_state.get("temp_file_type")
                )
                
                # Handle "I don't know" case
                if response is None:
                    response = "I'm sorry, I don't know the answer to that yet."
                
                # Post-processing: AI REFORMATTING (HTML Strategy)
                html_response = st.session_state.bot.reformat_text(response)
                
                # Render HTML directly
                message_placeholder.markdown(html_response, unsafe_allow_html=True)
                
                # Add assistant message to chat history
                st.session_state.messages.append({"role": "assistant", "content": html_response})
                
            except Exception as e:
                st.error(f"An error occurred: {e}")
                response = "Error generating response."
            finally:
                # Clean up logic
                st.session_state.temp_file = None
                st.session_state.temp_file_type = None
                st.session_state.processing = False
                
                # Reset uploader by incrementing key
                st.session_state.uploader_key += 1
                st.rerun()
