import re

def format_response(text):
    # Current logic in app.py
    response = text
    # 1. Ensure headers have double newlines
    response = re.sub(r'(?<!\n)\n?###', '\n\n###', response)
    # 2. Ensure lists have double newlines
    response = re.sub(r'(?<!\n)\n?(\* |- |\d+\. )', '\n\n\\1', response)
    return response

def test_repro():
    # Text approximated from user screenshot
    problem_text = "สัมพันธ์ระหว่างพระเจ้ากับมนุษย์ ### รายการบัญญัติ 10 ประการ 1. อย่ามีพระเจ้าอื่นใด 2. อย่าทำรูปเคารพ 3. อย่าออกพระนาม"
    
    print("--- INPUT ---")
    print(problem_text)
    
    formatted = format_response(problem_text)
    
    print("\n--- OUTPUT ---")
    print(formatted)
    
    print("\n--- EXPECTED ---")
    print("...มนุษย์\n\n### รายการ...\n\n1. อย่า...\n\n2. อย่า...\n\n3. อย่า...")

if __name__ == "__main__":
    test_repro()
