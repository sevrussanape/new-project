def notes_prompt(text):
    return f"""Turn the following study material into structured notes. Use headings, concise explanations, definitions, important facts, formulas, examples, and an Exam Focus section. Do not invent information.\n\nMATERIAL:\n{text}"""

def flashcards_prompt(text, n=12):
    return f"""Create {n} useful study flashcards from this material. Format each as Q: ... A: ... Prioritize concepts, definitions, comparisons, formulas and likely exam points.\n\nMATERIAL:\n{text}"""

def quiz_prompt(text, n=10):
    return f"""Create {n} multiple-choice questions from this material. For every question provide Question, A-D, Correct and Explanation. Use only the material.\n\nMATERIAL:\n{text}"""
