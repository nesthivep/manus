import re

def is_asking_question(text: str) -> bool:
    """
    Detects if the given text is asking a question or requesting input from the user.
    
    Args:
        text: The text to analyze
        
    Returns:
        bool: True if the text appears to be asking for user input
    """
    # Check for question marks
    if "?" in text:
        return True
        
    # Common question patterns
    question_patterns = [
        r"(?i)would you like",
        r"(?i)do you want",
        r"(?i)can you",
        r"(?i)could you",
        r"(?i)please provide",
        r"(?i)please let me know",
        r"(?i)please specify",
        r"(?i)tell me",
        r"(?i)what.*(?:would|should|can|could)",
        r"(?i)how.*(?:would|should|can|could)",
        r"(?i)which.*(?:option|choice)",
        r"(?i)let me know",
        r"(?i)if you have",
        r"(?i)if you would like",
    ]
    
    for pattern in question_patterns:
        if re.search(pattern, text):
            return True
            
    return False

# Test examples from the logs
test_texts = [
    "Hello! How can I assist you today? If you have any tasks or questions, feel free to let me know!",
    "It seems that you've shared some information about the tools and guidelines for interacting with the system. If you have any specific tasks or questions in mind, please let me know how I can assist you!",
    "It seems that the same information has been repeated once again. If you have a specific question or task you'd like assistance with, please let me know! I'm here to help with any inquiries or tasks you may have.",
    "This is a test string without any question pattern.",
    "Do you want to create a file?"
]

for i, text in enumerate(test_texts):
    result = is_asking_question(text)
    print(f"Text {i+1}: {'IS' if result else 'is NOT'} a question")
    print(f"Text: {text}\n") 