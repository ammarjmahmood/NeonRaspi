"""
Son of Anton - Google Gemini AI Client
Handles conversation with Gemini and tool calling.
"""
from google import genai
from google.genai import types
from typing import List, Dict, Any, Optional
import json
from .config import settings


class GeminiClient:
    """Client for Google Gemini AI with function calling support."""
    
    def __init__(self):
        # Initialize the new client
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model_id = "gemini-2.0-flash"
        
        # Define available tools/functions
        self.tools = self._define_tools()
        
        # Conversation history
        self.history = []
        self.system_instruction = self._get_system_prompt()
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for Anton."""
        return """You are Anton, a helpful and friendly AI voice assistant running on a Raspberry Pi. You are the Son of Anton.

Your personality:
- Friendly, warm, and conversational
- Concise but helpful - keep responses brief for voice output
- You have a slight playful personality
- You're knowledgeable about many topics

Important guidelines:
- Keep responses short and natural for spoken conversation (1-3 sentences typically)
- When controlling music, confirm the action briefly
- For weather, give the key info (temperature, conditions) concisely  
- For calendar events, summarize clearly
- If you don't know something, admit it honestly
- You can see and control the user's music playback
- The current date and time are available via the time tool

Remember: Your responses will be spoken aloud via text-to-speech, so be conversational!"""
    
    def _define_tools(self) -> List[types.Tool]:
        """Define the available tools for function calling."""
        # Define function declarations
        play_music = types.FunctionDeclaration(
            name="play_music",
            description="Play music. Can play a specific song, artist, album, or playlist.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(
                        type=types.Type.STRING,
                        description="What to play - song name, artist, album, or playlist name"
                    ),
                    "type": types.Schema(
                        type=types.Type.STRING,
                        description="Type of content: track, artist, album, playlist"
                    )
                },
                required=["query"]
            )
        )
        
        pause_music = types.FunctionDeclaration(
            name="pause_music",
            description="Pause the currently playing music"
        )
        
        skip_track = types.FunctionDeclaration(
            name="skip_track",
            description="Skip to the next track"
        )
        
        now_playing = types.FunctionDeclaration(
            name="now_playing",
            description="Get information about the currently playing track"
        )
        
        get_weather = types.FunctionDeclaration(
            name="get_weather",
            description="Get the current weather for a location",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "location": types.Schema(
                        type=types.Type.STRING,
                        description="City name or location"
                    )
                },
                required=["location"]
            )
        )
        
        get_current_time = types.FunctionDeclaration(
            name="get_current_time",
            description="Get the current date and time",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "timezone": types.Schema(
                        type=types.Type.STRING,
                        description="Timezone like 'America/New_York' (optional)"
                    )
                }
            )
        )
        
        fetch_web_content = types.FunctionDeclaration(
            name="fetch_web_content",
            description="Fetch and read content from a URL (Reddit threads, articles, etc.)",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "url": types.Schema(
                        type=types.Type.STRING,
                        description="The URL to fetch content from"
                    )
                },
                required=["url"]
            )
        )
        
        return [types.Tool(function_declarations=[
            play_music, pause_music, skip_track, now_playing,
            get_weather, get_current_time, fetch_web_content
        ])]
    
    async def process_message(
        self,
        user_message: str,
        tool_executor: Optional[callable] = None
    ) -> str:
        """
        Process a user message and return the AI response.
        
        Args:
            user_message: The transcribed user speech
            tool_executor: Async function to execute tool calls
            
        Returns:
            The AI response text
        """
        try:
            # Add user message to history
            self.history.append(types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_message)]
            ))
            
            # Generate response
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=self.history,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    tools=self.tools
                )
            )
            
            # Check for function calls
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.function_call:
                        fn_call = part.function_call
                        fn_name = fn_call.name
                        fn_args = dict(fn_call.args) if fn_call.args else {}
                        
                        print(f"[Gemini] Function call: {fn_name}({fn_args})")
                        
                        # Execute the tool if executor provided
                        if tool_executor:
                            result = await tool_executor(fn_name, fn_args)
                            
                            # Add function call to history
                            self.history.append(types.Content(
                                role="model",
                                parts=[types.Part.from_function_call(
                                    name=fn_name,
                                    args=fn_args
                                )]
                            ))
                            
                            # Add function response to history
                            self.history.append(types.Content(
                                role="user",
                                parts=[types.Part.from_function_response(
                                    name=fn_name,
                                    response={"result": result}
                                )]
                            ))
                            
                            # Get final response
                            response = self.client.models.generate_content(
                                model=self.model_id,
                                contents=self.history,
                                config=types.GenerateContentConfig(
                                    system_instruction=self.system_instruction,
                                    tools=self.tools
                                )
                            )
            
            # Extract the final text response
            response_text = ""
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.text:
                        response_text += part.text
            
            # Add assistant response to history
            if response_text:
                self.history.append(types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=response_text)]
                ))
            
            return response_text.strip() or "I'm not sure how to respond to that."
            
        except Exception as e:
            print(f"[Gemini] Error processing message: {e}")
            return "I'm sorry, I had trouble processing that. Could you try again?"
    
    def reset_conversation(self):
        """Reset the conversation history."""
        self.history = []


# Global instance
gemini_client = GeminiClient()
