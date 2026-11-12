"""One Groq intent request, followed by local geometry compilation. No AI retries."""
import json
import math
from groq import Groq
from schema import Scene
from intent import BriefResponse, DesignResult, INTENT_PROMPT
from planner import compile_brief, summarize_scene, PlanningError

def design(requirements, previous=None, redesign=False, api_key=None, model_name='openai/gpt-oss-20b', client=None):
    if not api_key and client is None:
        raise ValueError('Parent project ki .env mein GROQ_API_KEY set karo.')
    instructions = INTENT_PROMPT + """
Schema: """ + json.dumps(BriefResponse.model_json_schema(), separators=(',', ':'))
    data = {'requirements': requirements, 'previous_scene_summary': summarize_scene(previous) if previous else None, 'different_layout_requested': redesign}
    messages = [{'role': 'system', 'content': instructions}, {'role': 'user', 'content': json.dumps(data, separators=(',', ':'))}]
    estimated_input = math.ceil(sum((len(m['content']) for m in messages)) / 3) + 200
    limit = min(5000, 7400 - estimated_input)
    if limit < 1000:
        raise ValueError('Brief is too long for the single-call token budget. Shorten the request. No API call was sent.')
    if client is None:
        client = Groq(api_key=api_key, timeout=120, max_retries=0)
    result = client.chat.completions.create(model=model_name, messages=messages, temperature=0.2, reasoning_effort='low', max_completion_tokens=limit, response_format={'type': 'json_object'})
    choice = result.choices[0]
    if choice.finish_reason != 'stop':
        raise ValueError('AI response was incomplete. No automatic retry was sent. Simplify the brief or request more token quota.')
    reply = BriefResponse.model_validate_json(choice.message.content or '')
    packet = DesignResult(message=reply.message, ready=reply.ready, assumptions=reply.assumptions, unsupported=reply.unsupported, brief=reply.brief, scene=None)
    if not reply.ready:
        return packet
    if reply.brief is None:
        raise ValueError('Groq marked the brief ready but omitted it. No retry was sent.')
    if previous and redesign and (reply.brief.action != 'palette') and (reply.brief.layout_variant == previous.get('layout_variant', 0)):
        reply.brief.layout_variant = (reply.brief.layout_variant + 1) % 10000
    try:
        packet.scene = Scene.model_validate(compile_brief(reply.brief, previous))
    except PlanningError as exc:
        packet.ready = False
        packet.message = str(exc)
        return packet
    packet.assumptions.append('Exact geometry, circulation, wall openings and furniture placement calculated locally; no geometry-repair Groq call.')
    packet.assumptions.append('Room target areas are preferences; explicit minimum usable room widths/areas are enforced. Circulation may use multiple connected rectangles.')
    if reply.brief.storeys > 1:
        packet.assumptions.append('Aligned stairs and floor lobbies are added locally. Unspecified upper-floor programs repeat the ground-floor rooms.')
        packet.assumptions.append(f'Storey spacing: {packet.scene.storey_height:.2f} m including slab; insufficient provider spacing is increased locally to preserve ceiling clearance.')
    if packet.scene.site:
        packet.assumptions.append(f'Site envelope: {packet.scene.site.width:.1f} × {packet.scene.site.depth:.1f} m; {len(packet.scene.site.parking)} parking bays. Plot dimensions are calculated when unspecified.')
    return packet
