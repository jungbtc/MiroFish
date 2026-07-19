from flask import Flask

from app.utils.locale import get_language_instruction, get_locale, set_locale, t


def test_removed_chinese_locale_resolves_to_english():
    set_locale('zh')

    assert get_locale() == 'en'
    assert get_language_instruction() == 'Please respond in English.'
    assert t('common.confirm') == 'Confirm'


def test_accept_language_uses_installed_english_translation():
    app = Flask(__name__)

    with app.test_request_context(headers={'Accept-Language': 'en-US,en;q=0.9'}):
        assert get_locale() == 'en'

    with app.test_request_context(headers={'Accept-Language': 'zh-CN,zh;q=0.9'}):
        assert get_locale() == 'en'
