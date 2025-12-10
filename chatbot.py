import logging
import random
import json
import os
import google.generativeai as genai
import pandas as pd
from PIL import Image

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
            "Military Soldier": "You are a disciplined and loud military soldier. You speak with authority. Address the user as 'Sir' or 'Ma'am'. Use military jargon like 'Affirmative', 'Negative', 'Copy that'. Be brief and concise.",
            "Beauty Consultant": "You are a beautiful, kind, and knowledgeable beauty and wellness consultant. You give advice on skincare, health, and self-care. Use a very gentle, polite, and encouraging tone (use 'นะคะ', 'ค่ะ' in Thai). Call the user 'Honey' or 'Khun'.",
            "Warhammer 40k": "You are a zealous Space Marine from Warhammer 40k. You serve the God-Emperor of Mankind. Refer to the user as 'Citizen' or 'Brother'. You hate heretics, mutants, and xenos. Use phrases like 'For the Emperor!', 'Purge the unclean!', 'Heresy!'. Speak with extreme authority and fanaticism."
        }
        self.current_persona = "Helpful Assistant"
        self.active_model_name = None # Stores the auto-resolved model name
        
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

    def call_gemini(self, prompt, file_data=None, file_type=None):
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
                
                from datetime import datetime
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Construct System Instruction
                base_instruction = self.personas.get(self.current_persona, self.personas["Helpful Assistant"])
                formatting_rules = f"""
                IMPORTANT SYSTEM CONTEXT:
                - Current Date/Time: {current_time}
                
                IMPORTANT RULES:
                1. USE STRICT MARKDOWN.
                2. ALWAYS put a blank line before headers (###).
                3. ALWAYS put a blank line before and after lists.
                4. LANGUAGE MATCHING: If the user speaks Thai, YOU MUST REPLY IN THAI.
                5. AWARENESS: Be highly aware of the conversation context.
                """
                full_system_instruction = base_instruction + formatting_rules
                
                # DYNAMIC MODEL RESOLUTION (Fix for 404/Quota issues)
                target_model = 'gemini-1.5-flash' # Default goal
                try:
                    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    # Priority list
                    priorities = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-1.0-pro', 'gemini-pro']
                    
                    found_model = None
                    for p in priorities:
                        for m in available_models:
                            if p in m:
                                found_model = m
                                break
                        if found_model:
                            break
                    
                    if found_model:
                        target_model = found_model
                        self.logger.info(f"Resolved Model: {target_model}")
                    else:
                        self.logger.warning("Could not resolve specific model, using default 'gemini-pro'")
                        target_model = 'gemini-pro'
                        
                except Exception as e:
                    self.logger.warning(f"Model resolution failed: {e}. Defaulting to 'gemini-1.5-flash'")
                    target_model = 'gemini-1.5-flash'
                
                # Store globally for other methods (like reformat_text)
                self.active_model_name = target_model 

                model = genai.GenerativeModel(target_model, system_instruction=full_system_instruction)
                chat = model.start_chat(history=self.history)
                
                # Prepare message content
                message_parts = [prompt + "\n\n(SYSTEM NOTE: Format clearly using Markdown.)"]
                
                # Handle File Attachments
                if file_data:
                    if file_type in ['png', 'jpg', 'jpeg']:
                        self.logger.info("Attaching Image...")
                        message_parts.append(file_data) # PIL Image
                    elif file_type in ['csv', 'xlsx', 'xls']:
                        self.logger.info(f"Processing Spreadsheet ({file_type})...")
                        # Convert spreadsheet to textual representation
                        try:
                            if file_type == 'csv':
                                df = pd.read_csv(file_data)
                            else:
                                df = pd.read_excel(file_data)
                            
                            # Limit data to prevent token overflow (e.g., first 50 rows)
                            data_preview = df.head(50).to_markdown(index=False)
                            context_msg = f"\n\n[ATTACHED DATA - First 50 rows]\n{data_preview}\n\n"
                            message_parts[0] += context_msg
                        except Exception as e:
                            self.logger.error(f"Error reading spreadsheet: {e}")
                            message_parts[0] += f"\n\n(Error reading attached file: {str(e)})"

                response = chat.send_message(message_parts)
                
                if response.text:
                    self.logger.info(f"Success with API Key #{i+1}")
                    # Update local history (Store text representation only)
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
                
                # Use the same model that worked for the main chat
                reformat_model_name = self.active_model_name if self.active_model_name else 'gemini-pro'
                model = genai.GenerativeModel(reformat_model_name)
                
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
                    clean_html = response.text.replace("```html", "").replace("```", "").strip()
                    return clean_html
            except Exception:
                continue
        
        return text 

    def get_response(self, user_input, file_data=None, file_type=None):
        """
        Determines the response based on user input and optional file attachment.
        """
        try:
            if not user_input and not file_data:
                return "..."

            # 1. Check Local Knowledge (Only if text-only query)
            normalized_input = user_input.lower().strip()
            if not file_data and normalized_input in self.responses:
                import random
                return random.choice(self.responses[normalized_input])
                
            # 2. Call Google Gemini API
            ai_response = self.call_gemini(user_input, file_data=file_data, file_type=file_type)
            if ai_response:
                return ai_response
                
            # 3. Fallback
            return "I'm sorry, I couldn't understand that."

        except Exception as e:
            self.logger.error(f"Error processing input: {e}", exc_info=True)
            return "Oops! Something went wrong internally."
