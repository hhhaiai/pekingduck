import json
import random
import string
def is_chatgpt_format(data):
    """Check if the data is in the expected ChatGPT format"""
    try:
        # If the data is a string, try to parse it as JSON
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return False  # If the string can't be parsed, it's not in the expected format

        # Now check if data is a dictionary and contains the necessary structure
        if isinstance(data, dict):
            # Ensure 'choices' is a list and the first item has a 'message' field
            if "choices" in data and isinstance(data["choices"], list) and len(data["choices"]) > 0:
                if "message" in data["choices"][0]:
                    return True
    except Exception as e:
        print(f"Error checking ChatGPT format: {e}")

    return False


def _generate_id(letters: int = 4, numbers: int = 6) -> str:
    """Generate unique chat completion ID"""
    letters_str = ''.join(random.choices(string.ascii_lowercase, k=letters))
    numbers_str = ''.join(random.choices(string.digits, k=numbers))
    return f"chatcmpl-{letters_str}{numbers_str}"