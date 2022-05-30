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
    
    return paymentCapacityPriceTable(request)
    
@app.route('/installapp/priceTable/', methods=['GET'])
#/priceTable?preApproved=123123&Period=12&interestRate=3&Partner=GYRA&Fees=True&Iof=True
def calculate_preapproved():
    
    gc.collect()
    
    return priceTable(request)

@app.route('/installapp/interestAmount/', methods=['GET'])
#/interestAmount?Principal=16800&Period=24&DisbursementDate=29-10-2020&PaymentDate=20-12-2020&Amortization=1350.50
def calculate_interestrate():
    
    gc.collect()
    
    return calculate_inverse_interest_amount(request)
    
if __name__ == '__main__':
    app.run(host='0.0.0.0')