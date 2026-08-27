from __future__ import annotations


def test_projector_generates_generic_person_and_project_states(client):
    payload = client.get('/v1/bootstrap', params={'user_id': 'maya'}).json()
    states = {item['entity_id']: item for item in payload['work_states']}
    assert states['daniel']['status'] == 'in_review'
    assert 'AUTH-392' in states['daniel']['headline']
    assert states['sarah']['status'] == 'delegated'
    assert 'Alex Morgan' in states['sarah']['headline']
    assert states['atlas']['status'] == 'blocked'
    assert 'SEC-184' in states['atlas']['headline']


def test_projector_mutates_work_item_from_normalized_events(client):
    event = {
        'id': 'event-auth-approved-generic',
        'source': 'github',
        'event_type': 'pull_request.reviewed',
        'actor_user_id': 'daniel',
        'entity_ids': ['atlas', 'auth-392'],
        'occurred_at': '2026-08-27T13:20:00-04:00',
        'payload': {'number': 892, 'review_state': 'approved', 'mergeable': True},
    }
    response = client.post('/v1/events', json=event)
    assert response.status_code == 200
    states = {item['entity_id']: item for item in response.json()['states']}
    assert states['daniel']['status'] == 'ready_to_merge'
    assert 'approved and ready to merge' in states['daniel']['headline']
