#https://stackoverflow.com/questions/24892035/how-can-i-get-the-named-parameters-from-a-url-using-flask
from flask import Flask, request, redirect, url_for, flash, jsonify, abort, Response
from installFunctions import *
from datetime import datetime
from flask_cors import CORS
from Functions import *
import warnings
import pymongo
import json
import gc

warnings.filterwarnings("ignore")

app = Flask(__name__)
CORS(app) #Prevents CORS errors

@app.route('/')
def works():
	return ''
    
@app.route('/installapp/paymentCapacityPriceTable/', methods=['GET'])
#/paymentCapacityPriceTable?paymentCapacity=1062.825282&riskGroup=3&Partner=GYRA&Fees=True&Iof=True
#/paymentCapacityPriceTable?paymentCapacity=1062.825282&interestRate=3&Partner=GYRA&Fees=True&Iof=True
def calculate_paymentCapacity():
    
    gc.collect()
    co = CreditOperation()
    return co.paymentCapacityPriceTable(request)
    
@app.route('/installapp/priceTable/', methods=['GET'])
#/priceTable?preApproved=123123&Period=12&interestRate=3&Partner=GYRA&Fees=True&Iof=True
def calculate_preapproved():
    
    gc.collect()
    co = CreditOperation()
    return co.priceTable(request)

@app.route('/installapp/priceTableTabular/', methods=['GET'])
#/priceTable?preApproved=123123&Period=12&interestRate=3&Partner=GYRA&Fees=True&Iof=True
def calculate_preapproved_tabular():
    
    gc.collect()
    co = CreditOperation()
    _json_ = co.priceTable(request)
    defaultDict = {}
    defaultDict['DisbursementDate'] = _json_['choices'][0]['DisbursementDate']
    try:
        defaultDict['IPCA'] = _json_['choices'][0]['IPCA']
    except:
        pass 
    defaultDict['Iof'] = _json_['choices'][0]['Iof']
    defaultDict['annualCet'] = _json_['choices'][0]['annualCet']
    defaultDict['installAmount'] = _json_['choices'][0]['installAmount']
    defaultDict['interestRate'] = _json_['choices'][0]['interestRate']
    defaultDict['months'] = _json_['choices'][0]['months']
    defaultDict['preApproved'] = _json_['choices'][0]['preApproved']
    defaultDict['preApprovedWithFees'] = _json_['choices'][0]['preApprovedWithFees']
    defaultDict['totalFinalAmount'] = _json_['choices'][0]['totalFinalAmount']
    arr = []
    for i in _json_['choices'][0]['amortizationTable']['amortization_amount'].keys():
        _dic_ = copy.copy(defaultDict)
        _dic_['amortization_amount'] = _json_['choices'][0]['amortizationTable']['amortization_amount'][i]
        _dic_['balance'] = _json_['choices'][0]['amortizationTable']['balance'][i]
        _dic_['installDates'] = _json_['choices'][0]['amortizationTable']['installDates'][i]
        _dic_['interest'] = _json_['choices'][0]['amortizationTable']['interest'][i]
        _dic_['number'] = _json_['choices'][0]['amortizationTable']['number'][i]
        _dic_['payDayDates'] = _json_['choices'][0]['amortizationTable']['payDayDates'][i]
        _dic_['principal'] = _json_['choices'][0]['amortizationTable']['principal'][i]
        arr.append(_dic_)
    return arr

@app.route('/installapp/interestAmount/', methods=['GET'])
#/interestAmount?Principal=16800&Period=24&DisbursementDate=29-10-2020&PaymentDate=20-12-2020&Amortization=1350.50
def calculate_interestrate():
    
    gc.collect()
    co = CreditOperation()
    return co.calculate_inverse_interest_amount(request)
    
if __name__ == '__main__':
    app.run(host='0.0.0.0')