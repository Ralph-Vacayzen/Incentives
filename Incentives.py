import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title='Incentives', page_icon='💰', layout="wide", initial_sidebar_state="auto", menu_items=None)

st.caption('VACAYZEN')
st.title('Incentives')
st.info('Loving the crew. Giving them an extra buck or two. Hoping above and beyond is what they do.')

l, r = st.columns(2)

start = l.date_input('Start of Period')
end   = r.date_input('End of Period', min_value=start)

settings = pd.read_json('settings.json')

tab_b2b, tab_b2c, tab_lsv, tab_sales = st.tabs(['B2B','B2C','LSV','SALES'])

with tab_b2b:

    l, r = st.columns(2)

    house_agreements = l.file_uploader(
        label='House Program Order Numbers',
        type='CSV',
        help='These order numbers will be the only orders considered in terms of activity in this analysis.')
    
    disptach_activities = r.file_uploader(
        label='Dispatch Activities',
        type='CSV',
        help='These are from the integraRental database report, Incentives_Dispatches.')
    

    if house_agreements is not None and disptach_activities is not None:

        dha = pd.read_csv(house_agreements)
        dda = pd.read_csv(disptach_activities)

        dda['Dispatch'] = pd.to_datetime(dda['Dispatch']).dt.date

        with st.expander('**Analysis**'):

            st.info('Required and irrelevant services are maintained in the settings area.')

            required = st.multiselect(
                label='Required Dispatches',
                options=dda.DeliverOrPickupToType.unique(),
                default=settings['B2B']['DISPATCH']['Required'])
            
            irrelevant = st.multiselect(
                label='Irrelevant Dispatches',
                options=dda.DeliverOrPickupToType.unique(),
                default=settings['B2B']['DISPATCH']['Irrelevant'])
            
            remaining = (set(dda.DeliverOrPickupToType.unique()) - set(settings['B2B']['DISPATCH']['Required'])) - set(settings['B2B']['DISPATCH']['Irrelevant'])
            
            additional = st.multiselect(
                label='Additional Work Dispatches',
                options=dda.DeliverOrPickupToType.unique(),
                default=remaining)
            
            st.info('Dispatches are isolated to the date range.')
            st.info('Dispatches validated based on: house agreement, required dispatch, and additional dispatch.')

            dda = dda[(dda.Dispatch >= start) & (dda.Dispatch <= end)]

            def IsHouseAgreement(row):
                return row.RentalAgreementID in dha.RentalAgreementID
            
            def IsRequiredDispatch(row):
                return row.DeliverOrPickupToType in required
            
            def IsAdditionalDispatch(row):
                return row.DeliverOrPickupToType in additional
            
            dda['house']      = dda.apply(IsHouseAgreement,     axis=1)
            dda['required']   = dda.apply(IsRequiredDispatch,   axis=1)
            dda['additional'] = dda.apply(IsAdditionalDispatch, axis=1)

            dda = dda[dda.house]
            dda = dda[dda.required | dda.additional]

            st.dataframe(dda, use_container_width=True, hide_index=True)

            st.info('Dispatches are counted.')

        
        count_required   = np.count_nonzero(dda[dda.required]['required'])
        count_additional = np.count_nonzero(dda[dda.additional]['additional'])
        efficiency       = 1 - (count_additional / count_required)

        with st.container(border=True):

            l, m, r = st.columns(3)

            l.metric(
                label='Required Dispatches',
                value=count_required
            )

            m.metric(
                label='Additional Dispatches',
                value=count_additional
            )

            r.metric(
                label='Efficiency',
                value=round(efficiency, 4),
                delta=round(efficiency - 0.97, 2)
            )