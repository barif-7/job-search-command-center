import json
from unittest.mock import patch

from jobsearch.ranking.preferences import apply_preferences, load_preferences, save_preferences
from jobsearch.ranking.fit import score_job_fit


def test_profile_roundtrip_and_isolation(tmp_path):
    a, b = tmp_path / 'a.json', tmp_path / 'b.json'
    a.write_text(json.dumps({'email': 'candidate@example.com', 'checkbox_answers': {'Consent': True}}))
    prefs = load_preferences(a)
    prefs.update(search_presets={'ios': {'label': 'Mobile', 'title_keywords': ['swift'], 'description': ''}},
                 target_presets=['ios'], profile_signals=['swift'], filter_by_presets=True, sort_by_fit=True)
    save_preferences(prefs, a)
    assert load_preferences(a) == prefs
    assert json.loads(a.read_text())['email'] == 'candidate@example.com'
    assert json.loads(a.read_text())['checkbox_answers'] == {'Consent': True}
    assert load_preferences(b)['target_presets'] == []
    jobs = [{'title': 'Swift Engineer'}, {'title': 'AI Engineer'}]
    assert apply_preferences(jobs, prefs)[0]['title'] == 'Swift Engineer'
    assert len(apply_preferences(jobs, prefs)) == 1
    assert jobs == [{'title': 'Swift Engineer'}, {'title': 'AI Engineer'}]


def test_empty_signals_and_disabled_preferences(tmp_path):
    prefs = load_preferences(tmp_path / 'missing.json')
    jobs = [{'title': 'LLM AI Platform Engineer'}]
    assert apply_preferences(jobs, prefs) == jobs
    assert score_job_fit(jobs[0], profile_signals=[], presets={})['fit_score'] == 0
    prefs['sort_by_fit'] = True
    assert apply_preferences(jobs, prefs)[0]['fit_score'] == 0


def test_client_editor_saves(tmp_path):
    from streamlit.testing.v1 import AppTest
    path = tmp_path / 'profile.json'
    path.write_text(json.dumps({'full_name': 'Test Candidate'}))
    with patch('jobsearch.ui.search_preferences.load_preferences', side_effect=lambda: load_preferences(path)), \
         patch('jobsearch.ui.search_preferences.save_preferences', side_effect=lambda prefs: save_preferences(prefs, path)):
        app = AppTest.from_string('from jobsearch.ui.search_preferences import render_search_preferences\nrender_search_preferences()').run()
        assert not app.exception
        app.text_area[0].set_value('swift, ios')
        app.checkbox[1].check()
        app.button[0].click().run()
        assert not app.exception
    assert load_preferences(path)['profile_signals'] == ['swift', 'ios']
    assert load_preferences(path)['sort_by_fit'] is True
    assert json.loads(path.read_text())['full_name'] == 'Test Candidate'
