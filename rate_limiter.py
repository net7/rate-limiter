import time
import math
import os
import json
from cat.mad_hatter.decorators import hook
from cat.log import log

# Path for the persistent data file
DATA_FILE = os.path.join(os.path.dirname(__file__), "rate_limit_data.json")

# In-memory cache for user data
_user_data_cache = {}
_cache_last_loaded = 0

def _load_data(force_reload=False):
    """
    Loads rate limit data from the JSON file into an in-memory cache.
    The cache is reloaded from disk if it's older than 5 seconds or if forced.
    """
    global _user_data_cache, _cache_last_loaded
    current_time = time.time()
    
    # Reload from disk if cache is old or forced
    if force_reload or not _user_data_cache or (current_time - _cache_last_loaded > 5):
        if not os.path.exists(DATA_FILE):
            _user_data_cache = {}
        else:
            try:
                with open(DATA_FILE, "r") as f:
                    _user_data_cache = json.load(f)
            except (json.JSONDecodeError, IOError):
                _user_data_cache = {}
        _cache_last_loaded = current_time
    return _user_data_cache

def _save_data(data):
    """Saves the rate limit data to the JSON file and updates the in-memory cache."""
    global _user_data_cache
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
        _user_data_cache = data # Update cache on successful save
    except IOError as e:
        log.error(f"[RateLimiter] Could not save data to {DATA_FILE}: {e}")


def _check_prompt_length(prompt: str, max_length: int) -> bool:
    """Checks if the prompt exceeds the maximum allowed length."""
    if max_length <= 0:
        return False
    return len(prompt) > max_length

def _check_jailbreak_keywords(prompt: str, keywords: list) -> bool:
    """Checks if the prompt contains any of the forbidden keywords."""
    if not keywords:
        return False
    lower_prompt = prompt.lower()
    for keyword in keywords:
        if keyword.lower() in lower_prompt:
            return True
    return False

def _check_complexity(prompt: str, threshold: float) -> bool:
    """Checks if the ratio of non-alphanumeric characters exceeds the threshold."""
    if threshold <= 0:
        return False
    if not prompt:
        return False
    
    non_alphanumeric = sum(1 for char in prompt if not char.isalnum())
    ratio = non_alphanumeric / len(prompt)
    return ratio > threshold

@hook
def fast_reply(fast_reply: dict, cat) -> dict | None:
    """
    Core hook for the Prompt Guard plugin.
    
    This hook intercepts user messages before they are processed by the LLM.
    It performs several checks:
    1.  **Content Analysis**: Scans for prompts that are too long, contain forbidden
        keywords (jailbreak attempts), or have a high complexity (too many
        non-alphanumeric characters). Violations trigger a progressive suspension.
    2.  **Rate Limiting**: Checks if the user has sent too many messages in a
        configured time window. Violations trigger a fixed-duration suspension.
    
    If any check fails, the hook returns a blocking message directly in the chat
    and stops the regular message processing flow. The content of this message is
    fully configurable in the plugin settings. It also manages user data, such as
    infraction levels and total message counts.
    """
    
    # Load plugin settings
    try:
        plugin = cat.mad_hatter.get_plugin()
        settings = plugin.load_settings()
    except Exception as e:
        log.error(f"[RateLimiter] Could not load settings: {e}")
        return None # Do not block in case of an error

    if not settings.get("enable_rate_limit"):
        return None

    user_id = cat.user_id
    current_time = time.time()
    user_prompt = cat.working_memory.get("user_message_json", {}).get("text", "")
    
    # Load all user data and get specific user data
    all_data = _load_data()
    user_data = all_data.get(user_id, {})
    
    # Check if the user is currently blocked from a previous infraction
    if "blocked_until" in user_data and current_time < user_data["blocked_until"]:
        remaining_seconds = user_data["blocked_until"] - current_time
        remaining_minutes = math.ceil(remaining_seconds / 60)

        if user_data.get("block_reason") == "content":
            message_template = settings.get("user_blocked_message", "Your account has been temporarily suspended for {minutes} minutes due to a content policy violation.")
            block_message = message_template.format(minutes=remaining_minutes)
        else:
            message_template = settings.get("user_limited_message", "You have sent too many messages. Please wait {minutes} minutes before sending new messages.")
            block_message = message_template.format(minutes=remaining_minutes)
        return {"output": f"{block_message}"}
    elif "blocked_until" in user_data and current_time >= user_data["blocked_until"]:
        # The user is no longer blocked, so clean up the block data
        del user_data["blocked_until"]
        if "block_reason" in user_data:
            del user_data["block_reason"]
    
    # --- Start of Infraction Checks ---
    infraction_detected = False
    infraction_reason = ""
    is_content_infraction = False

    # 1. Content Analysis Checks
    # Check 1.1: Prompt Length
    max_len = settings.get("max_prompt_length", 0)
    if _check_prompt_length(user_prompt, max_len):
        infraction_detected = True
        is_content_infraction = True
        infraction_reason = f"exceeded max length of {max_len} characters"

    # Check 1.2: Jailbreak Keywords
    if not infraction_detected:
        keywords = settings.get("jailbreak_keywords", [])
        if _check_jailbreak_keywords(user_prompt, keywords):
            infraction_detected = True
            is_content_infraction = True
            infraction_reason = "contained a forbidden keyword"

    # Check 1.3: Complexity
    if not infraction_detected:
        threshold = settings.get("non_alphanumeric_threshold", 0.0)
        if _check_complexity(user_prompt, threshold):
            infraction_detected = True
            is_content_infraction = True
            infraction_reason = f"exceeded non-alphanumeric threshold of {threshold*100}%"
    
    # 2. Frequency Check (Rate Limiting)
    rate_limit_window_minutes = settings.get("rate_limit_window_minutes", 1)
    rate_limit_window_seconds = rate_limit_window_minutes * 60
    # Filter timestamps to the current window
    message_timestamps = [t for t in user_data.get("timestamps", []) if current_time - t < rate_limit_window_seconds]
    
    max_messages = settings.get("rate_limit_max_messages", 20)
    if not infraction_detected and len(message_timestamps) >= max_messages:
        infraction_detected = True
        infraction_reason = f"exceeded frequency limit of {max_messages} messages per {rate_limit_window_minutes} minute(s)"
    
    # --- End of Infraction Checks ---
    
    # If an infraction is detected, block the user and save state
    if infraction_detected:
        log.warning(f"[PromptGuard] User {user_id} blocked. Reason: {infraction_reason}.")
        
        block_minutes = 0
        if is_content_infraction:
            # Progressive suspension for content-based infractions
            suspension_durations = settings.get("content_infraction_suspensions_minutes", [5, 15, 60])
            infraction_level = user_data.get("infraction_level", 0)

            # A jailbreak attempt can be configured to immediately jump to a higher infraction level
            if "forbidden keyword" in infraction_reason:
                jailbreak_severity = settings.get("jailbreak_severity_level", 2)
                if jailbreak_severity > infraction_level:
                    infraction_level = jailbreak_severity
            
            if infraction_level < len(suspension_durations):
                block_minutes = suspension_durations[infraction_level]
            else:
                block_minutes = suspension_durations[-1]
            
            user_data["infraction_level"] = infraction_level + 1

        else:
            # Fixed-duration suspension for rate limit violations
            block_minutes = settings.get("rate_limit_suspension_minutes", 30)

        user_data["blocked_until"] = current_time + (block_minutes * 60)
        if is_content_infraction:
            user_data["block_reason"] = "content"
        else:
            user_data["block_reason"] = "rate_limit"
        
        # Add current message to timestamps for completeness
        message_timestamps.append(current_time)
        user_data["timestamps"] = message_timestamps
        
        all_data[user_id] = user_data
        _save_data(all_data)
        
        # Return block message
        if is_content_infraction:
            message_template = settings.get("user_blocked_message", "Your account has been temporarily suspended for {minutes} minutes due to a content policy violation.")
            block_message = message_template.format(minutes=block_minutes)
        else:
            message_template = settings.get("user_limited_message", "You have sent too many messages. Please wait {minutes} minutes before sending new messages.")
            block_message = message_template.format(minutes=block_minutes)
        return {"output": f"{block_message}"}


    # --- Regular Flow (No Infraction) ---

    # Reset content infraction level after a period of inactivity
    infraction_reset_minutes = settings.get("infraction_reset_minutes", 60)
    if infraction_reset_minutes > 0:
        infraction_reset_seconds = infraction_reset_minutes * 60
        last_message_time = user_data.get("timestamps", [])[-1] if user_data.get("timestamps") else 0
        if current_time - last_message_time > infraction_reset_seconds:
            if user_data.get("infraction_level", 0) > 0:
                log.info(f"[PromptGuard] User {user_id} has been inactive. Content infraction level reset.")
                user_data["infraction_level"] = 0
    
    # If the user is not blocked, add the current message's timestamp and save
    message_timestamps.append(current_time)
    user_data["timestamps"] = message_timestamps
    
    # Increment total messages
    total_messages = user_data.get("total_messages", 0) + 1
    user_data["total_messages"] = total_messages
    
    all_data[user_id] = user_data
    _save_data(all_data)

    log.info(f"[PromptGuard] Valid message from user {user_id} recorded. Total messages: {total_messages}. Current count in window: {len(message_timestamps)}/{max_messages}.")

    return None
