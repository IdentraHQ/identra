import ollama

MODEL_NAME = "llama3.1"
CONTEXT_SIZE = 8192 

def start_chat():
    print(f"\n--- 📊 {MODEL_NAME} Pro Summarizer ---")
    print("INSTRUCTIONS:")
    print("1. Paste your text (it can be many paragraphs).")
    print("2. On a NEW LINE, type 'DONE' and press Enter to start the summary.")
    print("-" * 30)
    
    conversation_history = [
        {'role': 'system', 'content': "You are a precise analyst. Summarize the ENTIRE provided text with all numbers."}
    ]

    while True:
        print("\nPaste your text below (Type 'DONE' on a new line when finished):")
        
        # --- THE FIX: COLLECT MULTIPLE LINES ---
        lines = []
        while True:
            line = input()
            if line.strip().upper() == "DONE":
                break
            if line.strip().upper() in ["EXIT", "QUIT"]:
                return
            lines.append(line)
        
        user_text = "\n".join(lines)
        
        if not user_text.strip():
            print("No text detected. Try again.")
            continue

        final_prompt = f"Summarize every detail and number from this text:\n\n{user_text}"
        conversation_history.append({'role': 'user', 'content': final_prompt})

        print("\nAnalyzing Everything...", end="", flush=True)

        try:
            response = ollama.chat(
                model=MODEL_NAME,
                messages=conversation_history,
                options={'temperature': 0, 'num_ctx': CONTEXT_SIZE}
            )

            print(f"\rAI Summary:\n{response['message']['content']}\n")
            conversation_history.append({'role': 'assistant', 'content': response['message']['content']})

        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    start_chat()