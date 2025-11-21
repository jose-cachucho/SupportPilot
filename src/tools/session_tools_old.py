from typing import Dict, Any
from google.adk.tools.tool_context import ToolContext

def get_my_info(tool_context: ToolContext) -> Dict[str, str]:
    """
    Retrieves the current authenticated user's ID and Name from the session state.
    Returns a structured dictionary.
    """
    # Leitura segura do estado
    user_id = tool_context.state.get("user:user_id", "Unknown")
    name = tool_context.state.get("user:name", "Guest")
    
    return {
        "status": "success",
        "user_id": user_id,
        "user_name": name,
        "message": f"The current active user is {user_id}."
    }