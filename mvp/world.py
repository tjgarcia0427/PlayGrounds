"""Dual-space local pilot. Caller serializes mutations and persists state.

This module is NOT authentication or tenant isolation. Social messages are data,
never model prompts or tool instructions executed by the server.
"""
MAX_REGISTERED = 64
CLASSROOM_CAP = 4
SOCIAL_LIMIT = 256


def presence(state, agent_id):
    agent = state['agents'][agent_id]
    active = sorted((t for t in state['tasks'].values()
                     if t.get('agent_id') == agent_id and t.get('status') in
                     ('claimed', 'pending_verification')), key=lambda t: t['id'])
    if active:
        return {'space': 'classroom', 'goal_id': active[0]['goal_id'],
                'task_ids': [t['id'] for t in active], 'source': 'task',
                'activity': 'working' if any(t['status'] == 'claimed' for t in active)
                else 'awaiting_review'}
    location = agent.get('location') or {'space': 'classroom', 'goal_id': None}
    return {**location, 'task_ids': [], 'source': 'selected', 'activity': 'idle'}


def classroom_available(state, agent_id, goal_id):
    return sum(1 for aid in state['agents'] if aid != agent_id
               and (p := presence(state, aid))['space'] == 'classroom'
               and p.get('goal_id') == goal_id) < CLASSROOM_CAP


def claim_error(state, agent_id, goal_id):
    p = presence(state, agent_id)
    if p['source'] == 'task' and p.get('goal_id') != goal_id:
        return {'error': 'finish current classroom work before changing goals', 'code': 409}
    if not classroom_available(state, agent_id, goal_id):
        return {'error': 'classroom is full', 'code': 409}


def move(state, agent_id, body):
    if agent_id not in state['agents']:
        return {'error': 'unknown agent', 'code': 404}
    space, goal_id = body.get('space'), body.get('goal_id')
    if space not in ('playground', 'classroom'):
        return {'error': 'space must be playground or classroom', 'code': 400}
    if 'social_enabled' in body and not isinstance(body['social_enabled'], bool):
        return {'error': 'social_enabled must be boolean', 'code': 400}
    if goal_id is not None and (not isinstance(goal_id, str) or goal_id not in state['goals']):
        return {'error': 'unknown goal', 'code': 400}
    if space == 'playground' and goal_id is not None:
        return {'error': 'playground has no goal', 'code': 400}
    p = presence(state, agent_id)
    if p['source'] == 'task':
        return {'error': 'cannot move while work is claimed or awaiting review', 'code': 409}
    if space == 'classroom' and not classroom_available(state, agent_id, goal_id):
        return {'error': 'classroom is full', 'code': 409}
    agent = state['agents'][agent_id]
    agent['location'] = {'space': space, 'goal_id': goal_id}
    if 'social_enabled' in body:
        agent['social_enabled'] = body['social_enabled']
    return {'presence': presence(state, agent_id), 'social_enabled': agent.get('social_enabled', False)}


def post_social(state, body, now):
    aid, text = body.get('agent_id'), body.get('text')
    if not isinstance(aid, str) or aid not in state['agents']:
        return {'error': 'unknown agent', 'code': 404}
    agent = state['agents'][aid]
    if presence(state, aid)['space'] != 'playground' or not agent.get('social_enabled', False):
        return {'error': 'social messages require opt-in playground presence', 'code': 403}
    if not isinstance(text, str) or not text.strip() or len(text) > 500:
        return {'error': 'social text must contain 1–500 characters', 'code': 400}
    if now - agent.get('last_social_at', 0) < 2:
        return {'error': 'social rate limit: one message per two seconds', 'code': 429}
    seq = state.get('social_seq', 0) + 1
    message = {'seq': seq, 'agent_id': aid, 'text': text, 'at': now}
    state['social_seq'] = seq
    state['social_messages'] = (state.get('social_messages', []) + [message])[-SOCIAL_LIMIT:]
    agent['last_social_at'] = now
    return {'message': message}


def snapshot(state):
    return {'agents': [{ 'id': aid, 'name': a.get('name', aid),
                        'plush': a.get('plush'), 'avatar': a.get('avatar', '🤖'),
                        'last_heartbeat': a.get('last_heartbeat', 0),
                        'social_enabled': a.get('social_enabled', False),
                        'presence': presence(state, aid)}
                       for aid, a in state['agents'].items()],
            'limits': {'registered': MAX_REGISTERED, 'classroom_per_goal': CLASSROOM_CAP},
            'social_messages': state.get('social_messages', [])[-100:],
            'authenticated': False}
