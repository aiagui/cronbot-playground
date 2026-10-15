def format_duration(seconds: int) -> str:
    """Format a non-negative duration as compact hour, minute, and second parts."""
    if type(seconds) is not int:
        raise TypeError("seconds must be an integer")
    if seconds < 0:
        raise ValueError("seconds must not be negative")

    parts = []
    if seconds > 3600:
        hours, seconds = divmod(seconds, 3600)
        parts.append(f"{hours}h")
    if seconds >= 60:
        minutes, seconds = divmod(seconds, 60)
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)
