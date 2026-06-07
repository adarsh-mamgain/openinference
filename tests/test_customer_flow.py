from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app, CONTROL_PLANE


async def fake_completion(payload):
    return {
        'id': 'chatcmpl_test',
        'object': 'chat.completion',
        'choices': [
            {
                'index': 0,
                'message': {'role': 'assistant', 'content': 'hello'},
                'finish_reason': 'stop',
            }
        ],
        'usage': {'prompt_tokens': 10, 'completion_tokens': 5},
    }


def test_customer_register_key_and_chat_flow(monkeypatch) -> None:
    monkeypatch.setattr(main_module, 'proxy_chat_completion', fake_completion)
    client = TestClient(app)

    register = client.post(
        '/auth/register',
        json={'email': 'owner@example.com', 'password': 'secret', 'name': 'Owner'},
    )
    assert register.status_code == 200

    me = client.get('/v1/me')
    assert me.status_code == 200
    user_id = me.json()['id']

    CONTROL_PLANE.auth.top_up_credits(user_id, 5000)

    created_key = client.post('/v1/api-keys', json={'name': 'Production'})
    assert created_key.status_code == 200
    secret = created_key.json()['secret']
    assert secret.startswith('or_live_')

    keys = client.get('/v1/api-keys')
    assert keys.status_code == 200
    assert len(keys.json()['data']) == 1

    chat = client.post(
        '/v1/chat/completions',
        headers={'Authorization': f'Bearer {secret}'},
        json={
            'model': 'deepseek-v4-flash',
            'messages': [{'role': 'user', 'content': 'hello'}],
        },
    )
    assert chat.status_code == 200
    assert chat.json()['choices'][0]['message']['content'] == 'hello'
