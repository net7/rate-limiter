# Rate Limiter Plugin

A powerful security and moderation plugin for the Cheshire Cat AI framework designed to protect your instance from spam, abuse, and malicious inputs.

Rate Limiter acts as a firewall for user prompts, analyzing them for suspicious patterns and controlling the frequency of messages. It allows you to set up a robust defense system with fine-grained control over user behavior.

## Key Features

-   **Rate Limiting**: Control how many messages a user can send in a specific time frame to prevent spam and abuse.
-   **Content Analysis**: Automatically block prompts based on:
    -   **Max Length**: Reject overly long messages that could strain resources.
    -   **Forbidden Keywords**: Detect and block common "jailbreak" attempts, prompt injections, or other undesirable phrases using a customizable keyword list.
    -   **High Complexity**: Prevent obfuscated or nonsensical inputs by analyzing the ratio of non-alphanumeric characters.
-   **Dual Suspension System**:
    -   **Fixed Suspension**: Users exceeding the simple message rate limit receive a suspension of a fixed, predictable duration.
    -   **Progressive Suspension**: Users who violate content rules (e.g., by sending malicious prompts) receive increasingly longer suspensions for repeated infractions, discouraging persistent bad actors.
-   **Configurable Block Messages**: Customize the exact messages sent to users when they are suspended. Use placeholders like `{minutes}` to dynamically include the suspension duration.
-   **Severity Control**: Immediately assign a higher penalty for serious violations, such as jailbreak attempts, bypassing the initial warning stages.
-   **Persistent User Tracking**: User data, including infraction levels and total message counts, is saved to a local JSON file, ensuring that disciplinary measures are maintained across sessions.

## Configuration

All settings can be configured from the Cheshire Cat Admin Panel under the **Plugins** section. Find the **Rate Limiter** plugin and click on "Settings".

---

### Main Settings

| Setting               | Description                                                  | Default Value |
| --------------------- | ------------------------------------------------------------ | ------------- |
| `Enable Prompt Guard` | Main switch to turn all plugin features on or off.           | `True`        |

### Rate Limit Settings (Message Frequency)

These settings control how many messages a user can send.

| Setting                             | Description                                                                                             | Default Value |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------- | ------------- |
| `Maximum Messages`                  | The maximum number of messages a user can send within the defined time window.                          | `30`          |
| `Time Window (minutes)`             | The time span in minutes in which messages are counted towards the limit.                               | `60`          |
| `Suspension for Rate Limit (minutes)` | The fixed duration (in minutes) of a suspension triggered *only* by exceeding the message rate limit. | `30`          |

### Content Analysis Settings

These settings control *what* kind of content is allowed in a prompt.

| Setting                                | Description                                                                                                                                                             | Default Value                                                                                                                               |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `Maximum Prompt Length (characters)`   | Blocks prompts that exceed this character count. Set to `0` to disable this check.                                                                                      | `500`                                                                                                                                       |
| `Jailbreak Detection Keywords`         | A list of case-insensitive keywords or phrases that will trigger a content infraction.                                                                                  | `["ignore your instructions", "pretend to be", "act as if", "developer mode", "reply as", "you are without restrictions", "without censorship", "you have no limits", "you have no rules", "DAN"]` |
| `Non-Alphanumeric Character Threshold` | Blocks prompts where the ratio of non-alphanumeric characters exceeds this value (e.g., `0.4` for 40%). This is useful for blocking obfuscated prompts. Set to `0` to disable. | `0.4`                                                                                                                                       |

### Progressive Suspension for Content Analysis

These settings control the punishment for violating the content rules defined above.

| Setting                                                | Description                                                                                                                                                                                              | Default Value |
| ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------- |
| `Progressive Suspension for Content Infractions (minutes)` | A list of suspension durations for content-based infractions (e.g., `[5, 15, 60]`). The first infraction gets the first duration, the second gets the second, and so on. The last duration is used for all subsequent infractions. | `[5, 15, 60]` |
| `Jailbreak Infraction Severity Level`                  | Immediately assigns a higher infraction level for a jailbreak attempt. For example, if your suspensions are `[5, 15, 60]` and the severity is `2`, a user's first jailbreak attempt will immediately trigger the third suspension duration (60 minutes). The level is 0-indexed. | `2`           |
| `Content Infraction Reset (minutes)`                   | The number of minutes of inactivity after which a user's content infraction count is reset to zero. This does not affect rate limit violations.                                                              | `60`          |

### Notification Settings

These settings control the messages sent to the user when a block is triggered.

| Setting                  | Description                                                                                                                                        | Default Value                                                                                                   |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `User Blocked Message`   | The message sent when a user is blocked for a content infraction. Use `{minutes}` as a placeholder for the remaining block time.                     | `"Your account has been temporarily suspended for {minutes} minutes due to a content policy violation."`      |
| `User Limited Message`   | The message sent when a user is blocked for exceeding the rate limit. Use `{minutes}` as a placeholder for the remaining block time.                 | `"You have sent too many messages. Please wait {minutes} minutes before sending new messages."`                 |
