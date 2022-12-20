from flask import jsonify
from datetime import date
import pandas as pd
import numpy as np
import datetime
import holidays
from pandas.core.frame import DataFrame
from scipy.optimize import fsolve
import calendarNew as calendar
import copy
import sys, os
import logging 

def xirr(transactions):
    years = [(ta[0] - transactions[0][0]).days / 365.0 for ta in transactions]
    residual = 1
    step = 0.05
    guess = 0.05
    epsilon = 0.0001
    limit = 10000
    while abs(residual) > epsilon and limit > 0:
        limit -= 1
        residual = 0.0
        for i, ta in enumerate(transactions):
            residual += ta[1] / pow(guess, years[i])
        if abs(residual) > epsilon:
            if residual > 0:
                guess += step
            else:
                guess -= step
                step /= 2.0
    return guess-1

def return_forward_months(anomes,qtd,actualmonth=True):
    if actualmonth == True:
        meses = [anomes]
    else:
        meses = []
    mes = anomes
    for i in range(0,qtd):
        if (mes // 10**0 % 100) == 12:
            mes = mes - 11
            mes = mes + 100
        else:
            mes = mes + 1
        meses.append(int(mes))
    return meses

def interest_rate(tj,*data):
    A,P,M = data
    return A/30 - P*( (tj*(np.power(1+tj,M))) / ( np.power(1+tj,M) - 1) )

def calculate_interest_rate(interest_rate, *data):
    
    principal, amortization, installDates, rDisbursementDate = data
    
    soma = 0

    for i in installDates:

        days = ( i - ( date(rDisbursementDate.year, rDisbursementDate.month, rDisbursementDate.day) ) ).days

        soma = soma + ( 1/( (1+interest_rate)**( (days)/30.0) ) )
    
    return amortization - np.round(principal/soma,6)

def calculate_amortization_amount(principal, interest_rate, installDates, rDisbursementDate):
    
    days_each_month = []
    
    soma = 0

    for i in installDates:

        days = ( i - ( date(rDisbursementDate.year, rDisbursementDate.month, rDisbursementDate.day) ) ).days

        days_each_month.append(days)

        soma = soma + ( 1/( (1+interest_rate)**( (days)/30.0) ) )
    
    return round(principal/soma,6)

def returnDaysEachMonth(period, rPaymentDate, rDisbursementDate):
    
    vecHolidays = [i[0] for i in holidays.BRA(years=date.today().year).items()] + [i[0] for i in holidays.BRA(years=date.today().year+1).items()] + [i[0] for i in holidays.BRA(years=date.today().year+2).items()]
    
    days_each_month = []
    
    installInterestDate = []
    
    installDates = []
    
    paymentDay = rPaymentDate.day
    
    monthIndex = 1
    
    year = rPaymentDate.year
    
    month = rPaymentDate.month
    
    for i in range(1,period+1):
        add = 1
        loop = True
        while loop:
            try:
                if i == 1:
                    # First install must be different
    
                    day2 = date(rDisbursementDate.year, rDisbursementDate.month, rDisbursementDate.day)

                    day1 = date(rPaymentDate.year, rPaymentDate.month, rPaymentDate.day)
            
                    year = calendar._nextmonth(day1.year,day1.month)[0]
                        
                    month = calendar._nextmonth(day1.year,day1.month)[1]
            
                else:
                    
                    try:
                        day1 = date(year, month, paymentDay)
                        
                        year = calendar._nextmonth(day1.year,day1.month)[0]
                        
                        month = calendar._nextmonth(day1.year,day1.month)[1]
                        
                    except:
                        
                        day1 = date( year, month , paymentDay - add) + datetime.timedelta(days=1)
                        
                        if ( day1 - day2 ).days < 31:
                            
                            #getting last day of month
                            lastday = calendar.monthrange(day2.year, day2.month)[1]
                            
                            day1 = date(day2.year, day2.month, day2.day) + datetime.timedelta(days=31)
                        
                        year = calendar._nextmonth(day1.year,day1.month)[0]
                        
                        month = calendar._nextmonth(day1.year,day1.month)[1]
                        
                
                days = ( day1 - day2 ).days
                days_each_month.append(days)
                installInterestDate.append(day1)
                day2 = copy.deepcopy(day1)
                
                PayDay = copy.deepcopy(day1)
                # verificando se o dia não é feriado ou dia da semana
                while (PayDay.weekday() > 4) or (PayDay in vecHolidays):
                
                    if PayDay.weekday() > 4:

                        PayDay = PayDay + datetime.timedelta(days=(7-day1.weekday()))

                    if PayDay in vecHolidays:

                        PayDay = PayDay + datetime.timedelta(days=1)
                
                installDates.append(PayDay)
                
                #fixing the new payment date
                paymentDay = day1.day
                
                loop = False
            except:
                add = add + 1
    
    return days_each_month, installInterestDate, installDates

def amortization_schedule_right(principal, interest_rate, period, rPaymentDate, rDisbursementDate):
    
    months = return_forward_months(rDisbursementDate.year*100+rDisbursementDate.month,period,actualmonth=True)
    
    days_each_month, installDates, payDay = returnDaysEachMonth(period, rPaymentDate, rDisbursementDate)
    
    amortization_amount = calculate_amortization_amount(principal, interest_rate, installDates, rDisbursementDate)
    
    number = 1
    
    balance = 1*principal
    
    installments = []
    
    while number <= period:
        
        interest = balance * (np.power((1+interest_rate),(days_each_month[number-1]/30))-1) # quantidade de dias no mes
        principal = amortization_amount - interest
        balance = balance - principal
        installments.append(dict(installDates=installDates[number-1],payDayDates=payDay[number-1],number=number, amortization_amount=amortization_amount, interest=round(interest,6), principal=round(principal,6), balance=round(balance,6) if balance > 0.001 else 0))
        number += 1
        
    return installments, amortization_amount

def amortization_schedule(principal, interest_rate, period, rPaymentDate, rDisbursementDate):
    
    months = return_forward_months(rDisbursementDate.year*100+rDisbursementDate.month,period,actualmonth=True)
    
    days_each_month, installDates, payDay = returnDaysEachMonth(period, rPaymentDate, rDisbursementDate)
    
    amortization_amount = calculate_amortization_amount(principal, interest_rate, installDates, rDisbursementDate)
    
    number = 1
    
    balance = 1*principal
    
    balanceAdjusted = 1*principal
    
    installments = []
    
    interestBiggerThanPrincipal = 0
    
    while number <= period:
        
        # não sou a favor disso, mas aparentemente não é a matemática que está valendo neste negócio.
        
        interest = ( balance * (np.power((1+interest_rate),(days_each_month[number-1]/30))-1) ) # quantidade de dias no mes
        interestAdjusted = interest + interestBiggerThanPrincipal# quantidade de dias no mes
        
        if interest > amortization_amount:
            
            interestBiggerThanPrincipal = (interest - amortization_amount)/(period-number) + interestBiggerThanPrincipal*(period-number)
            
            interestAdjusted = amortization_amount*1.0
        
        # Caso queira voltar a conta correta, deve-se apenas tirar esse if e deletar a variável interestBiggerThanPrincipal
        
        principal = amortization_amount - interest
        
        principalAdjusted = amortization_amount - interestAdjusted
        
        balance = balance - principal
        
        balanceAdjusted = balance - principalAdjusted
        
        installments.append(dict(installDates=installDates[number-1],payDayDates=payDay[number-1],number=number, amortization_amount=amortization_amount, interest=interestAdjusted, principal=principalAdjusted, balance=balanceAdjusted if balanceAdjusted > 0.001 else 0))
        number += 1
        
    return installments, amortization_amount

# iof_interest_rate=0.000041, iof_max_rate=0.015
#def return_iof_fee( amounts_installs, amount, period, rPaymentDate, rDisbursementDate, iof_interest_rate=0.0000559, iof_max_rate=0.0204):
def return_iof_fee( amounts_installs, amount, period, rPaymentDate, rDisbursementDate, iof_interest_rate=0.000041, iof_max_rate=0.015):
    
    days_each_month, installDates, _ = returnDaysEachMonth(period, rPaymentDate, rDisbursementDate)
    
    total_iof = []
    
    for j,i in enumerate(amounts_installs):
        
        #days_iof = (installDates[j] - date(rDisbursementDate.year, rDisbursementDate.month, rDisbursementDate.day)).days
        
        days_iof = np.sum(days_each_month[:j+1])
        #if days_iof > 365:
        #    days_iof = 365
        
        total_iof.append(i*iof_interest_rate*days_iof)
    
    # sempre perguntar se essa regra ainda existe
    iof_fee = sum(total_iof)+ amounts_installs.sum()*0.0038
    iof_fee_2 = amounts_installs.sum()*iof_max_rate
    iof_fee_2 = iof_fee_2 + amounts_installs.sum()*0.0038
    
    if iof_fee_2 < iof_fee:
        iof_fee = iof_fee_2
        
    return round(iof_fee,6)
    
def reverse_calculate_amortization_amount(paymentCapacity, interest_rate, period, rPaymentDate, rDisbursementDate):

    days_each_month, installDates, _ = returnDaysEachMonth(period, rPaymentDate, rDisbursementDate)
    
    days_each_month = []
    
    for i in installDates:
        
        days = ( i - (date(rDisbursementDate.year, rDisbursementDate.month, rDisbursementDate.day))).days
        
        days_each_month.append(days)
    
    return paymentCapacity*sum(1/((1+interest_rate)**(np.array(days_each_month)/30)))

# iof_interest_rate=0.000041, iof_max_rate=0.015
#def reverse_return_iof_fee( amounts_installs, amount, period, rPaymentDate, rDisbursementDate, iof_interest_rate=0.0000559, iof_max_rate=0.0204):
def reverse_return_iof_fee( amounts_installs, amount, period, rPaymentDate, rDisbursementDate, iof_interest_rate=0.000041, iof_max_rate=0.015):
    
    days_each_month, installDates, _ = returnDaysEachMonth(period, rPaymentDate, rDisbursementDate)
    
    total_iof = []
    
    for j,i in enumerate(amounts_installs):
        
        #days_iof = (installDates[j] - date(rDisbursementDate.year, rDisbursementDate.month, rDisbursementDate.day)).days
        
        days_iof = np.sum(days_each_month[:j+1])
        
        #if days_iof > 365:
        #    days_iof = 365
        
        total_iof.append(i*iof_interest_rate*days_iof)
    
    iof_fee = sum(total_iof) + amount*0.0038
    
    iof_fee_2 = amount*iof_max_rate
    iof_fee_2 = iof_fee_2 + amount*0.0038
    
    if iof_fee_2 < iof_fee:
        iof_fee = iof_fee_2
        
    return round(iof_fee,6)
    
def calculate_amortization_schedule_with_taxes(amountWithFees, initial_amount, interest_rate, period=12, iof=True, adjusted=True, rPaymentDate=datetime.datetime.today(), rDisbursementDate=datetime.datetime.today()):

    amount = amountWithFees
    
    installments, installAmount = amortization_schedule_right(amount, interest_rate, period, rPaymentDate, rDisbursementDate)

    installments = pd.DataFrame(installments)
        
    iof_fee = return_iof_fee( installments['principal'].values, amount, period, rPaymentDate, rDisbursementDate)
    
    if iof == False:
        
        iof_fee = 0
    
    if adjusted:
        
        final_installments, installAmount = amortization_schedule(amount+iof_fee, interest_rate, period, rPaymentDate, rDisbursementDate)
        final_installments = pd.DataFrame(final_installments)

    else:
        
        final_installments, installAmount = amortization_schedule_right(amount+iof_fee, interest_rate, period, rPaymentDate, rDisbursementDate)
        final_installments = pd.DataFrame(final_installments)
    
    """
    array_irr = list(final_installments['amortization_amount'].values)
    array_irr.insert(0,-initial_amount)

    cet = np.irr(array_irr)
    annualCet = (1+cet)**12-1
    """
    
    array_irr = [ (i[1], i[0]) for i in final_installments[['amortization_amount','installDates']].values ]
    
    addDay = datetime.date(rDisbursementDate.year, rDisbursementDate.month, rDisbursementDate.day)
    
    array_irr.insert(0,(datetime.date(addDay.year, addDay.month, addDay.day),-initial_amount))
    
    annualCet = np.round(xirr(array_irr),6)
    
    cet = ((annualCet+1)**(1/12))-1
    
    # Norma BACEN
    
    cet = round(((annualCet+1)**(30/365))-1,6)

    annualCet = round(((1+cet)**12) - 1,6)
    
    return final_installments.to_dict(), cet, annualCet, iof_fee, installAmount
    
def find_pre_approved_with_fees(paymentCapacity, interest_rate, period=12, rPaymentDate=datetime.datetime.today(), rDisbursementDate=datetime.datetime.today()):
    
    amount_wiof = reverse_calculate_amortization_amount(paymentCapacity, interest_rate, period, rPaymentDate, rDisbursementDate)
    
    #doing it with maximum iof possible
    installments, _ = amortization_schedule(1, interest_rate, period, rPaymentDate, rDisbursementDate)
    installments = pd.DataFrame(installments)
    
    iof_fee = reverse_return_iof_fee(installments['principal'].values, 1, period, rPaymentDate, rDisbursementDate)
    
    #doing it with maximum iof possible
    final_installments, _ = amortization_schedule(amount_wiof*(1-iof_fee), interest_rate, period, rPaymentDate, rDisbursementDate)
    final_installments = pd.DataFrame(final_installments)
    
    final_iof = return_iof_fee( final_installments['principal'].values, np.round(amount_wiof*(1-iof_fee),4), period, rPaymentDate, rDisbursementDate)
    
    #doing it with maximum iof possible
    final_installments, _ = amortization_schedule(np.round(amount_wiof-final_iof,4), interest_rate, period, rPaymentDate, rDisbursementDate)
    final_installments = pd.DataFrame(final_installments)
    
    pre_appr_w_fees = reverse_calculate_amortization_amount(final_installments['amortization_amount'].values[0], interest_rate, period, rPaymentDate, rDisbursementDate)
    
    return pre_appr_w_fees
    
def paymentCapacityPriceTable(request, gyraFeesPath='./install_csv/gyra_fees.csv'):
    
    gyra_fees = pd.read_csv(gyraFeesPath)
    
    try:
        
        rPaymentDate = datetime.datetime.strptime(request.args.get('PaymentDate'), '%d-%m-%Y')
        
        rDisbursementDate = datetime.datetime.strptime(request.args.get('DisbursementDate'), '%d-%m-%Y')
        
        paymentCapacity = np.float(request.args.get('paymentCapacity'))
        
        if paymentCapacity < 0:
            paymentCapacity = 0
        
        partner = request.args.get('Partner')
        
        fees = eval(request.args.get('Fees'))
        
        iof_fee = eval(request.args.get('Iof'))

        try:
            bankFeeRate = np.float(request.args.get('BankFeeRate'))
            gyra_fees.loc[:,'bankFee'] = bankFeeRate
        except:
            pass
        
        try:
            risk_group = int(request.args.get('riskGroup'))
        except:
            risk_group = 1
        
        try:
            interest_rate = round(float(request.args.get('interestRate'))/100,6)
            interestGiven = True
        except:
            interest_rate = None
            interestGiven = False
            
        try:
            adjusted = eval(request.args.get('Adjusted'))
        except:
            adjusted = False

        try:
            # Arredondar o paymentCapacity
            rounding = eval(request.args.get('Round'))
        except:
            rounding = True
        
        if any(partner in sub for sub in list(gyra_fees['type'].unique())) == False:
            
            partner = 'GYRA'

        if risk_group not in list(gyra_fees['riskGroup'][(gyra_fees['type'].str.contains(partner))].unique()):

            risk_group = gyra_fees['riskGroup'][(gyra_fees['type'].str.contains(partner))].min()

        pre_approved = { 'choices' : [] }

        #for period in gyra_fees['period'][(gyra_fees['riskGroup'] == risk_group)].unique(): #[6,9,12,18,24]:
        for period in [3,6,9,12,18,24]: #[6,9,12,18,24]:
            
            #print(interestGiven)
            
            if interestGiven == False:
                
                interest_rate = round(float(gyra_fees['interest'][(gyra_fees['period'] == period) & (gyra_fees['type'].str.contains(partner)) & (gyra_fees['riskGroup'] == risk_group)].max()),6)

            preaprwfees = find_pre_approved_with_fees(paymentCapacity, interest_rate, period, rPaymentDate, rDisbursementDate)
            
            # Working with Fees
            
            if fees == True:
                
                detailed_fees = {}
                
                int_fees = 0.0
                
                for col in list(gyra_fees.columns):
                    
                    if 'Fee' in col:
                        
                        try:
                            fee = gyra_fees[col][(gyra_fees['period'] == period) & (gyra_fees['type'].str.contains(partner))].max()
                        except:
                            fee = gyra_fees[col][(gyra_fees['type'].str.contains(partner))].max()
                        
                        detailed_fees[col] = fee
            
                for key in detailed_fees.keys():

                    if key not in ['gyraMaisFee','bankFee']:

                        detailed_fees['gyraMaisFee'] = float(np.clip(detailed_fees['gyraMaisFee']-detailed_fees[key],0,10))

                for key in detailed_fees.keys():

                    int_fees = int_fees + detailed_fees[key]
                
                preapr = preaprwfees/(1+(int_fees))
                
                if rounding:
                    preapr = np.ceil(preapr/5000)*5000
                else:
                    preapr = np.round(preapr/100,0)*100
                
                feesValue = 0
                
                for key in detailed_fees.keys():
                    
                    detailed_fees[key] = detailed_fees[key]*preapr
                    
                    feesValue = feesValue + detailed_fees[key]
                
                table, cet, acet, iofval, installAmount = calculate_amortization_schedule_with_taxes( preapr + feesValue, preapr,  interest_rate, period, iof_fee, adjusted, rPaymentDate, rDisbursementDate)
                
                preaprwfees = preapr + feesValue + iofval
                
                pre_approved['choices'].append(
                    dict(months=int(period),preApproved=preapr,interestRate=interest_rate,
                    preApprovedWithFees=preaprwfees,totalfeesRate=int_fees,separatedFees=detailed_fees,
                    amortizationTable=table,annualCet=acet,Cet=cet,
                    Iof=iofval,DisbursementDate=rDisbursementDate,installAmount=installAmount,
                    totalFinalAmount=installAmount*period)
                )

            else:

                preapr = np.round(preaprwfees/100,0)*100
                
                table, cet, acet, iofval, installAmount = calculate_amortization_schedule_with_taxes(preapr, preapr, interest_rate, period, iof_fee, adjusted, rPaymentDate, rDisbursementDate)
                
                preaprwfees = preapr+iofval
                
                pre_approved['choices'].append(
                    dict(months=int(period),preApproved=preapr,preApprovedWithFees=float(preaprwfees),
                    interestRate=interest_rate,amortizationTable=table,annualCet=acet,
                    Cet=cet,Iof=iofval,DisbursementDate=rDisbursementDate,
                    installAmount=installAmount,totalFinalAmount=installAmount*period)
                )


        pre_approved['partner'] = partner

        return pre_approved
    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        logging.basicConfig(filename='app.log', filemode='w+', format='%(name)s - %(levelname)s - %(message)s')
        logging.error(exc_type + ' ' + fname + ' ' +exc_tb.tb_lineno)
        return jsonify({'Error' : 'Not a valid request.'})
    
def priceTable(request, gyraFeesPath='./install_csv/gyra_fees.csv'):

    gyra_fees = pd.read_csv(gyraFeesPath)
    
    try:
        
        rPaymentDate = datetime.datetime.strptime(request.args.get('PaymentDate'), '%d-%m-%Y')
        
        rDisbursementDate = datetime.datetime.strptime(request.args.get('DisbursementDate'), '%d-%m-%Y')
        
        preapr = np.float(request.args.get('preApproved'))
        
        if preapr < 0:
            preapr = 0 
        
        interest_rate = round(float(request.args.get('interestRate'))/100,6)
        
        period = int(request.args.get('Period'))
        
        fees = eval(request.args.get('Fees'))
        
        iof_fee = eval(request.args.get('Iof'))
        
        partner = request.args.get('Partner')

        try:
            bankFeeRate = np.float(request.args.get('BankFeeRate'))
            gyra_fees.loc[:,'bankFee'] = bankFeeRate
        except:
            pass
        
        try:
            adjusted = eval(request.args.get('Adjusted'))
        except:
            adjusted = False
        
        if any(partner in sub for sub in list(gyra_fees['type'].unique())) == False:
            
            partner = 'GYRA'

        pre_approved = { 'choices' : [] }
        
        # Working with Fees
        
        if fees == True and partner != None:
                
            detailed_fees = {}
                
            for col in list(gyra_fees.columns):
                    
                if 'Fee' in col:
                    
                    try:
                        fee = gyra_fees[col][(gyra_fees['period'] == period) & (gyra_fees['type'].str.contains(partner))].max()
                    except:
                        fee = gyra_fees[col][(gyra_fees['type'].str.contains(partner))].max()
                        
                    detailed_fees[col] = fee
            
            
            for key in detailed_fees.keys():
                
                if key not in ['gyraMaisFee','bankFee']:
                    
                    detailed_fees['gyraMaisFee'] = float(np.clip(detailed_fees['gyraMaisFee']-detailed_fees[key],0,10))
                    
            int_fees = 0.0
            preaprwfees = preapr + 0.0
            
            for key in detailed_fees.keys():
                int_fees = int_fees + detailed_fees[key]
                detailed_fees[key] = detailed_fees[key]*preapr
                preaprwfees = preaprwfees + float(detailed_fees[key])
                
            #preapr = np.round(preapr/100,0)*100
            
            table, cet, acet, iofval, installAmount = calculate_amortization_schedule_with_taxes(preaprwfees, preapr, interest_rate, period, iof_fee, adjusted, rPaymentDate, rDisbursementDate)
            
            preaprwfees = preaprwfees + iofval
            pre_approved['choices'].append(
                dict(months=int(period),preApproved=preapr,interestRate=interest_rate,
                preApprovedWithFees=preaprwfees,totalfeesRate=int_fees,separatedFees=detailed_fees,
                amortizationTable=table,annualCet=acet,Cet=cet,Iof=iofval,DisbursementDate=rDisbursementDate,
                installAmount=installAmount,totalFinalAmount=installAmount*period
                )
            )

        else:

            #preapr = np.round(preapr/100,0)*100
            
            table, cet, acet, iofval, installAmount = calculate_amortization_schedule_with_taxes(preapr, preapr, interest_rate, period, iof_fee, adjusted, rPaymentDate, rDisbursementDate)
            
            preaprwfees = preapr + iofval

            pre_approved['choices'].append(
                dict(months=int(period),preApproved=preapr,preApprovedWithFees=preaprwfees,
                interestRate=interest_rate,amortizationTable=table,annualCet=acet,
                Cet=cet,Iof=iofval,DisbursementDate=rDisbursementDate,
                installAmount=installAmount,totalFinalAmount=installAmount*period
                )
            )
        
        #Ending
        pre_approved['partner'] = partner

        return pre_approved
        
    except Exception as e:
        
        #print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        logging.basicConfig(filename='app.log', filemode='w+', format='%(name)s - %(levelname)s - %(message)s')
        logging.error(exc_type + ' ' + fname + ' ' +exc_tb.tb_lineno)
        return jsonify({'Error' : 'Not a valid request.'})

def calculate_inverse_interest_amount(request):

    try:

        rPaymentDate = datetime.datetime.strptime(request.args.get('PaymentDate'), '%d-%m-%Y')
            
        D = datetime.datetime.strptime(request.args.get('DisbursementDate'), '%d-%m-%Y')

        P = np.float(request.args.get('Principal'))
        
        A = np.float(request.args.get('Amortization'))

        period = np.int(request.args.get('Period'))

        _, I, _ = returnDaysEachMonth(period, rPaymentDate, D)

        #A = amortization_amount
        #P = principal
        #I = installDates
        #D = rDisbursementDate

        i_initial_guess = 0.01
        i_solution = fsolve(calculate_interest_rate, i_initial_guess,args=(P,A,I,D))

        return { 'interestRate' : i_solution[0] }

    except Exception as e:
        print(e)
        return jsonify({'Error' : 'Not a valid request.'})