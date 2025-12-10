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

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

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

# Sidebar for controls
with st.sidebar:
    st.title("🤖 SmartBot")
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.messages = []
        if "bot" in st.session_state:
            st.session_state.bot.history = []
        st.rerun()
        
    # Regenerate Button (Only show if last message is from assistant)
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        if st.button("🔄 Regenerate Response", use_container_width=True):
            st.session_state.messages.pop() # Remove last assistant message
            st.rerun() # Rerun to trigger generation
        
    st.divider()
    
    st.header("⚙️ Settings")
    
    # Persona Selector
    st.subheader("🎭 Persona")
    selected_persona = st.selectbox(
        "Choose Character:",
        options=list(st.session_state.bot.personas.keys()),
        index=0
    )
    st.session_state.bot.set_persona(selected_persona)
    
    st.divider()
    
    # Image Uploader
    st.subheader("📷 Vision")
    uploaded_file = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])
    image = None
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", use_column_width=True)

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"], unsafe_allow_html=True)

# Initialize processing state
if "processing" not in st.session_state:
    st.session_state.processing = False

# Accept user input
if prompt := st.chat_input("Send a message...", disabled=st.session_state.processing):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.processing = True
    st.rerun() # Rerun to update UI and trigger response generation

# Generate response if last message is from user
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        prompt = st.session_state.messages[-1]["content"]
        
        with st.spinner("Thinking..."):
            try:
                # Get response from bot (Pass image if exists)
                response = st.session_state.bot.get_response(prompt, image=image)
                
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
                st.session_state.processing = False
                st.rerun()
