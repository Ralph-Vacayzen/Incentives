import streamlit as st
import pandas as pd
import numpy as np
import time

st.set_page_config(page_title='Incentives - Settings', page_icon='⚙️', layout="wide", initial_sidebar_state="auto", menu_items=None)

logged_in = False

st.caption('VACAYZEN')
st.title('Settings')

if not logged_in:
    def Create_Stream(phrase):
        for word in phrase.split(' '):
            yield word + ' '
            time.sleep(0.02)

    with st.chat_message('assistant'):
        st.write_stream(Create_Stream('Be sure to save any changes after each adjustment, and **double-check the save went through.**'))


if logged_in:
    st.info('Be sure to save any changes after each adjustment, and **double-check the save went through.**')


    settings       = pd.read_json('settings.json')
    available_tabs = list(settings.columns.values)
    tabs           = st.tabs(available_tabs)

    for index, tab in enumerate(tabs):
        with tab:

            seconday_tabs = list(settings[available_tabs[index]].dropna().index.values)
            tabs_seconday = st.tabs(seconday_tabs)

            for index2, tab2 in enumerate(tabs_seconday):
                with tab2:
                    for item in settings[available_tabs[index]][seconday_tabs[index2]]:

                        st.subheader(item)

                        if item == "Disbursement Percentage":
                            settings[available_tabs[index]][seconday_tabs[index2]][item] = st.data_editor(
                                data=settings[available_tabs[index]][seconday_tabs[index2]][item],
                                use_container_width=True,
                                key=str(index)+str(index2)+item+'editor')
                        else:
                            settings[available_tabs[index]][seconday_tabs[index2]][item] = st.data_editor(
                                data=settings[available_tabs[index]][seconday_tabs[index2]][item],
                                use_container_width=True,
                                num_rows='dynamic',
                                key=str(index)+str(index2)+item+'editor')
                        
                        if st.button('SAVE', use_container_width=True, type='primary', key=str(index)+str(index2)+item+'button'):
                            settings.to_json('settings.json')
                            st.toast('Settings saved!')