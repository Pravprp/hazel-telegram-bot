# Models.py
import os
import random
import google.generativeai as genai
from groq import Groq
from openai import OpenAI
from Errors import logger

GOOGLE_KEYS = [os.getenv("GOOGLE_AI_STUDIO_KEY")]
GROQ_KEY = os.getenv("GROQ_API_KEY")
NVIDIA_KEY = os.getenv("NVIDIA_API_KEY")

if GOOGLE_KEYS[0]:
    genai.configure(api_key=GOOGLE_KEYS[0])
groq_client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None
nvidia_client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=NVIDIA_KEY) if NVIDIA_KEY else None

TEXT_MODELS_GOOGLE = ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3-flash", "gemma-4-31b-it"]
TEXT_MODELS_GROQ = ["allam-2-7b", "llama-3.3-70b-versatile", "qwen/qwen3-32b"]
TEXT_MODELS_NVIDIA = ["google/gemma-2-2b-it", "stepfun-ai/step-3.5-flash"]

# Updated to use the correct available Imagen 3 model
IMAGEN_MODELS = ["imagen-3.0-generate-001"]

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
        selected_tone = "Friendly"
        
    return f"Your name is Hazel, a highly intelligent female AI companion. You must reply exclusively in {language} script. Tone Guidelines: {TONE_PROMPTS.get(selected_tone, '')}"

async def text_to_text_generation(prompt, language="English", tone="Friendly"):
    sys_instruction = resolve_system_prompt(language, tone)
    
    for model_name in TEXT_MODELS_GOOGLE:
        try:
            model = genai.GenerativeModel(model_name=model_name, system_instruction=sys_instruction)
            response = model.generate_content(prompt)
            if response.text: return response.text
        except Exception as e:
            logger.warning(f"Google Engine Failure ({model_name}): {e}")

    if groq_client:
        for model_name in TEXT_MODELS_GROQ:
            try:
                chat_completion = groq_client.chat.completions.create(
                    messages=[{"role": "system", "content": sys_instruction}, {"role": "user", "content": prompt}],
                    model=model_name,
                )
                return chat_completion.choices[0].message.content
            except Exception as e:
                logger.warning(f"Groq Engine Failure ({model_name}): {e}")

    if nvidia_client:
        for model_name in TEXT_MODELS_NVIDIA:
            try:
                completion = nvidia_client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "system", "content": sys_instruction}, {"role": "user", "content": prompt}],
                    max_tokens=1024
                )
                return completion.choices[0].message.content
            except Exception as e:
                logger.warning(f"Nvidia Engine Failure ({model_name}): {e}")

    raise RuntimeError("All configured generative text inference engines failed or timed out.")

async def text_to_image_generation(prompt):
    """Generates images using Google's dedicated ImageGenerationModel API."""
    for model_name in IMAGEN_MODELS:
        try:
            # We must use ImageGenerationModel, NOT GenerativeModel for images
            model = genai.ImageGenerationModel(f"models/{model_name}")
            result = model.generate_images(
                prompt=prompt,
                number_of_images=1,
                output_mime_type="image/jpeg"
            )
            
            # Extract the raw byte data from the generated payload
            if result.images:
                # The SDK nests the bytes inside the _image attribute
                return result.images[0]._image.image_bytes
                
        except Exception as e:
            logger.warning(f"Imagen infrastructure failure ({model_name}): {e}")
            
    raise RuntimeError("All primary Image synthesis engines failed. Ensure your prompt meets safety guidelines.")

async def image_to_text_description(image_bytes, prompt=None):
    custom_prompt = prompt if prompt else "Describe this image in precise detail."
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content([custom_prompt, {'mime_type': 'image/jpeg', 'data': image_bytes}])
        return response.text
    except Exception as e:
        logger.warning(f"Google Vision fallback triggered: {e}")
        
    if nvidia_client:
        try:
            completion = nvidia_client.chat.completions.create(
                model="microsoft/phi-4-multimodal-instruct",
                messages=[{"role": "user", "content": custom_prompt}]
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Nvidia Vision failure: {e}")
    raise RuntimeError("Multimodal graphical recognition arrays failed completely.")

async def speech_to_text_conversion(file_path):
    if not groq_client: raise ValueError("Groq Client API key missing.")
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
