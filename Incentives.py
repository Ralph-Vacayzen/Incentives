from datetime import datetime

import streamlit as st
import pandas as pd
import numpy as np

import openpyxl
import zipfile
import os


st.set_page_config(page_title='Incentives', page_icon='💰', layout="wide", initial_sidebar_state="auto", menu_items=None)

st.caption('VACAYZEN')
st.title('Incentives')
st.info('Loving the crew. Giving them an extra buck or two. Hoping above and beyond is what they do.')

l, r = st.columns(2)

start = l.date_input('Start of Period', value=pd.to_datetime('today')-pd.Timedelta(days=1), max_value=pd.to_datetime('today')-pd.Timedelta(days=1))
end   = r.date_input('End of Period',   value=pd.to_datetime('today')-pd.Timedelta(days=1), max_value=pd.to_datetime('today')-pd.Timedelta(days=1), min_value=start)

settings = pd.read_json('settings.json')

with st.expander('Uploaded Files'):
    
    file_descriptions = [
        ['Incentive_Dispatches.csv','An integraRental database report, Incentive_Dispatches.'],
        ['Incentive_Payments.csv','An integraRental database report, Incentive_Payments.'],
        ['Incentive_Beach.csv','An integraRental database report, Incentive_Beach.'],
        ['Incentive_Beach_Seasonals.csv','A tab from a Google Sheet, Beach Service Seasonals.'],
        ['Incentive_House_Agreements.csv','A Partner Program Register (PPR) report, House Agreements - All - B2B.'],
        ['Incentive_Seagrove.csv','A Shopify report: Total Sales, filtered Year to Date.'],
        ['Incentive_Baybaits.csv','A Shopify report: Total Sales, filtered Year to Date.']
    ]

    files = {
        'Incentive_Dispatches.csv': None,
        'Incentive_Payments.csv': None,
        'Incentive_House_Agreements.csv': None,
        'Incentive_Beach.csv': None,
        'Incentive_Beach_Seasonals.csv': None,
        'Incentive_Seagrove.csv': None,
        'Incentive_Baybaits.csv': None
    }


    uploaded_files = st.file_uploader(
        label='Files (' + str(len(files)) + ')',
        accept_multiple_files=True
    )

    st.info('File names are **case sensitive** and **must be identical** to the file name below.')
    st.dataframe(pd.DataFrame(file_descriptions, columns=['Required File','Source Location']), hide_index=True, use_container_width=True)










if len(uploaded_files) > 0:
    for index, file in enumerate(uploaded_files):
        files[file.name] = index

    hasAllRequiredFiles = True
    missing = []

    for file in files:
        if files[file] == None:
            hasAllRequiredFiles = False
            missing.append(file)

if len(uploaded_files) > 0 and not hasAllRequiredFiles:
    for item in missing:
        st.warning('**' + item + '** is missing and required.')


elif len(uploaded_files) > 0 and hasAllRequiredFiles:
    dha     = pd.read_csv(uploaded_files[files['Incentive_House_Agreements.csv']])
    dda     = pd.read_csv(uploaded_files[files['Incentive_Dispatches.csv']])
    dp      = pd.read_csv(uploaded_files[files['Incentive_Payments.csv']])
    bso     = pd.read_csv(uploaded_files[files['Incentive_Beach.csv']])
    bss     = pd.read_csv(uploaded_files[files['Incentive_Beach_Seasonals.csv']])
    dss     = pd.read_csv(uploaded_files[files['Incentive_Seagrove.csv']])
    bbs     = pd.read_csv(uploaded_files[files['Incentive_Baybaits.csv']])
    summary = []










    # LOGIC: LSV, B2B, B2C

    def IsBS(row):
        return (row.Product == 'Beach Services')    or (row.DeliverOrPickupToType in settings['BEACH']['DISPATCH']['SPECIFIC'])
    
    def IsLSV(row):
        return (row.Product == 'Golf Cart Rentals') or (row.DeliverOrPickupToType in settings['LSV']['DISPATCH']['SPECIFIC'])

    def IsB2B(row):
        isNotBS          = not (row.isBS)
        isNotLSV         = not (row.isLSV)
        isOnHouseProgram = row.RentalAgreementID in dha['RentalAgreementID'].to_list()
        isB2BSpecific    = row.DeliverOrPickupToType in settings['B2B']['DISPATCH']['SPECIFIC']

        return isNotBS and isNotLSV and (isOnHouseProgram or isB2BSpecific)
    
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

        return (row.DeliverOrPickupToType in settings[department]['DISPATCH']['REQUIRED'])

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
    
    # LOGIC: BEACH

    def IsSpecificBS(row):
        isSpecificProduct = row.ProductDescription in settings['BEACH']['DISPATCH']['SPECIFIC']
        isSpecificService = row.ShortDescription   in settings['BEACH']['DISPATCH']['SPECIFIC']

        return isSpecificProduct or isSpecificService
    
    def IsInRange(row):
        dates = pd.date_range(start, end)
    
        for day in dates:
            if row.RentalAgreementStartDate <= day.date() and day.date() <= row.RentalAgreementEndDate:
                return True
        
        return False
    
    def AdjustStartDate(row):
        if row.RentalAgreementStartDate < start:
            return start
        return row.RentalAgreementStartDate
    
    def AdjustEndDate(row):
        if row.RentalAgreementEndDate > end:
            return end
        return row.RentalAgreementEndDate
    
    def GetSetupDays(row):
        return len(pd.date_range(row.RentalAgreementStartDate, row.RentalAgreementEndDate))
    
    def IsBeachError(row):
        return row.ShortDescription == 'Beach Fix'








    # SECTION: LSV, B2B, B2C
    
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

    dda                     = dda.drop(columns=['isBS'])

    LSV = dda[dda.isLSV].drop(columns=['isLSV','isB2B','isB2C','isIgnored']).sort_values(by=['isError','Dispatch','RentalAgreementID'],ascending=False)
    B2B = dda[dda.isB2B].drop(columns=['isLSV','isB2B','isB2C','isIgnored']).sort_values(by=['isError','Dispatch','RentalAgreementID'],ascending=False)
    B2C = dda[dda.isB2C].drop(columns=['isLSV','isB2B','isB2C','isIgnored']).sort_values(by=['isError','Dispatch','RentalAgreementID'],ascending=False)

    # SECTION: BEACH

    bso['RentalAgreementStartDate'] = pd.to_datetime(bso['RentalAgreementStartDate']).dt.date
    bso['RentalAgreementEndDate']   = pd.to_datetime(bso['RentalAgreementEndDate']).dt.date
    bso['isSpecific']               = bso.apply(IsSpecificBS, axis=1)
    bso                             = bso[bso.isSpecific]
    bso['isInRange']                = bso.apply(IsInRange, axis=1)
    bso                             = bso[bso.isInRange]
    bso['RentalAgreementStartDate'] = bso.apply(AdjustStartDate, axis=1)
    bso['RentalAgreementEndDate']   = bso.apply(AdjustEndDate, axis=1)
    bso['SetupDays']                = bso.apply(GetSetupDays, axis=1)
    bso['isError']                  = bso.apply(IsBeachError, axis=1)

    bss['DATE']                     = pd.to_datetime(bss['DATE']).dt.date
    bss                             = bss[(start <= bss['DATE']) & (bss['DATE'] <= end)]


    with st.expander('**Dispatches**'):

        'LSV'
        LSV = st.data_editor(LSV, use_container_width=True, hide_index=True)

        'B2B'
        B2B = st.data_editor(B2B, use_container_width=True, hide_index=True)

        'B2C'
        B2C = st.data_editor(B2C, use_container_width=True, hide_index=True)

        'BEACH'
        bso = st.data_editor(bso, use_container_width=True, hide_index=True)


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
            },
        'BEACH': {                                                                  # TODO
            'required':         np.sum(bso.SetupDays) + bss.shape[0],
            'error':            np.count_nonzero(bso.isError),
            'efficiency':       (1 - np.count_nonzero(bso.isError) / (np.sum(bso.SetupDays) + bss.shape[0])) * 100,
            'bonus_percentage': 0,
            'max_bonus':        0,
            'calculated_bonus': 0,
            'disbursement':     {}
        }
    }
    
    
    
    
    
    
    



    # SECTION: SALES, STOREFRONT
    
    # OFFICE (INTEGRARENTAL)
        
    dp['PaymentDate']   = pd.to_datetime(dp['PaymentDate']).dt.date
    dp                  = dp[(dp.PaymentDate >= start) & (dp.PaymentDate <= end)]

    # BAYBAITS (CLOVER) (NO LONGER USE)
    
    # def ConvertCloverDateToDate(row):
    #     date = row['Payment Date'][:11]
    #     date = datetime.strptime(date, '%d-%b-%Y')

    #     return date.strftime('%m/%d/%Y')

        
    # bbs['Payment Date'] = bbs.apply(ConvertCloverDateToDate, axis = 1)
    # bbs['Payment Date'] = pd.to_datetime(bbs['Payment Date']).dt.date
    # bbs                 = bbs[(bbs['Payment Date'] >= start) & (bbs['Payment Date'] <= end)]

    # BAYBAITS (SHOPIFY)

    bbs['Date']         = bbs['Date'].str[:10]
    bbs['Date']         = pd.to_datetime(bbs['Date']).dt.date
    bbs                 = bbs[(bbs.Date >= start) & (bbs.Date <= end)]

    # SEAGROVE (SHOPIFY)

    dss['Date']         = dss['Date'].str[:10]
    dss['Date']         = pd.to_datetime(dss['Date']).dt.date
    dss                 = dss[(dss.Date >= start) & (dss.Date <= end)]


    sales = {
        'SALES': {
            'transactions':        np.sum(dp.TransactionAmount),
            'budgeted_sales':      0,
            'incentive_threshold': 0,
            'bucket':              0,
            'calculated_bonus':    0,
            'disbursement':        {}
            },
        'BAY BAITS': {
            'transactions':        np.sum(bbs['Total sales']),
            'budgeted_sales':      0,
            'incentive_threshold': 0,
            'bucket':              0,
            'calculated_bonus':    0,
            'disbursement':        {}
            },
        'SEAGROVE': {
            'transactions':        np.sum(dss['Total sales']),
            'budgeted_sales':      0,
            'incentive_threshold': 0,
            'bucket':              0,
            'calculated_bonus':    0,
            'disbursement':        {}
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
        sales[department]['incentive_threshold'] = sales[department]['budgeted_sales'] * settings[department]['BUDGET']['Incentive Threshold'][0]
        sales[department]['bucket']              = sales[department]['transactions']   - sales[department]['incentive_threshold']
        if sales[department]['bucket'] <= 0:       sales[department]['bucket']         = 0
        sales[department]['calculated_bonus']    = sales[department]['bucket']         * settings[department]['BUDGET']['Disbursment Percentage'][0]
    
    for department in sales:
        sales[department]['disbursement'] = dict()
        for role in settings[department]['STAFF']['Role to Number in Role to Disbursement']:
            title   = role[0]
            people  = role[1]
            portion = role[2]

            sales[department]['disbursement'][title] = [
                float(people),
                (sales[department]['calculated_bonus'] * portion),
                (sales[department]['calculated_bonus'] * portion) / float(people)
                ]
    
    for department in sales:
        df = pd.DataFrame(sales[department]['disbursement']).transpose()
        df.columns = ['People','Bonus Due','Bonus Divided Equally']
        df['Department'] = department
        summary.append(df)






    




    with st.expander('**Transactions**'):

        'OFFICE'
        st.dataframe(dp, use_container_width=True, hide_index=True)

        'BAY BAITS'
        st.dataframe(bbs, use_container_width=True, hide_index=True)

        'BAY BAITS @ SEAGROVE'
        st.dataframe(dss, use_container_width=True, hide_index=True)

    



    with st.expander('**Efficiency**'):
        for department in dispatch:
            st.write(department)
            with st.container(border=True):
                l, m, r = st.columns(3)
                l.metric('Required Stops',           dispatch[department]['required'])
                dispatch[department]['error'] = m.number_input('Additional (Error) Stops', value=dispatch[department]['error'], key=str(department)+str(dispatch))

                dispatch[department]['efficiency'] = (1 - (dispatch[department]['error'] / dispatch[department]['required'])) * 100

                r.metric('**Efficiency**',           round(dispatch[department]['efficiency'],2))
        
        for department in sales:
            st.write(department)
            with st.container(border=True):
                l, m, r = st.columns(3)
                l.metric('Budgeted Sales',      round(sales[department]['budgeted_sales'],2))
                m.metric('Incentive Threshold', round(sales[department]['incentive_threshold'],2))
                r.metric('Transations',         round(sales[department]['transactions'],2), round(sales[department]['transactions'] - sales[department]['incentive_threshold'],2))
    

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

            dispatch[department]['disbursement'][title] = [
                float(people),
                (dispatch[department]['calculated_bonus'] * portion),
                (dispatch[department]['calculated_bonus'] * portion) / float(people)
                ]
            
    for department in dispatch:
        df = pd.DataFrame(dispatch[department]['disbursement']).transpose()
        df.columns = ['People','Bonus Due','Bonus Divided Equally']
        df['Department'] = department
        summary.append(df)
    



    with st.expander('**Adjusted Bonus**'):
        for department in dispatch:
            st.write(department)
            with st.container(border=True):
                l, m, r = st.columns(3)
                l.metric('Percentage of Max Bonus', dispatch[department]['bonus_percentage'])
                m.metric('Max Bonus',               dispatch[department]['max_bonus'])
                r.metric('**Bonus Due**',           dispatch[department]['calculated_bonus'])
        
        for department in sales:
            st.write(department)
            with st.container(border=True):
                l, m, r = st.columns(3)
                l.metric('Bonus Bucket',           round(sales[department]['bucket'],2))
                m.metric('Disbusement Percentage', settings[department]['BUDGET']['Disbursment Percentage'][0])
                r.metric('**Bonus Due**',          round(sales[department]['calculated_bonus'],2))
                




    with st.expander('**Disbursement**'):
        for department in dispatch:
            st.write(department)

            df = pd.DataFrame(dispatch[department]['disbursement']).transpose()
            df.columns = ['People','Bonus Due','Bonus Divided Equally']
            st.dataframe(df, use_container_width=True)

        for department in sales:
            st.write(department)

            df = pd.DataFrame(sales[department]['disbursement']).transpose()
            df.columns = ['People','Bonus Due','Bonus Divided Equally']
            st.dataframe(df, use_container_width=True)
    









    errors = [
        [LSV[LSV['isError']],'LSV'],
        [B2B[B2B['isError']],'B2B'],
        [B2C[B2C['isError']],'B2C'],
        [bso[bso['isError']],'BEACH']
    ]

    with zipfile.ZipFile('errors.zip', 'w') as ezip:
        for error in errors:
            error[0].to_csv(f'{error[1]}.csv', index=False)
            ezip.write(f'{error[1]}.csv')
            os.remove(f'{error[1]}.csv')
    
    with open('errors.zip','rb') as error_file:
        st.download_button('DOWNLOAD ERRORS FILE', data=error_file, file_name='Errors_'+str(start)+'_'+str(end)+'.zip', type='secondary', use_container_width=True)









    with zipfile.ZipFile('incentives.zip', 'w') as izip:
        for department in summary:
            df = department.reset_index()
            df = df.rename(columns={'index': 'Role'})
            df = df[['Department','Role','People','Bonus Due','Bonus Divided Equally']]
            df = df[df['Bonus Due'] > 0]

            if len(df) > 0:
                file_name = df['Department'][0]
                df.to_csv(f'{file_name}.csv', index=False)
                izip.write(f'{file_name}.csv')
                os.remove(f'{file_name}.csv')
    
    with open('incentives.zip','rb') as error_file:
        st.download_button('DOWNLOAD PAYROLL FILE', data=error_file, file_name='Incentives_'+str(start)+'_'+str(end)+'.zip', type='primary', use_container_width=True)