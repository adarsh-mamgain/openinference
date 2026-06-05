from app.litellm_proxy import build_completion_kwargs, list_model_names, resolve_model


MODEL_CONFIG = {
    'model_list': [
        {
            'model_name': 'deepseek-v4-flash',
            'litellm_params': {
                'model': 'deepseek/deepseek-chat',
                'api_key': 'os.environ/DEEPSEEK_API_KEY',
            },
        }
    ]
}


def test_list_model_names(monkeypatch) -> None:
    monkeypatch.setattr('app.litellm_proxy.load_litellm_config', lambda: MODEL_CONFIG)
    assert list_model_names() == ['deepseek-v4-flash']


def test_resolve_model(monkeypatch) -> None:
    monkeypatch.setattr('app.litellm_proxy.load_litellm_config', lambda: MODEL_CONFIG)
    model = resolve_model('deepseek-v4-flash')
    assert model['litellm_params']['model'] == 'deepseek/deepseek-chat'


def test_build_completion_kwargs(monkeypatch) -> None:
    monkeypatch.setattr('app.litellm_proxy.load_litellm_config', lambda: MODEL_CONFIG)
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'secret-key')

    kwargs = build_completion_kwargs({
        'model': 'deepseek-v4-flash',
        'messages': [{'role': 'user', 'content': 'hello'}],
    })

    assert kwargs['model'] == 'deepseek/deepseek-chat'
    assert kwargs['api_key'] == 'secret-key'
