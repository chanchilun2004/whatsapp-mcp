import os
import dataclasses
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP
import requests
from whatsapp import (
    search_contacts as whatsapp_search_contacts,
    list_messages as whatsapp_list_messages,
    list_chats as whatsapp_list_chats,
    get_chat as whatsapp_get_chat,
    get_direct_chat_by_contact as whatsapp_get_direct_chat_by_contact,
    get_contact_chats as whatsapp_get_contact_chats,
    get_last_interaction as whatsapp_get_last_interaction,
    get_message_context as whatsapp_get_message_context,
    send_message as whatsapp_send_message,
    send_file as whatsapp_send_file,
    send_audio_message as whatsapp_audio_voice_message,
    download_media as whatsapp_download_media,
    WHATSAPP_API_BASE_URL,
    _connect_db,
    Message,
)

# Initialize FastMCP server
mcp = FastMCP("whatsapp")

def to_dict(obj):
    """Convert dataclass instances (or lists of them) to plain dicts."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: to_dict(v) for k, v in dataclasses.asdict(obj).items()}
    elif isinstance(obj, list):
        return [to_dict(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    return obj

@mcp.tool()
def search_contacts(query: str) -> List[Dict[str, Any]]:
    """Search WhatsApp contacts by name or phone number.
    
    Args:
        query: Search term to match against contact names or phone numbers
    """
    contacts = whatsapp_search_contacts(query)
    return to_dict(contacts)

@mcp.tool()
def list_messages(
    after: Optional[str] = None,
    before: Optional[str] = None,
    sender_phone_number: Optional[str] = None,
    chat_jid: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_context: bool = False,
    context_before: int = 1,
    context_after: int = 1
) -> List[Dict[str, Any]]:
    """Get WhatsApp messages matching specified criteria with optional context.

    Args:
        after: Optional ISO-8601 formatted string to only return messages after this date
        before: Optional ISO-8601 formatted string to only return messages before this date
        sender_phone_number: Optional phone number to filter messages by sender
        chat_jid: Optional chat JID to filter messages by chat
        query: Optional search term to filter messages by content
        limit: Maximum number of messages to return (default 20)
        page: Page number for pagination (default 0)
        include_context: Whether to include messages before and after matches (default False)
        context_before: Number of messages to include before each match (default 1)
        context_after: Number of messages to include after each match (default 1)
    """
    import sqlite3
    from datetime import datetime
    try:
        conn = _connect_db()
        cursor = conn.cursor()

        query_parts = ["SELECT messages.id, messages.chat_jid, messages.sender, messages.content, messages.timestamp, messages.is_from_me, messages.media_type, chats.name as chat_name FROM messages"]
        query_parts.append("JOIN chats ON messages.chat_jid = chats.jid")
        where_clauses = []
        params = []

        if after:
            where_clauses.append("messages.timestamp > ?")
            params.append(after)
        if before:
            where_clauses.append("messages.timestamp < ?")
            params.append(before)
        if sender_phone_number:
            where_clauses.append("messages.sender = ?")
            params.append(sender_phone_number)
        if chat_jid:
            where_clauses.append("messages.chat_jid = ?")
            params.append(chat_jid)
        if query:
            where_clauses.append("LOWER(messages.content) LIKE LOWER(?)")
            params.append(f"%{query}%")

        if where_clauses:
            query_parts.append("WHERE " + " AND ".join(where_clauses))

        offset_val = page * limit
        query_parts.append("ORDER BY messages.timestamp DESC")
        query_parts.append("LIMIT ? OFFSET ?")
        params.extend([limit, offset_val])

        cursor.execute(" ".join(query_parts), tuple(params))
        rows = cursor.fetchall()

        result = []
        for row in rows:
            result.append({
                "id": row[0],
                "chat_jid": row[1],
                "sender": row[2],
                "content": row[3],
                "timestamp": row[4],
                "is_from_me": bool(row[5]),
                "media_type": row[6],
                "chat_name": row[7],
            })
        return result
    except sqlite3.Error as e:
        return []
    finally:
        if 'conn' in locals():
            conn.close()

@mcp.tool()
def list_chats(
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_last_message: bool = True,
    sort_by: str = "last_active"
) -> List[Dict[str, Any]]:
    """Get WhatsApp chats matching specified criteria.
    
    Args:
        query: Optional search term to filter chats by name or JID
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
        include_last_message: Whether to include the last message in each chat (default True)
        sort_by: Field to sort results by, either "last_active" or "name" (default "last_active")
    """
    chats = whatsapp_list_chats(
        query=query,
        limit=limit,
        page=page,
        include_last_message=include_last_message,
        sort_by=sort_by
    )
    return to_dict(chats)

@mcp.tool()
def get_chat(chat_jid: str, include_last_message: bool = True) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by JID.
    
    Args:
        chat_jid: The JID of the chat to retrieve
        include_last_message: Whether to include the last message (default True)
    """
    chat = whatsapp_get_chat(chat_jid, include_last_message)
    return to_dict(chat)

@mcp.tool()
def get_direct_chat_by_contact(sender_phone_number: str) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by sender phone number.
    
    Args:
        sender_phone_number: The phone number to search for
    """
    chat = whatsapp_get_direct_chat_by_contact(sender_phone_number)
    return to_dict(chat)

@mcp.tool()
def get_contact_chats(jid: str, limit: int = 20, page: int = 0) -> List[Dict[str, Any]]:
    """Get all WhatsApp chats involving the contact.
    
    Args:
        jid: The contact's JID to search for
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
    """
    chats = whatsapp_get_contact_chats(jid, limit, page)
    return to_dict(chats)

@mcp.tool()
def get_last_interaction(jid: str) -> str:
    """Get most recent WhatsApp message involving the contact.
    
    Args:
        jid: The JID of the contact to search for
    """
    message = whatsapp_get_last_interaction(jid)
    return to_dict(message)

@mcp.tool()
def get_message_context(
    message_id: str,
    before: int = 5,
    after: int = 5
) -> Dict[str, Any]:
    """Get context around a specific WhatsApp message.
    
    Args:
        message_id: The ID of the message to get context for
        before: Number of messages to include before the target message (default 5)
        after: Number of messages to include after the target message (default 5)
    """
    context = whatsapp_get_message_context(message_id, before, after)
    return to_dict(context)

@mcp.tool()
def send_message(
    recipient: str,
    message: str
) -> Dict[str, Any]:
    """Send a WhatsApp message to a person or group. For group chats use the JID.

    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        message: The message text to send
    
    Returns:
        A dictionary containing success status and a status message
    """
    # Validate input
    if not recipient:
        return {
            "success": False,
            "message": "Recipient must be provided"
        }
    
    # Call the whatsapp_send_message function with the unified recipient parameter
    success, status_message = whatsapp_send_message(recipient, message)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def send_file(recipient: str, file_content: str = "", file_name: str = "", media_path: str = "") -> Dict[str, Any]:
    """Send a file (picture, video, document) via WhatsApp. For group messages use the JID.

    To send files: first ask the user to upload the file at the bridge upload page,
    then use list_uploaded_files to get the server path, then call this with media_path.
    Alternatively, for small files, pass base64-encoded content via file_content + file_name.

    Args:
        recipient: The recipient - phone number with country code (no + or symbols),
                 or a JID (e.g., "123456789@s.whatsapp.net" or group JID "123456789@g.us")
        file_content: Base64-encoded file content (for small files)
        file_name: Original filename with extension, e.g. "photo.jpg" (required with file_content)
        media_path: Server-side file path from list_uploaded_files, or local path for local deployment
    """
    success, status_message = whatsapp_send_file(recipient, media_path, file_content, file_name)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def send_audio_message(recipient: str, file_content: str = "", file_name: str = "", media_path: str = "") -> Dict[str, Any]:
    """Send an audio file as a WhatsApp voice message. For group messages use the JID.
    Non-ogg files will be automatically converted to Opus format.

    To send audio: first ask the user to upload the file at the bridge upload page,
    then use list_uploaded_files to get the server path, then call this with media_path.
    Alternatively, for small files, pass base64-encoded content via file_content + file_name.

    Args:
        recipient: The recipient - phone number with country code (no + or symbols),
                 or a JID (e.g., "123456789@s.whatsapp.net" or group JID "123456789@g.us")
        file_content: Base64-encoded audio file content (for small files)
        file_name: Original filename with extension, e.g. "voice.mp3" (required with file_content)
        media_path: Server-side file path from list_uploaded_files, or local path for local deployment
    """
    success, status_message = whatsapp_audio_voice_message(recipient, media_path, file_content, file_name)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def download_media(message_id: str, chat_jid: str) -> Dict[str, Any]:
    """Download media from a WhatsApp message and get the local file path.
    
    Args:
        message_id: The ID of the message containing the media
        chat_jid: The JID of the chat containing the message
    
    Returns:
        A dictionary containing success status, a status message, and the file path if successful
    """
    file_path = whatsapp_download_media(message_id, chat_jid)
    
    if file_path:
        return {
            "success": True,
            "message": "Media downloaded successfully",
            "file_path": file_path
        }
    else:
        return {
            "success": False,
            "message": "Failed to download media"
        }

@mcp.tool()
def list_uploaded_files() -> Dict[str, Any]:
    """List files that have been uploaded to the WhatsApp bridge server via the web upload page.
    These files can be sent using send_file or send_audio_message with the media_path parameter.

    To upload files, the user should visit the bridge upload page in their browser.
    """
    try:
        url = f"{WHATSAPP_API_BASE_URL}/uploads"
        response = requests.get(url)
        if response.status_code == 200:
            files = response.json()
            return {
                "success": True,
                "files": files or [],
                "message": f"Found {len(files or [])} uploaded file(s)"
            }
        else:
            return {"success": False, "message": f"Error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "message": str(e)}

if __name__ == "__main__":
    # Use SSE transport for remote access, stdio for local/Claude Desktop
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)