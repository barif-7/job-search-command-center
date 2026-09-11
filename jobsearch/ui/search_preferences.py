"""Client editor for the active candidate profile's search preferences."""
import pandas as pd
import streamlit as st

from jobsearch.ranking.preferences import load_preferences, save_preferences


def render_search_preferences() -> dict:
    try:
        preferences = load_preferences()
    except (ValueError, OSError) as exc:
        st.error(f'Could not read candidate search preferences: {exc}')
        return {}
    with st.expander('Search preferences'):
        st.caption('Saved to the active candidate profile on this installation. Preset filters match any selected preset against job titles. Existing feed filters still apply.')
        rows = [dict(id=key, label=preset['label'], keywords=', '.join(preset['title_keywords']),
                     description=preset.get('description', ''), selected=key in preferences['target_presets'])
                for key, preset in preferences['search_presets'].items()]
        with st.form('search_preferences'):
            edited = st.data_editor(pd.DataFrame(rows, columns=['id', 'label', 'keywords', 'description', 'selected']),
                                    num_rows='dynamic', hide_index=True, use_container_width=True,
                                    column_config={'selected': st.column_config.CheckboxColumn('Use preset', default=False)},
                                    key='profile_preset_editor')
            signals = st.text_area('Fit signals (comma-separated)', value=', '.join(preferences['profile_signals']))
            filtering = st.checkbox('Filter feed by selected presets', value=preferences['filter_by_presets'])
            ranking = st.checkbox('Sort feed by profile fit', value=preferences['sort_by_fit'])
            if st.form_submit_button('Save search preferences'):
                try:
                    presets, selected = {}, []
                    for row in edited.fillna('').to_dict('records'):
                        key = str(row['id']).strip()
                        if key in presets:
                            raise ValueError('Preset IDs must be unique.')
                        presets[key] = dict(label=str(row['label']).strip(),
                                            title_keywords=[w.strip() for w in str(row['keywords']).split(',') if w.strip()],
                                            description=str(row['description']))
                        if row['selected']:
                            selected.append(key)
                    save_preferences(dict(search_presets=presets, target_presets=selected,
                                          profile_signals=[w.strip() for w in signals.split(',') if w.strip()],
                                          filter_by_presets=filtering, sort_by_fit=ranking))
                except (ValueError, OSError) as exc:
                    st.error(str(exc))
                else:
                    st.rerun()
    return preferences
