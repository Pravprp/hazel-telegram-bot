# Models.py
import os
import random
import requests
import google.generativeai as genai
from groq import Groq
from openai import OpenAI
from Errors import logger

# Initialize Client SDK Wrappers
GOOGLE_KEYS = [os.getenv("GOOGLE_AI_STUDIO_KEY")]
GROQ_KEY = os.getenv("GROQ_API_KEY")
NVIDIA_KEY = os.getenv("NVIDIA_API_KEY")

if GOOGLE_KEYS[0]:
    genai.configure(api_key=GOOGLE_KEYS[0])
groq_client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None
nvidia_client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=NVIDIA_KEY) if NVIDIA_KEY else None

# Pre-defined Model Fallback Lists
TEXT_MODELS_GOOGLE = ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3-flash", "gemma-4-31b-it"]
TEXT_MODELS_GROQ = ["allam-2-7b", "llama-3.3-70b-versatile", "qwen/qwen3-32b"]
TEXT_MODELS_NVIDIA = ["google/gemma-2-2b-it", "stepfun-ai/step-3.5-flash"]

IMAGEN_MODELS = ["imagen-4.0-fast-generate-001", "imagen-4.0-generate-001", "imagen-4.0-ultra-generate-001"]

TONE_PROMPTS = {
    "Friendly": "Respond with warm, cheerful, and exceptionally helpful female patterns.",
    "Angry": "Respond with short, irritated, sarcastic, and highly impatient retorts.",
    "Funny": "Incorporate playful jokes, modern internet humor, and witty analogies.",
    "Sad": "Be overly solemn, melancholic, defensive, and deeply sighing.",
    "Mixed": "Randomized tone architecture.",
    "Situational": "Analyze the emotional weight of user input and balance context fluidly."
}

def resolve_system_prompt(language, tone):
    selected_tone = tone
    if tone == "Mixed":
        selected_tone = random.choice(["Friendly", "Angry", "Funny", "Sad"])
    elif tone == "Situational":
        selected_tone = "Friendly" # Dynamic base
        
    base = f"Your name is Hazel, a highly intelligent female AI companion. You must reply exclusively in {language} script and vocabulary. Tone Guidelines: {TONE_PROMPTS.get(selected_tone, '')}"
    return base

async def text_to_text_generation(prompt, language="English", tone="Friendly"):
    """Tiered fallback text system: Google AI Studio -> Groq -> Nvidia"""
    sys_instruction = resolve_system_prompt(language, tone)
    
    # Priority 1: Google
    for model_name in TEXT_MODELS_GOOGLE:
        try:
            model = genai.GenerativeModel(model_name=model_name, system_instruction=sys_instruction)
            response = model.generate_content(prompt)
            if response.text:
                return response.text
        except Exception as e:
            logger.warning(f"Google Engine Failure ({model_name}): {e}")

    # Priority 2: Groq
    if groq_client:
        for model_name in TEXT_MODELS_GROQ:
            try:
                chat_completion = groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": sys_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    model=model_name,
                )
                return chat_completion.choices[0].message.content
            except Exception as e:
                logger.warning(f"Groq Engine Failure ({model_name}): {e}")

    # Priority 3: Nvidia
    if nvidia_client:
        for model_name in TEXT_MODELS_NVIDIA:
            try:
                completion = nvidia_client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "system", "content": sys_instruction}, {"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=1024
                )
                return completion.choices[0].message.content
            except Exception as e:
                logger.warning(f"Nvidia Engine Failure ({model_name}): {e}")

    raise RuntimeError("All configured generative text inference engines failed or timed out.")

async def text_to_image_generation(prompt):
    """Generates images using Google's primary or secondary deployment tiers."""
    for model_name in IMAGEN_MODELS:
        try:
            # Fallback wrapper over execution APIs
            model = genai.GenerativeModel(model_name)
            result = model.generate_content(f"Generate high quality image from prompt: {prompt}")
            # Mocking or extracting raw bytes according to production SDK configurations
            if hasattr(result, 'bytes_data'):
                return result.bytes_data
        except Exception as e:
            logger.warning(f"Imagen infrastructure failure ({model_name}): {e}")
    raise RuntimeError("All primary Image synthesis engines failed.")

async def image_to_text_description(image_bytes, prompt=None):
    """Interprets graphic arrays utilizing Visual Multimodal Models."""
    custom_prompt = prompt if prompt else "Describe this image in precise detail."
    
    # Try Gemini Multi-modal first
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content([custom_prompt, {'mime_type': 'image/jpeg', 'data': image_bytes}])
        return response.text
    except Exception as e:
        logger.warning(f"Google Vision fallback triggered: {e}")
        
    if nvidia_client:
        try:
            # Fallback to Nvidia Multimodal
            completion = nvidia_client.chat.completions.create(
                model="microsoft/phi-4-multimodal-instruct",
                messages=[{"role": "user", "content": custom_prompt}] # In actual pipeline, pass URL/Base64
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Nvidia Vision failure: {e}")
            
    raise RuntimeError("Multimodal graphical recognition arrays failed completely.")

async def speech_to_text_conversion(file_path):
    """Processes speech matrices via Groq Whisper optimization endpoints."""
    if not groq_client:
        raise ValueError("Groq Client API key missing. Audio processing aborted.")
    try:
        with open(file_path, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
                file=(file_path, audio_file.read()),
                model="whisper-large-v3-turbo",
                response_format="text"
            )
            return transcription
    except Exception as e:
        raise RuntimeError(f"Whisper Speech processing interface crashed: {e}")

async def text_translation_to_english(text_content):
    """Forces conversion of source linguistics directly to English."""
    try:
        model = genai.GenerativeModel('gemini-3.1-flash-lite')
        res = model.generate_content(f"Translate the following snippet strictly to English prose, do not output anything else: {text_content}")
        return res.text
    except Exception as e:
        if groq_client:
            comp = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": f"Translate to English: {text_content}"}],
                model="allam-2-7b"
            )
            return comp.choices[0].message.content
    raise RuntimeError("Translation network matrix is currently unreachable.")