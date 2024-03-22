from flask import jsonify
from datetime import date
import pandas as pd
import numpy as np
import datetime
import holidays
from pandas.core.frame import DataFrame
from scipy.optimize import fsolve
import calendarNew as calendar
from flask import request
import pymongo
import base64
import copy
import sys, os
import logging 

def generateClient(section='mongodbRead'):

    if section == 'mongodb':
        return pymongo.MongoClient(base64.b64decode(os.getenv('mongodb', default=None)).decode(), ssl=True)
    elif section == 'mongodbRead':
        return pymongo.MongoClient(base64.b64decode(os.getenv('mongodbRead', default=None)).decode(), ssl=True)
    else:
        raise Exception("MongoDB env not found.")

class CreditOperation():

    def __init__(self):
        self.roundingPlaces = 6
        self.iofInterestRate= 0.000041
        self.iofMaxRate = 0.015
        self.iofAdicional = 0.0038
        
    def xirr(self, transactions):
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

    def return_forward_months(self, anomes,qtd,actualmonth=True):
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

    def interest_rate(self, tj,*data):
        A,P,M = data
        return A/30 - P*( (tj*(np.power(1+tj,M))) / ( np.power(1+tj,M) - 1) )

    def calculate_interest_rate(self, interestRate, *data):
        
        principal, amortization, installDates, rDisbursementDate = data
        
        soma = 0

        for i in installDates:

            days = ( i - ( date(rDisbursementDate.year, rDisbursementDate.month, rDisbursementDate.day) ) ).days

            soma = soma + ( 1/( (1+interestRate)**( (days)/30.0) ) )
        
        return amortization - np.round(principal/soma,self.roundingPlaces)

    def calculate_amortization_amount(self, principal, interestRate, installDates, rDisbursementDate):
        
        days_each_month = []
        
        soma = 0

        for i in installDates:

            days = ( i - ( date(rDisbursementDate.year, rDisbursementDate.month, rDisbursementDate.day) ) ).days

            days_each_month.append(days)

            soma = soma + ( 1/( (1+interestRate)**( (days)/30.0) ) )
        
        return round(principal/soma,self.roundingPlaces)

    def returnDaysEachMonth(self, period, rPaymentDate, rDisbursementDate):
        
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

    def amortization_schedule_right(self, principal, interestRate, period, rPaymentDate, rDisbursementDate):
        
        #months = self.return_forward_months(rDisbursementDate.year*100+rDisbursementDate.month,period,actualmonth=True)
        
        days_each_month, installDates, payDay = self.returnDaysEachMonth(period, rPaymentDate, rDisbursementDate)
        amortization_amount = self.calculate_amortization_amount(principal, interestRate, installDates, rDisbursementDate)
        number = 1
        balance = 1*principal
        installments = []
        
        while number <= period:
            interest = balance * (np.power((1+interestRate),(days_each_month[number-1]/30))-1) # quantidade de dias no mes
            principal = amortization_amount - interest
            balance = balance - principal
            installments.append(
                dict(
                    installDates=installDates[number-1],
                    payDayDates=payDay[number-1],
                    number=number,
                    amortization_amount=round(amortization_amount,self.roundingPlaces),
                    interest=round(interest,self.roundingPlaces),
                    principal=round(principal,self.roundingPlaces),
                    balance=round(balance,self.roundingPlaces) if balance > 0.001 else 0
                )
            )
            number += 1
            
        return installments, amortization_amount

    def amortization_schedule(self, principal, interestRate, period, rPaymentDate, rDisbursementDate):
        # months = self.return_forward_months(rDisbursementDate.year*100+rDisbursementDate.month,period,actualmonth=True)
        
        days_each_month, installDates, payDay = self.returnDaysEachMonth(period, rPaymentDate, rDisbursementDate)
        amortization_amount = self.calculate_amortization_amount(principal, interestRate, installDates, rDisbursementDate)
        number = 1
        balance = 1*principal
        balanceAdjusted = 1*principal
        installments = []
        interestBiggerThanPrincipal = 0
        
        while number <= period:
            # não sou a favor disso, mas aparentemente não é a matemática que está valendo neste negócio.
            interest = ( balance * (np.power((1+interestRate),(days_each_month[number-1]/30))-1) ) # quantidade de dias no mes
            
            if interestBiggerThanPrincipal > 0:
                interest = interest + interestBiggerThanPrincipal
                interestBiggerThanPrincipal = 0

            if interest > amortization_amount:
                interestBiggerThanPrincipal = (interest - amortization_amount)
                interest = amortization_amount*1.0

            if number == period and interestBiggerThanPrincipal > 0:
                interest = interest + interestBiggerThanPrincipal

            # Caso queira voltar a conta correta, deve-se apenas tirar esse if e deletar a variável interestBiggerThanPrincipal
            principal = amortization_amount - interest
            principalAdjusted = amortization_amount - interest
            balance = balance - principal
            balanceAdjusted = balance - principalAdjusted
            installments.append(
                dict(
                    installDates=installDates[number-1],
                    payDayDates=payDay[number-1],
                    number=number,
                    amortization_amount=round(amortization_amount,self.roundingPlaces),
                    interest=round(interest,self.roundingPlaces),
                    principal=round(principalAdjusted,self.roundingPlaces),
                    balance=round(balanceAdjusted,self.roundingPlaces) if balanceAdjusted > 0.001 else 0
                )
            )
            number += 1
            
        return installments, amortization_amount

    def return_iof_fee(self, amounts_installs, period, rPaymentDate, rDisbursementDate, iofadjust):
        
        days_each_month, installDates, _ = self.returnDaysEachMonth(period, rPaymentDate, rDisbursementDate)
        if iofadjust == False:
            total_iof = []
            for j,i in enumerate(amounts_installs['amortization_amount']):
                days_iof = np.sum(days_each_month[:j+1])
                total_iof.append(i*self.iofInterestRate*days_iof)
            # sempre perguntar se essa regra ainda existe
            iof_fee = sum(total_iof)+ amounts_installs['amortization_amount'].sum()*self.iofAdicional
            iof_fee_2 = amounts_installs['amortization_amount'].sum()*self.iofMaxRate
            iof_fee_2 = iof_fee_2 + amounts_installs['amortization_amount'].sum()*self.iofAdicional
            if iof_fee_2 < iof_fee:
                iof_fee = iof_fee_2
            return round(iof_fee,self.roundingPlaces)
        else:
            accInterest = amounts_installs['amortization_amount']-amounts_installs['interest']
            iofs = []
            for i in range(len(days_each_month)):
                if sum(days_each_month[:i+1]) < 365:
                    iofs.append(accInterest[i]*self.iofInterestRate*sum(days_each_month[:i+1])+accInterest[i]*self.iofAdicional)
                else:
                    iofs.append(accInterest[i]*self.iofInterestRate*365+accInterest[i]*self.iofAdicional)
            
            return round(np.sum(iofs),self.roundingPlaces)

    def reverse_calculate_amortization_amount(self, paymentCapacity, interestRate, period, rPaymentDate, rDisbursementDate):

        days_each_month, installDates, _ = self.returnDaysEachMonth(period, rPaymentDate, rDisbursementDate)     
        days_each_month = []
        for i in installDates:
            days = ( i - (date(rDisbursementDate.year, rDisbursementDate.month, rDisbursementDate.day))).days
            days_each_month.append(days)
        
        return paymentCapacity*sum(1/((1+interestRate)**(np.array(days_each_month)/30)))

    def reverse_return_iof_fee(self, amounts_installs, period, rPaymentDate, rDisbursementDate, iofadjust):
        
        days_each_month, installDates, _ = self.returnDaysEachMonth(period, rPaymentDate, rDisbursementDate)
        if iofadjust == False:
            total_iof = []
            for j,i in enumerate(amounts_installs['amortization_amount']):
                days_iof = np.sum(days_each_month[:j+1])
                total_iof.append(i*self.iofInterestRate*days_iof)
            iof_fee = sum(total_iof) + amounts_installs['amortization_amount'].sum()*self.iofAdicional
            iof_fee_2 = amounts_installs['amortization_amount'].sum()*self.iofMaxRate
            iof_fee_2 = iof_fee_2 + amounts_installs['amortization_amount'].sum()*self.iofAdicional
            if iof_fee_2 < iof_fee:
                iof_fee = iof_fee_2
                
            return round(iof_fee,self.roundingPlaces)
        
        else:
            accInterest = amounts_installs['amortization_amount']-amounts_installs['interest']
            iofs = []
            for i in range(len(days_each_month)):
                if sum(days_each_month[:i+1]) < 365:
                    iofs.append(accInterest[i]*self.iofInterestRate*sum(days_each_month[:i+1])+accInterest[i]*self.iofAdicional)
                else:
                    iofs.append(accInterest[i]*self.iofInterestRate*365+accInterest[i]*self.iofAdicional)
            
            return round(np.sum(iofs),self.roundingPlaces)
        
    def calculate_amortization_schedule_with_taxes(self, amountWithFees, initial_amount, 
                                                   interestRate, period=12, iofadjust=False, iof=True, 
                                                   adjusted=True, rPaymentDate=datetime.datetime.today(), rDisbursementDate=datetime.datetime.today()):

        amount = amountWithFees
        if adjusted:
            installments, installAmount = self.amortization_schedule(amount, interestRate, period, 
                                                                     rPaymentDate, rDisbursementDate)
        else:
            installments, installAmount = self.amortization_schedule_right(amount, interestRate, period, 
                                                                           rPaymentDate, rDisbursementDate)

        installments = pd.DataFrame(installments)
        #print(installments.to_dict(orient='records'))
        if iof == False:
            iof_fee = 0
        else:
            iof_fee = self.return_iof_fee( installments, period, rPaymentDate, rDisbursementDate, iofadjust)
        
        if adjusted:
            final_installments, installAmount = self.amortization_schedule(amount+iof_fee, interestRate, period, 
                                                                           rPaymentDate, rDisbursementDate)
            final_installments = pd.DataFrame(final_installments)
        else:
            final_installments, installAmount = self.amortization_schedule_right(amount+iof_fee, interestRate, period, 
                                                                                 rPaymentDate, rDisbursementDate)
            final_installments = pd.DataFrame(final_installments)
        # recalculando IOF            
        #iof_fee = self.return_iof_fee( final_installments, period, rPaymentDate, rDisbursementDate, iofadjust)
        """
        array_irr = list(final_installments['amortization_amount'].values)
        array_irr.insert(0,-initial_amount)

        cet = np.irr(array_irr)
        annualCet = (1+cet)**12-1
        """
        array_irr = [ (i[1], i[0]) for i in final_installments[['amortization_amount','installDates']].values ]
        addDay = datetime.date(rDisbursementDate.year, rDisbursementDate.month, rDisbursementDate.day)
        array_irr.insert(0,(datetime.date(addDay.year, addDay.month, addDay.day),-initial_amount))
        annualCet = np.round(self.xirr(array_irr),6)
        cet = ((annualCet+1)**(1/12))-1
        # Norma BACEN
        cet = round(((annualCet+1)**(30/365))-1,6)
        annualCet = round(((1+cet)**12) - 1,6)
        
        return final_installments.to_dict(), cet, annualCet, iof_fee, installAmount
        
    def find_pre_approved_with_fees(self, paymentCapacity, interestRate, 
                                    period=12, iofadjust=False, rPaymentDate=datetime.datetime.today(), 
                                    rDisbursementDate=datetime.datetime.today()):
        
        amount_wiof = self.reverse_calculate_amortization_amount(paymentCapacity, interestRate, period, rPaymentDate, rDisbursementDate)
        #doing it with maximum iof possible
        installments, _ = self.amortization_schedule(1, interestRate, period, rPaymentDate, rDisbursementDate)
        installments = pd.DataFrame(installments)
        iof_fee = self.reverse_return_iof_fee(installments, period, rPaymentDate, rDisbursementDate, iofadjust)
        #doing it with maximum iof possible
        final_installments, _ = self.amortization_schedule(amount_wiof*(1-iof_fee), interestRate, period, 
                                                           rPaymentDate, rDisbursementDate)
        final_installments = pd.DataFrame(final_installments)
        final_iof = self.return_iof_fee( final_installments, period, rPaymentDate, rDisbursementDate, iofadjust)
        #doing it with maximum iof possible
        final_installments, _ = self.amortization_schedule(np.round(amount_wiof-final_iof,4), interestRate, period, rPaymentDate, rDisbursementDate)
        final_installments = pd.DataFrame(final_installments)
        pre_appr_w_fees = self.reverse_calculate_amortization_amount(final_installments['amortization_amount'].values[0], interestRate, period, 
                                                                     rPaymentDate, rDisbursementDate)
        
        return pre_appr_w_fees
        
    def paymentCapacityPriceTable(self, request, gyraFeesPath='./install_csv/gyra_fees.csv'):
        
        gyra_fees = pd.read_csv(gyraFeesPath)
        try:
            rPaymentDate = datetime.datetime.strptime(request.args.get('PaymentDate'), '%d-%m-%Y')
            rDisbursementDate = datetime.datetime.strptime(request.args.get('DisbursementDate'), '%d-%m-%Y')
            paymentCapacity = float(request.args.get('paymentCapacity'))
            if paymentCapacity < 0:
                paymentCapacity = 0
            partner = request.args.get('Partner')
            fees = eval(request.args.get('Fees'))
            iof_fee = eval(request.args.get('Iof'))
            try:
                if eval(request.args.get('PF')):
                    self.iofInterestRate = 0.000082
                    self.iofMaxRate = 0.03
                    self.iofAdicional = 0.0038
                elif eval(request.args.get('PJ')):
                    self.iofInterestRate= 0.000041
                    self.iofMaxRate = 0.015
                    self.iofAdicional = 0.0038
            except:
                pass # do nothing
            try:
                bankFeeRate = float(request.args.get('BankFeeRate'))
                gyra_fees.loc[:,'bankFee'] = bankFeeRate
            except:
                pass
            try:
                risk_group = int(request.args.get('riskGroup'))
            except:
                risk_group = 1
            try:
                interestRate= round(float(request.args.get('interestRate'))/100,self.roundingPlaces)
                interestGiven = True
            except:
                interestRate= None
                interestGiven = False
            try:
                adjusted = eval(request.args.get('Adjusted'))
            except:
                adjusted = False
            try:
                # Arredondar o paymentCapacity
                iofadjust = eval(request.args.get('AdjustedIof'))
            except:
                iofadjust = False
            try:
                ipca = eval(request.args.get('IPCA'))
            except:
                ipca = False
            if iofadjust:
                self.roundingPlaces = 2
                adjusted = True
            if ipca:
                try:
                    client = generateClient()
                    ipcaslist = list(client['gyramais']['IntegrationEconomics'].find({},{'ipcaAcc12MCRI': 1, 'anomes': 1}).sort('anomes', -1).limit(10))
                    interestIPCA = (1 + ipcaslist[2]['ipcaAcc12MCRI'] + interestRate)**(1/12)-1 # conta inversa
                    interestRate = round(interestIPCA,4)
                except Exception as e:
                    return { 'Error': 'Could not fetch IPCA values.'}
            if any(partner in sub for sub in list(gyra_fees['type'].unique())) == False:
                partner = 'GYRA'
            if risk_group not in list(gyra_fees['riskGroup'][(gyra_fees['type'].str.contains(partner))].unique()):
                risk_group = gyra_fees['riskGroup'][(gyra_fees['type'].str.contains(partner))].min()
            pre_approved = { 'choices' : [] }
            #for period in gyra_fees['period'][(gyra_fees['riskGroup'] == risk_group)].unique(): #[6,9,12,18,24]:
            for period in [3,6,9,12,18,24]: #[6,9,12,18,24]:
                #print(interestGiven)
                if interestGiven == False:
                    interestRate= round(
                        float(
                            gyra_fees['interest'][
                                (gyra_fees['period'] == period) & 
                                (gyra_fees['type'].str.contains(partner)) & 
                                (gyra_fees['riskGroup'] == risk_group)
                            ].max()),self.roundingPlaces)
                    
                preaprwfees = self.find_pre_approved_with_fees(paymentCapacity, interestRate, period, 
                                                               iofadjust, rPaymentDate, rDisbursementDate)

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

                    # ARREDONDAMENTO PRICETABLE
                    rounding = True
                    if rounding:
                        preapr = np.ceil(preapr/5000)*5000
                    else:
                        preapr = np.round(preapr/100,0)*100
                    
                    feesValue = 0
                    for key in detailed_fees.keys():
                        detailed_fees[key] = detailed_fees[key]*preapr
                        feesValue = feesValue + detailed_fees[key]
                    table, cet, acet, iofval, installAmount = self.calculate_amortization_schedule_with_taxes( preapr + feesValue, preapr,  interestRate, 
                                                                                                              period, iofadjust, iof_fee, 
                                                                                                              adjusted, rPaymentDate, rDisbursementDate)
                    preaprwfees = preapr + feesValue + iofval
                    pre_approved['choices'].append(
                        dict(months=int(period),preApproved=preapr,interestRate=interestRate,
                        preApprovedWithFees=preaprwfees,totalfeesRate=int_fees,separatedFees=detailed_fees,
                        amortizationTable=table,annualCet=acet,Cet=cet,
                        Iof=iofval,DisbursementDate=rDisbursementDate,installAmount=installAmount,
                        totalFinalAmount=installAmount*period)
                    )

                else:
                    preapr = np.round(preaprwfees/100,0)*100
                    table, cet, acet, iofval, installAmount = self.calculate_amortization_schedule_with_taxes(preapr, preapr, interestRate, 
                                                                                                              period, iofadjust, iof_fee, 
                                                                                                              adjusted, rPaymentDate, rDisbursementDate)
                    preaprwfees = preapr+iofval
                    pre_approved['choices'].append(
                        dict(months=int(period),preApproved=preapr,preApprovedWithFees=float(preaprwfees),
                        interestRate=interestRate,amortizationTable=table,annualCet=acet,
                        Cet=cet,Iof=iofval,DisbursementDate=rDisbursementDate,
                        installAmount=installAmount,totalFinalAmount=installAmount*period)
                    )
            pre_approved['partner'] = partner
            if ipca:
                for doc in pre_approved['choices']:
                    doc['IPCA'] = ipcaslist[2]['ipcaAcc12MCRI']
            return pre_approved
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            logging.basicConfig(filename='app.log', filemode='w+', format='%(name)s - %(levelname)s - %(message)s')
            logging.error(str(exc_type) + ' ' + str(fname) + ' ' + str(exc_tb.tb_lineno))
            return jsonify({'Error' : 'Not a valid request.'})
        
    def priceTable(self, request, gyraFeesPath='./install_csv/gyra_fees.csv'):
        gyra_fees = pd.read_csv(gyraFeesPath)
        try:
            rPaymentDate = datetime.datetime.strptime(request.args.get('PaymentDate'), '%d-%m-%Y')
            rDisbursementDate = datetime.datetime.strptime(request.args.get('DisbursementDate'), '%d-%m-%Y')
            preapr = float(request.args.get('preApproved'))
            if preapr < 0:
                preapr = 0 
            interestRate = round(float(request.args.get('interestRate'))/100,self.roundingPlaces)
            period = int(request.args.get('Period'))
            try:
                if eval(request.args.get('PF')):
                    self.iofInterestRate = 0.000082
                    self.iofMaxRate = 0.03
                    self.iofAdicional = 0.0038
                elif eval(request.args.get('PJ')):
                    self.iofInterestRate= 0.000041
                    self.iofMaxRate = 0.015
                    self.iofAdicional = 0.0038
            except Exception as e:
                pass # do nothing
            try:
                fees = eval(request.args.get('Fees'))
            except:
                fees = True
            try:
                iof_fee = eval(request.args.get('Iof'))
            except:
                iof_fee = True
            try:
                partner = request.args.get('Partner')
            except:
                partner = 'GYRA'
            try:
                adjusted = eval(request.args.get('Adjusted'))
            except:
                adjusted = False
            try:
                iofadjust = eval(request.args.get('AdjustedIof'))
            except:
                iofadjust = False
            try:
                bankFeeRate = float(request.args.get('BankFeeRate'))
                gyra_fees.loc[:,'bankFee'] = bankFeeRate
            except:
                pass
            try:
                ipca = eval(request.args.get('IPCA'))
            except:
                ipca = False
            if ipca:
                try:
                    client = generateClient()
                    ipcaslist = list(client['gyramais']['IntegrationEconomics'].find({},{'ipcaAcc12MCRI': 1, 'anomes': 1}).sort('anomes', -1).limit(10))
                    interestIPCA = (1 + ipcaslist[2]['ipcaAcc12MCRI'] + interestRate)**(1/12)-1 # conta inversa
                    interestRate = round(interestIPCA,4)
                except Exception as e:
                    return { 'Error': 'Could not fetch IPCA values.'}
            if iofadjust:
                self.roundingPlaces = 2
                adjusted = True
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
                table, cet, acet, iofval, installAmount = self.calculate_amortization_schedule_with_taxes(preaprwfees, preapr, interestRate, 
                                                                                                          period, iofadjust, iof_fee, 
                                                                                                          adjusted, rPaymentDate, rDisbursementDate)
                preaprwfees = preaprwfees + iofval
                pre_approved['choices'].append(
                    dict(months=int(period),preApproved=preapr,interestRate=interestRate,
                    preApprovedWithFees=preaprwfees,totalfeesRate=int_fees,separatedFees=detailed_fees,
                    amortizationTable=table,annualCet=acet,Cet=cet,Iof=iofval,DisbursementDate=rDisbursementDate,
                    installAmount=installAmount,totalFinalAmount=installAmount*period
                    )
                )
            else:
                table, cet, acet, iofval, installAmount = self.calculate_amortization_schedule_with_taxes(preapr, preapr, interestRate, 
                                                                                                          period, iofadjust, iof_fee, 
                                                                                                          adjusted, rPaymentDate, rDisbursementDate)
                preaprwfees = preapr + iofval
                pre_approved['choices'].append(
                    dict(months=int(period),preApproved=preapr,preApprovedWithFees=preaprwfees,
                    interestRate=interestRate,amortizationTable=table,annualCet=acet,
                    Cet=cet,Iof=iofval,DisbursementDate=rDisbursementDate,
                    installAmount=installAmount,totalFinalAmount=installAmount*period
                    )
                )
            #Ending
            pre_approved['partner'] = partner
            if ipca:
                for doc in pre_approved['choices']:
                    doc['IPCA'] = ipcaslist[2]['ipcaAcc12MCRI']
            return pre_approved
            
        except Exception as e:
            print(e)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            logging.basicConfig(filename='app.log', filemode='w+', format='%(name)s - %(levelname)s - %(message)s')
            logging.error(str(exc_type) + ' ' + str(fname) + ' ' + str(exc_tb.tb_lineno))
            return jsonify({'Error' : 'Not a valid request.'})

    def calculate_inverse_interest_amount(self, request):
        try:
            rPaymentDate = datetime.datetime.strptime(request.args.get('PaymentDate'), '%d-%m-%Y')
            D = datetime.datetime.strptime(request.args.get('DisbursementDate'), '%d-%m-%Y')
            P = float(request.args.get('Principal'))
            A = float(request.args.get('Amortization'))
            period = int(request.args.get('Period'))
            _, I, _ = self.returnDaysEachMonth(period, rPaymentDate, D)
            #A = amortization_amount
            #P = principal
            #I = installDates
            #D = rDisbursementDate
            i_initial_guess = 0.01
            i_solution = fsolve(self.calculate_interestRate, i_initial_guess,args=(P,A,I,D))
            return { 'interestRate' : i_solution[0] }
        except Exception as e:
            print(e)
            return jsonify({'Error' : 'Not a valid request.'})