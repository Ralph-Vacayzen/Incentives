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
        return (row.Product == 'Beach Services')    or (row.DeliverOrPickupToType in settings['BEACH']['DISPATCH']['SPECIFIC'])
    
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

        attempts = ['AT2','AT3','AT4','AT5','AT6','AT7','AT8','AT9']

        if any(attempt in str(row.Comment).upper() for attempt in attempts):
            return True

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

    LSV = dda[dda.isLSV]
    B2B = dda[dda.isB2B]
    B2C = dda[dda.isB2C]










    dispatch = {
        'LSV': {
            'required':         np.count_nonzero(LSV.isRequiredWork),
            'error':            np.count_nonzero(LSV.isError),
            'efficiency':       (1 - np.count_nonzero(LSV.isError) / np.count_nonzero(LSV.isRequiredWork)) * 100,
            'bonus_percentage': 0,
            'max_bonus':        0,
            'calculated_bonus': 0,
            'disbursement':     {}
            },
        'B2B': {
            'required':         np.count_nonzero(B2B.isRequiredWork),
            'error':            np.count_nonzero(B2B.isError),
            'efficiency':       (1 - np.count_nonzero(B2B.isError) / np.count_nonzero(B2B.isRequiredWork)) * 100,
            'bonus_percentage': 0,
            'max_bonus':        0,
            'calculated_bonus': 0,
            'disbursement':     {}
            },
        'B2C': {
            'required':         np.count_nonzero(B2C.isRequiredWork),
            'error':            np.count_nonzero(B2C.isError),
            'efficiency':       (1 - np.count_nonzero(B2C.isError) / np.count_nonzero(B2C.isRequiredWork)) * 100,
            'bonus_percentage': 0,
            'max_bonus':        0,
            'calculated_bonus': 0,
            'disbursement':     {}
            }
    }

    for department in dispatch:
        for bucket in settings[department]['BUDGET']['Success Rate to Bonus Pool']:
            if bucket[0] >= dispatch[department]['efficiency'] and dispatch[department]['efficiency'] >= bucket[1]:
                dispatch[department]['bonus_percentage'] = bucket[2]
                break
    
    for department in dispatch:
        max_bonus = 0
        dates = pd.date_range(start, end)
        
        for day in dates:
            
            for bucket in settings[department]['BUDGET']['Max Bonus Pool Bucket']:
                startDate = pd.to_datetime(bucket[0]).date()
                endDate   = pd.to_datetime(bucket[1]).date()
                days      = (endDate - startDate).days + 1
                dailyRate = bucket[2] / days

                if startDate <= day.date() and day.date() <= endDate:
                    max_bonus += dailyRate
                    break
        
        dispatch[department]['max_bonus'] = round(max_bonus,2)
        dispatch[department]['calculated_bonus'] = dispatch[department]['max_bonus'] * dispatch[department]['bonus_percentage']
    
    for department in dispatch:
        dispatch[department]['disbursement'] = dict()
        for role in settings[department]['STAFF']['Role to Number in Role to Disbursement']:
            title   = role[0]
            people  = role[1]
            portion = role[2]

            dispatch[department]['disbursement'][title] = [float(people), (dispatch[department]['calculated_bonus'] * portion) / float(people)]










    with st.expander('**Dispatch Analysis**'):
        st.dataframe(dda, use_container_width=True, hide_index=True)


    with st.expander('**Dispatch Efficiency**'):
        for department in dispatch:
            st.write(department)
            with st.container(border=True):
                l, m, r = st.columns(3)
                l.metric('Required Stops',           dispatch[department]['required'])
                m.metric('Additional (Error) Stops', dispatch[department]['error'])
                r.metric('**Efficiency**',           round(dispatch[department]['efficiency'],2))
    
    
    with st.expander('**Disptach Adjusted Bonus**'):
        for department in dispatch:
            st.write(department)
            with st.container(border=True):
                l, m, r = st.columns(3)
                l.metric('Percentage of Max Bonus', dispatch[department]['bonus_percentage'])
                m.metric('Max Bonus',               dispatch[department]['max_bonus'])
                r.metric('**Bonus Due**',           dispatch[department]['calculated_bonus'])
    
    summary = []

    with st.expander('**Disptach Disbursement**'):
        for department in dispatch:
            st.write(department)

            df = pd.DataFrame(dispatch[department]['disbursement']).transpose()
            df.columns = ['People','Bonus Due']
            st.dataframe(df, use_container_width=True)

            df['Department'] = department
            summary.append(df)









    dp['PaymentDate'] = pd.to_datetime(dp['PaymentDate']).dt.date
    dp                = dp[(dp.PaymentDate >= start) & (dp.PaymentDate <= end)]









    sales = {
        'SALES': {
            'transactions':   np.sum(dp.TransactionAmount),
            'budgeted_sales': 0
            },
        'STOREFRONT': {
            'transactions':   0,
            'budgeted_sales': 0
            }
    }

    for department in sales:
        budgeted_sales = 0
        dates = pd.date_range(start, end)
        
        for day in dates:
            
            for bucket in settings[department]['BUDGET']['Budgeted Sales']:
                startDate = pd.to_datetime(bucket[0]).date()
                endDate   = pd.to_datetime(bucket[1]).date()
                days      = (endDate - startDate).days + 1
                dailyRate = bucket[2] / days

                if startDate <= day.date() and day.date() <= endDate:
                    budgeted_sales += dailyRate
                    break
        
        sales[department]['budgeted_sales']      = budgeted_sales
        sales[department]['incentive_threshold'] = sales[department]['budgeted_sales']      * settings[department]['BUDGET']['Incentive Threshold'][0]
        sales[department]['bucket']              = sales[department]['incentive_threshold'] - sales[department]['budgeted_sales']
        sales[department]['calculated_bonus']    = sales[department]['bucket']              * settings[department]['BUDGET']['Disbursment Percentage'][0]

    sales

    








    
    final = pd.concat(summary)
    final = final.reset_index()
    final = final.rename(columns={'index': 'Role'})
    final = final[['Department','Role','People','Bonus Due']]
    final = final[final['Bonus Due'] > 0]
    
    st.download_button('DOWNLOAD PAYROLL FILE', data=final.to_csv(index=False), file_name='Incentives_'+str(start)+'_'+str(end)+'.csv', mime='csv', type='primary', use_container_width=True)