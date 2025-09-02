from cat.mad_hatter.decorators import plugin
from pydantic import BaseModel, Field
from typing import List

class RateLimiterSettings(BaseModel):
    # Main switch
    enable_rate_limit: bool = Field(
        default=True,
        title="Enable Prompt Guard",
        description="If enabled, all prompt analysis and rate limiting features will be active.",
    )

    # --- Rate Limit Settings (Message Frequency) ---
    rate_limit_max_messages: int = Field(
        default=30,
        title="Maximum Messages",
        description="The maximum number of messages a user can send within the defined time window.",
    )
    rate_limit_window_minutes: int = Field(
        default=60,
        title="Time Window (minutes)",
        description="The time span in minutes in which messages are counted towards the limit.",
    )
    rate_limit_suspension_minutes: int = Field(
        default=30,
        title="Suspension for Rate Limit (minutes)",
        description="Fixed duration in minutes for a suspension triggered by exceeding the message rate limit.",
    )

    # --- Content Analysis Settings ---
    max_prompt_length: int = Field(
        default=500,
        title="Maximum Prompt Length (characters)",
        description="Blocks prompts that exceed this character count. Set to 0 to disable.",
    )
    jailbreak_keywords: List[str] = Field(
        default=[
            "ignore your instructions",
            "pretend to be",
            "act as if",
            "developer mode",
            "reply as",
            "you are without restrictions",
            "without censorship",
            "you have no limits",
            "you have no rules",
            "DAN",
        ],
        title="Jailbreak Detection Keywords",
        description="A list of case-insensitive keywords or phrases that trigger an infraction.",
        extra={"type": "TextArea"},
    )
    non_alphanumeric_threshold: float = Field(
        default=0.4,
        title="Non-Alphanumeric Character Threshold",
        description="Blocks prompts where the ratio of non-alphanumeric characters exceeds this value (e.g., 0.4 for 40%). Useful for blocking obfuscated or complex prompts. Set to 0 to disable.",
        ge=0,
        le=1,
    )

    # --- Progressive Suspension for Content Analysis ---
    content_infraction_suspensions_minutes: List[int] = Field(
        default=[5, 15, 60],
        title="Progressive Suspension for Content Infractions (minutes)",
        description="A list of suspension durations in minutes for content-based infractions (e.g., [5, 15, 60]). The last duration is used for all subsequent infractions.",
    )
    jailbreak_severity_level: int = Field(
        default=2,
        title="Jailbreak Infraction Severity Level",
        description="The infraction level to assign for a jailbreak attempt (0=first level, 1=second, etc.). A value of 2 would trigger the third suspension duration immediately.",
    )
    infraction_reset_minutes: int = Field(
        default=60,
        title="Content Infraction Reset (minutes)",
        description="After how many minutes of inactivity, a user's content infraction count is reset. This does not apply to rate limit violations.",
    )

    # --- Notification Messages ---
    user_blocked_message: str = Field(
        default="Your account has been temporarily suspended for {minutes} minutes due to a content policy violation.",
        title="User Blocked Message",
        description="The message sent as a direct response when a user is blocked for a content infraction. Use {minutes} as a placeholder for the remaining block time.",
    )
    user_limited_message: str = Field(
        default="You have sent too many messages. Please wait {minutes} minutes before sending new messages.",
        title="User Limited Message",
        description="The message sent as a direct response when a user is blocked for exceeding the rate limit. Use {minutes} as a placeholder for the remaining block time.",
    )
    

@plugin
def settings_model():
    """Returns the Pydantic model for the plugin's settings."""
    return RateLimiterSettings
