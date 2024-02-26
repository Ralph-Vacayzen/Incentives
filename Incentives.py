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

with st.expander('Files'):

    dispatches = st.file_uploader(
        label='**Dispatch Activities**',
        type='CSV',
        help='These are from the integraRental database report, Incentives_Dispatches.')

    prepayments = st.file_uploader(
        label='**Prepayments**',
        type='CSV',
        help='These are from the integraRental database report, Incentives_Prepayments.')
    
    house_agreements = st.file_uploader(
        label='**House Program Order Numbers**',
        type='CSV',
        help='These order numbers will be the only orders considered in terms of activity in this analysis.')




if house_agreements is not None and dispatches is not None and prepayments is not None:

    dha = pd.read_csv(house_agreements)
    dda = pd.read_csv(dispatches)
    dp  = pd.read_csv(prepayments)


    def IsBS(row):
        return (row.Product == 'Beach Services') or (row.DeliverOrPickupToType == 'BEACH SERVICE SET UP') # TODO: Implement beach service logic

    def IsLSV(row):
        return (row.Product == 'Golf Cart Rentals') or (row.DeliverOrPickupToType in settings['LSV']['DISPATCH']['SPECIFIC'])

    def IsB2B(row):
        isNotBS           = not (row.isBS)
        isNotLSV          = not (row.isLSV)
        isOnHouseProgram  = row.RentalAgreementID in dha['RentalAgreementID'].to_list()

        return isNotBS and isNotLSV and isOnHouseProgram
    
    def IsB2C(row):
        return not (row.isBS or row.isLSV or row.isB2B)
    
    def IsIgnored(row):
        ignoreList = ['ABANDONED', 'MISC ERRAND']

        return row.DeliverOrPickupToType in ignoreList
    
    timestamps = {
        'LSV': {},
        'B2B': {},
        'B2C': {}
    }

    def IdentifyTimestamps(row):

        department = None

        if   row.isLSV: department = 'LSV'
        elif row.isB2B: department = 'B2B'
        elif row.isB2C: department = 'B2C'

        if department == None: return

        if row.DeliverOrPickupToType in settings[department]['DISPATCH']['TIMESTAMP']:
            if row.RentalAgreementID not in timestamps[department]:
                timestamps[department][row.RentalAgreementID] = set()
                timestamps[department][row.RentalAgreementID].add(row.Dispatch)
            else:
                timestamps[department][row.RentalAgreementID].add(row.Dispatch)
    
    def IsRequiredWork(row):

        department = None

        if   row.isLSV: department = 'LSV'
        elif row.isB2B: department = 'B2B'
        elif row.isB2C: department = 'B2C'

        if department == None: return False

        return row.DeliverOrPickupToType in settings[department]['DISPATCH']['REQUIRED']

    def IsAdditionalWork(row):

        department = None

        if   row.isLSV: department = 'LSV'
        elif row.isB2B: department = 'B2B'
        elif row.isB2C: department = 'B2C'

        if department == None: return False

        return row.DeliverOrPickupToType not in settings[department]['DISPATCH']['REQUIRED']
    
    def IsError(row):

        department = None

        if   row.isLSV: department = 'LSV'
        elif row.isB2B: department = 'B2B'
        elif row.isB2C: department = 'B2C'

        if department == None: return False

        if row.isAdditionalWork and row.RentalAgreementID in timestamps[department]:
            if   row.Dispatch                             in timestamps[department][row.RentalAgreementID]: return True
            elif row.Dispatch - pd.Timedelta(days=1)      in timestamps[department][row.RentalAgreementID]: return True
            elif row.Dispatch - pd.Timedelta(days=2)      in timestamps[department][row.RentalAgreementID]: return True

        return False
    



    dda['Dispatch']         = pd.to_datetime(dda['Dispatch']).dt.date
    dda                     = dda[(dda.Dispatch >= start) & (dda.Dispatch <= end)]
    dda['isBS']             = dda.apply(IsBS,      axis=1)
    dda['isLSV']            = dda.apply(IsLSV,     axis=1)
    dda['isB2B']            = dda.apply(IsB2B,     axis=1)
    dda['isB2C']            = dda.apply(IsB2C,     axis=1)
    dda['isIgnored']        = dda.apply(IsIgnored, axis=1)
    dda                     = dda[~dda['isIgnored']]

    dda.apply(IdentifyTimestamps, axis=1)

    dda['isRequiredWork']   = dda.apply(IsRequiredWork,   axis=1)
    dda['isAdditionalWork'] = dda.apply(IsAdditionalWork, axis=1)
    dda['isError']          = dda.apply(IsError,          axis=1)


    with st.expander('Showing the work'):
        st.dataframe(dda, use_container_width=True, hide_index=True)
    
    LSV = dda[dda.isLSV]
    B2B = dda[dda.isB2B]
    B2C = dda[dda.isB2C]

    st.subheader('Efficiency')

    st.write('**LSV**')
    with st.container(border=True):
        eLSVrequired   = np.count_nonzero(LSV.isRequiredWork)
        eLSVerror      = np.count_nonzero(LSV.isError)
        # eLSVefficiency = TODO

        l, m, r = st.columns(3)
        l.metric('Required Stops', np.count_nonzero(LSV.isRequiredWork))
        m.metric('Additional (Error) Stops', np.count_nonzero(LSV.isError))
        r.metric('**Efficiency**',)