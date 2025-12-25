
import google.generativeai as genai
import os

os.environ["GEMINI_API_KEY"] = "YOUR_GEMINI_API_KEY_HERE"
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

print("Listing available models...")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)
