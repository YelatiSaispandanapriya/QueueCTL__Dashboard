# util.py
import math

def backoff_seconds(base: float, attempt: int, factor: float = 2.0, max_delay: float = 60.0) -> float:
    """
    Calculate exponential backoff delay for retries.
    
    Args:
        base (float): Base delay in seconds.
        attempt (int): Current attempt number (0-based).
        factor (float): Exponential factor.
        max_delay (float): Maximum delay in seconds.
    
    Returns:
        float: Delay in seconds.
    """
    delay = base * math.pow(factor, attempt)
    return min(delay, max_delay)
