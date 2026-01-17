"""
Neon Pi - Google Gemini AI Client
Handles conversation with Gemini and tool calling.
"""
import google.generativeai as genai
from typing import List, Dict, Any, Optional
import json
from .config import settings


class GeminiClient:
    """Client for Google Gemini AI with function calling support."""
    
    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        
        # Define available tools/functions for Gemini
        self.tools = self._define_tools()
        
        # Initialize the model
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            tools=self.tools,
            system_instruction=self._get_system_prompt()
        )
        
        # Conversation history
        self.chat = self.model.start_chat(history=[])
    
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
- When controlling Spotify, confirm the action briefly
- For weather, give the key info (temperature, conditions) concisely  
- For calendar events, summarize clearly
- If you don't know something, admit it honestly
- You can see and control the user's Spotify playback
- The current date and time are available via the time tool

Remember: Your responses will be spoken aloud via text-to-speech, so be conversational!"""
    
    def _define_tools(self) -> List[Any]:
        """Define the available tools for function calling."""
        tools = [
            genai.protos.Tool(
                function_declarations=[
                    # Spotify Controls
                    genai.protos.FunctionDeclaration(
                        name="spotify_play",
                        description="Play music on Spotify. Can play a specific song, artist, album, or playlist.",
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                "query": genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description="What to play - song name, artist, album, or playlist name"
                                ),
                                "type": genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description="Type of content: track, artist, album, playlist"
                                )
                            },
                            required=["query"]
                        )
                    ),
                    genai.protos.FunctionDeclaration(
                        name="spotify_pause",
                        description="Pause the currently playing music on Spotify"
                    ),
                    genai.protos.FunctionDeclaration(
                        name="spotify_resume",
                        description="Resume playback on Spotify"
                    ),
                    genai.protos.FunctionDeclaration(
                        name="spotify_skip",
                        description="Skip to the next track on Spotify"
                    ),
                    genai.protos.FunctionDeclaration(
                        name="spotify_previous",
                        description="Go back to the previous track on Spotify"
                    ),
                    genai.protos.FunctionDeclaration(
                        name="spotify_volume",
                        description="Set the Spotify playback volume",
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                "volume": genai.protos.Schema(
                                    type=genai.protos.Type.INTEGER,
                                    description="Volume level from 0 to 100"
                                )
                            },
                            required=["volume"]
                        )
                    ),
                    genai.protos.FunctionDeclaration(
                        name="spotify_now_playing",
                        description="Get information about the currently playing track on Spotify"
                    ),
                    
                    # Weather
                    genai.protos.FunctionDeclaration(
                        name="get_weather",
                        description="Get the current weather for a location",
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                "location": genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description="City name or location"
                                )
                            },
                            required=["location"]
                        )
                    ),
                    
                    # Time
                    genai.protos.FunctionDeclaration(
                        name="get_current_time",
                        description="Get the current date and time",
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                "timezone": genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description="Timezone like 'America/New_York' (optional)"
                                )
                            }
                        )
                    ),
                    
                    # Web Fetch
                    genai.protos.FunctionDeclaration(
                        name="fetch_web_content",
                        description="Fetch and read content from a URL (Reddit threads, articles, etc.)",
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                "url": genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description="The URL to fetch content from"
                                )
                            },
                            required=["url"]
                        )
                    ),
                ]
            )
        ]
        return tools
    
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
            # Send the message to Gemini
            response = self.chat.send_message(user_message)
            
            # Check if there are function calls
            if response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        fn_call = part.function_call
                        fn_name = fn_call.name
                        fn_args = dict(fn_call.args) if fn_call.args else {}
                        
                        print(f"[Gemini] Function call: {fn_name}({fn_args})")
                        
                        # Execute the tool if executor provided
                        if tool_executor:
                            result = await tool_executor(fn_name, fn_args)
                            
                            # Send the function result back to Gemini
                            response = self.chat.send_message(
                                genai.protos.Content(
                                    parts=[
                                        genai.protos.Part(
                                            function_response=genai.protos.FunctionResponse(
                                                name=fn_name,
                                                response={"result": result}
                                            )
                                        )
                                    ]
                                )
                            )
            
            # Extract the final text response
            response_text = ""
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'text') and part.text:
                    response_text += part.text
            
            return response_text.strip()
            
        except Exception as e:
            print(f"[Gemini] Error processing message: {e}")
            return "I'm sorry, I had trouble processing that. Could you try again?"
    
    def reset_conversation(self):
        """Reset the conversation history."""
        self.chat = self.model.start_chat(history=[])


# Global instance
gemini_client = GeminiClient()
