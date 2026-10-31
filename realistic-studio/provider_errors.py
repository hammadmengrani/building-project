"""Safe provider diagnostics: only documented quota headers, never response secrets."""
import math
import re


def rate_limit_message(exc):
    headers=getattr(getattr(exc,'response',None),'headers',{}) or {}
    parts=['Groq quota/rate limit reached. No automatic retry was sent.']
    wait=headers.get('retry-after')
    try:
        seconds=float(wait)
        if math.isfinite(seconds) and 0<=seconds<=604800:
            parts.append(f'Groq says wait at least {math.ceil(seconds)} seconds before retrying.')
    except (ValueError,TypeError):
        pass
    for remaining,reset,label in [
        ('x-ratelimit-remaining-requests','x-ratelimit-reset-requests','daily requests'),
        ('x-ratelimit-remaining-tokens','x-ratelimit-reset-tokens','minute tokens')]:
        value=str(headers.get(remaining,''))
        duration=str(headers.get(reset,''))
        if re.fullmatch(r'\d{1,12}',value):
            detail=f'Remaining {label}: {value}'
            if duration and re.fullmatch(r'[0-9hms.µ ]{1,60}',duration):
                detail+=f'; reset in {duration}'
            parts.append(detail+'.')
    if len(parts)==1:
        parts.append('Exact reset time was not provided here. Check your Groq Console Limits page. Local project builds and examples still work without Groq.')
    return ' '.join(parts)
