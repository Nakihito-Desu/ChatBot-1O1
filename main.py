import sys
from chatbot import ChatBot
from utils import setup_logging

def main():
    # 1. Setup Logging
    logger = setup_logging()
    logger.info("Application started.")

    # 2. Initialize ChatBot
    try:
        bot = ChatBot()
    except Exception as e:
        logger.critical(f"Failed to initialize ChatBot: {e}", exc_info=True)
        print("Critical Error: Could not start ChatBot. Check logs for details.")
        sys.exit(1)

    print("=========================================")
    print("      Smart ChatBot v2.0 (Learning)      ")
    print("      Type 'exit' or 'quit' to stop      ")
    print("=========================================")

    # 3. Main Loop
    while True:
        try:
            user_input = input("You: ")
            
            if user_input.lower() in ["exit", "quit"]:
                print("Bot: Goodbye!")
                logger.info("User requested exit.")
                break

            response = bot.get_response(user_input)
            
            if response:
                print(f"Bot: {response}")
            else:
                # Learning Flow
                print("Bot: I don't know how to answer that yet.")
                new_answer = input("Bot: How should I respond? (or type 'skip' to skip): ")
                
                if new_answer.lower() != 'skip':
                    bot.learn(user_input, new_answer)
                    print("Bot: Thanks! I've learned that now.")
                else:
                    print("Bot: Okay, I'll skip learning that for now.")

        except KeyboardInterrupt:
            print("\nBot: Forced exit. Goodbye!")
            logger.warning("Application interrupted by user (KeyboardInterrupt).")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
            print("Bot: An unexpected error occurred. Please try again.")

    logger.info("Application finished.")

if __name__ == "__main__":
    main()
