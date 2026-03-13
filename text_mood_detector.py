import os
from dotenv import load_dotenv

load_dotenv()

class TextMoodDetector:
    """Detect mood from text using multiple AI providers"""
    
    def __init__(self, provider='openai'):
        """
        Initialize detector with specified AI provider
        
        Args:
            provider (str): 'openai', 'gemini', or 'anthropic'
        """
        self.provider = provider
        self.mood_categories = ["happy", "sad", "angry", "calm", "energetic", "nostalgic"]
        
        # Initialize the appropriate client
        if provider == 'openai':
            from openai import OpenAI
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in .env file")
            self.client = OpenAI(api_key=api_key)
            
        elif provider == 'gemini':
            import google.generativeai as genai
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in .env file")
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel('gemini-3-flash-preview')
            
        elif provider == 'anthropic':
            from anthropic import Anthropic
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in .env file")
            self.client = Anthropic(api_key=api_key)
    
    def detect_mood(self, text):
        """
        Analyze text and return the detected mood with confidence scores
        
        Args:
            text (str): The text to analyze
            
        Returns:
            dict: {
                'dominant_mood': str,
                'confidence': float,
                'emotions': dict of all emotions with scores
            }
        """
        try:
            if self.provider == 'openai':
                return self._detect_openai(text)
            elif self.provider == 'gemini':
                return self._detect_gemini(text)
            elif self.provider == 'anthropic':
                return self._detect_anthropic(text)
        except Exception as e:
            print(f"❌ Error detecting mood: {e}")
            return {
                'dominant_mood': 'calm',
                'confidence': 0.5,
                'emotions': {'calm': 0.5}
            }
    
    def _detect_openai(self, text):
        """Detect mood using OpenAI GPT"""
        prompt = f"""Analyze the emotional tone of this text and provide scores for each emotion.

Text: "{text}"

Rate each emotion from 0.0 to 1.0:
- happy: (joy, excitement, contentment)
- sad: (sadness, melancholy, disappointment)
- angry: (anger, frustration, irritation)
- calm: (peace, relaxation, serenity)
- energetic: (energy, motivation, enthusiasm)
- nostalgic: (nostalgia, reminiscence, longing)

Respond ONLY with JSON in this exact format:
{{"happy": 0.0, "sad": 0.0, "angry": 0.0, "calm": 0.0, "energetic": 0.0, "nostalgic": 0.0}}"""

        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an emotion analysis expert. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=100
        )
        
        import json
        emotions = json.loads(response.choices[0].message.content.strip())
        
        # Normalize scores
        total = sum(emotions.values())
        if total > 0:
            emotions = {k: v/total for k, v in emotions.items()}
        
        dominant = max(emotions.items(), key=lambda x: x[1])
        
        return {
            'dominant_mood': dominant[0],
            'confidence': dominant[1],
            'emotions': emotions
        }
    
    def _detect_gemini(self, text):
        """Detect mood using Google Gemini"""
        prompt = f"""Analyze the emotional tone of this text and provide scores for each emotion.

Text: "{text}"

Rate each emotion from 0.0 to 1.0:
- happy: (joy, excitement, contentment)
- sad: (sadness, melancholy, disappointment)
- angry: (anger, frustration, irritation)
- calm: (peace, relaxation, serenity)
- energetic: (energy, motivation, enthusiasm)
- nostalgic: (nostalgia, reminiscence, longing)

Respond ONLY with JSON in this exact format:
{{"happy": 0.0, "sad": 0.0, "angry": 0.0, "calm": 0.0, "energetic": 0.0, "nostalgic": 0.0}}"""

        response = self.client.generate_content(prompt)
        
        import json
        # Extract JSON from response
        text_response = response.text.strip()
        # Remove markdown code blocks if present
        if '```json' in text_response:
            text_response = text_response.split('```json')[1].split('```')[0].strip()
        elif '```' in text_response:
            text_response = text_response.split('```')[1].split('```')[0].strip()
        
        emotions = json.loads(text_response)
        
        # Normalize scores
        total = sum(emotions.values())
        if total > 0:
            emotions = {k: v/total for k, v in emotions.items()}
        
        dominant = max(emotions.items(), key=lambda x: x[1])
        
        return {
            'dominant_mood': dominant[0],
            'confidence': dominant[1],
            'emotions': emotions
        }
    
    def _detect_anthropic(self, text):
        """Detect mood using Anthropic Claude"""
        prompt = f"""Analyze the emotional tone of this text and provide scores for each emotion.

Text: "{text}"

Rate each emotion from 0.0 to 1.0:
- happy: (joy, excitement, contentment)
- sad: (sadness, melancholy, disappointment)
- angry: (anger, frustration, irritation)
- calm: (peace, relaxation, serenity)
- energetic: (energy, motivation, enthusiasm)
- nostalgic: (nostalgia, reminiscence, longing)

Respond ONLY with JSON in this exact format:
{{"happy": 0.0, "sad": 0.0, "angry": 0.0, "calm": 0.0, "energetic": 0.0, "nostalgic": 0.0}}"""

        response = self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=200,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        import json
        emotions = json.loads(response.content[0].text.strip())
        
        # Normalize scores
        total = sum(emotions.values())
        if total > 0:
            emotions = {k: v/total for k, v in emotions.items()}
        
        dominant = max(emotions.items(), key=lambda x: x[1])
        
        return {
            'dominant_mood': dominant[0],
            'confidence': dominant[1],
            'emotions': emotions
        }
