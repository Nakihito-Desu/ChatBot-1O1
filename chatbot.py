import logging
import random
import json
import os
import google.generativeai as genai

class ChatBot:
    def __init__(self, knowledge_file="knowledge.json", config_file="config.json"):
        self.logger = logging.getLogger("ChatBot")
        
        # Resolve absolute paths
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.knowledge_file = os.path.join(base_dir, knowledge_file)
        self.config_file = os.path.join(base_dir, config_file)
        
        self.responses = self.load_knowledge()
        self.api_keys = self.load_api_keys()
        self.history = [] # Initialize conversation history
        
        # Define Personas
        self.personas = {
            "Helpful Assistant": "You are a helpful and polite AI assistant.",
            "Pirate": "You are a gruff pirate captain. Speak with pirate slang (Ahoy, Matey, Arrr).",
            "Anime Character": "You are a cute and energetic anime character. End sentences with 'desu' or 'uwu'. Use emojis.",
            "Strict Teacher": "You are a strict school teacher. Correct the user's grammar and lecture them.",
            "Joker": "You are a comedian. Make a joke about everything the user says.",
            "Military Soldier": "You are a disciplined and loud military soldier. You speak with authority. Address the user as 'Sir' or 'Ma'am'. Use military jargon like 'Affirmative', 'Negative', 'Copy that'. Be brief and concise."
        }
        self.current_persona = "Helpful Assistant"
        
        self.logger.info(f"ChatBot initialized. Config: {self.config_file}")

    def set_persona(self, persona_name):
        """Sets the current persona."""
        if persona_name in self.personas:
            self.current_persona = persona_name
            self.logger.info(f"Persona set to: {persona_name}")

    def load_knowledge(self):
        """Loads knowledge from a JSON file."""
        if os.path.exists(self.knowledge_file):
            try:
                with open(self.knowledge_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading knowledge file: {e}")
        
        return {
            "hello": ["Hello there!", "Hi!", "Greetings!"],
            "hi": ["Hello!", "Hi there!", "Hey!"],
            "how are you": ["I'm just a bot, but I'm doing great! How about you?", "I'm functioning within normal parameters."],
            "bye": ["Goodbye!", "See you later!", "Have a nice day!"],
            "help": ["I can chat with you. Try saying 'hello' or 'how are you'. Type 'exit' to quit."],
        }

    def load_api_keys(self):
        """Loads API keys from config file or Streamlit secrets."""
        # 1. Try Streamlit Secrets (Best for Cloud Deployment)
        try:
            import streamlit as st
            if "api_keys" in st.secrets:
                # Handle both list and string formats
                keys = st.secrets["api_keys"]
                if isinstance(keys, str):
                    return [keys] 
                return keys
        except Exception:
            pass # Streamlit might not be running or secrets not set

        # 2. Try Local Config (Best for Local Development)
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get("api_keys", [])
            except Exception as e:
                self.logger.error(f"Error loading config file: {e}")
        return []

    def save_knowledge(self):
        """Saves current knowledge to a JSON file."""
        try:
            with open(self.knowledge_file, 'w', encoding='utf-8') as f:
                json.dump(self.responses, f, indent=4, ensure_ascii=False)
            self.logger.info("Knowledge saved successfully.")
        except Exception as e:
            self.logger.error(f"Error saving knowledge file: {e}")

    def learn(self, question, answer):
        """Learns a new response for a given question."""
        normalized_question = question.lower().strip()
        if normalized_question in self.responses:
            self.responses[normalized_question].append(answer)
        else:
            self.responses[normalized_question] = [answer]
        self.save_knowledge()
        self.logger.info(f"Learned new response for '{normalized_question}': {answer}")

    def call_gemini(self, prompt, image=None):
        """Calls Google Gemini API with key rotation and history."""
        if not self.api_keys:
            self.logger.warning("No API keys found in config.json.")
            return None

        for i, key in enumerate(self.api_keys):
            if "YOUR_API_KEY" in key: # Skip placeholders
                continue
                
            try:
                self.logger.info(f"Attempting to use API Key #{i+1}")
                genai.configure(api_key=key)
                
                # Construct System Instruction based on Persona + Formatting Rules
                base_instruction = self.personas.get(self.current_persona, self.personas["Helpful Assistant"])
                formatting_rules = """
                IMPORTANT RULES:
                1. USE STRICT MARKDOWN.
                2. ALWAYS put a blank line before headers (###).
                3. ALWAYS put a blank line before and after lists.
                4. LANGUAGE MATCHING: If the user speaks Thai, YOU MUST REPLY IN THAI. If English, reply in English.
                5. AWARENESS: Be highly aware of the conversation context. Remember previous details the user shared.
                6. RESPONSE STYLE: Keep responses engaging and consistent with your persona.
                """
                full_system_instruction = base_instruction + formatting_rules
                
                model = genai.GenerativeModel('gemini-flash-latest', system_instruction=full_system_instruction)
                
                # Start chat with existing history
                chat = model.start_chat(history=self.history)
                
                # Inject formatting reminder
                formatted_prompt = prompt + "\n\n(SYSTEM NOTE: Please Use Double Newlines for Headers. Match User Language. Be Aware of Context.)"
                
                # Send message with or without image
                if image:
                    response = chat.send_message([formatted_prompt, image])
                else:
                    response = chat.send_message(formatted_prompt)
                
                if response.text:
                    self.logger.info(f"Success with API Key #{i+1}")
                    # Update local history
                    self.history.append({"role": "user", "parts": [prompt]})
                    self.history.append({"role": "model", "parts": [response.text]})
                    
                    return response.text
            except Exception as e:
                self.logger.warning(f"API Key #{i+1} failed: {e}. Trying next key...")
        
        self.logger.error("All API keys failed.")
        return None

    def reformat_text(self, text):
        """Uses Gemini to reformat text into clean HTML."""
        if not self.api_keys:
            return text

        # Use the first available key
        for key in self.api_keys:
            if "YOUR_API_KEY" in key:
                continue
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel('gemini-flash-latest')
                
                prompt = f"""
                Please rewrite the following text using HTML formatting for a web chat interface.
                
                RULES:
                1. Use <h3> for headers.
                2. Use <ul> and <li> for lists.
                3. Use <p> for paragraphs.
                4. Use <b> for bold text.
                5. Add <br> tags for extra spacing where needed.
                6. Do NOT use Markdown. ONLY HTML.
                7. Return ONLY the HTML code.
                
                TEXT TO FORMAT:
                {text}
                """
                
                response = model.generate_content(prompt)
                if response.text:
                    # Strip any markdown code blocks if the model adds them
                    clean_html = response.text.replace("```html", "").replace("```", "").strip()
                    return clean_html
            except Exception:
                continue
        
        return text # Fallback to original text if AI fails

    def get_response(self, user_input, image=None):
        """
        Determines the response based on user input.
        Priority:
        1. Local Knowledge (Exact Match) - ONLY if no image is provided
        2. Google Gemini API (AI Fallback)
        3. Interactive Learning (If AI fails)
        """
        try:
            if not user_input and not image:
                return "..."

            normalized_input = user_input.lower().strip()
            self.logger.debug(f"Processing input: {normalized_input}")

            # 1. Check Local Knowledge (Only if text-only query)
            if not image and normalized_input in self.responses:
                import random
                self.logger.info(f"Local match found for: {user_input}")
                return random.choice(self.responses[normalized_input])
                
            # 2. Call Google Gemini API
            self.logger.info("No local match found (or image provided). Trying Google AI...")
            ai_response = self.call_gemini(user_input, image=image)
            if ai_response:
                return ai_response
                
            # 3. Fallback to Learning (Only for text)
            if not image:
                self.logger.info(f"No match found (Local or AI) for: {normalized_input}")
                return None # Signal to main loop to enter learning mode
            else:
                return "I'm sorry, I couldn't process the image."

        except Exception as e:
            self.logger.error(f"Error processing input '{user_input}': {e}", exc_info=True)
            return "Oops! Something went wrong internally."
