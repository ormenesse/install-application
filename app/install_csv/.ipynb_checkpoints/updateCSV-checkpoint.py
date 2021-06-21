import pandas as pd
import numpy as np
import datetime
import pymongo
import base64

def generateClient():
    
    return pymongo.MongoClient(base64.b64decode('bW9uZ29kYitzcnY6Ly9yZWFkb25seXVzZXI6bTRMYXJuQTdGUzhxME9KY0BneXJhbWFpcy1wcm9kdWN0aW9uLmxod3RiLm1vbmdvZGIubmV0L3Rlc3Q/cmV0cnlXcml0ZXM9dHJ1ZSZyZWFkUHJlZmVyZW5jZT1zZWNvbmRhcnkmcmVhZFByZWZlcmVuY2VUYWdzPW5vZGVUeXBlOkFOQUxZVElDUyZ3PW1ham9yaXR5').decode(), ssl=True)

def main():
    
    client = generateClient()
    allPartners = list(client['gyramais']['InterestFeesPartners'].aggregate([
        {
            '$match' : {
                'document': 'PartnersGyra'
            }
        }
    ]))
    riskGroups = list(client['gyramais']['InterestFeesPartners'].aggregate([
        {
            '$match' : {
                'document': 'RiskGroupsGyraScore'
            }
        }
    ]))

    allFees = list(client['gyramais']['InterestFeesPartners'].aggregate([
        {
            '$match' : {
                'document': 'BusinessFees'
            }
        }
    ]))
    client.close()
        
    partners = pd.json_normalize(allPartners,'type')

    dfNormalized = pd.json_normalize(riskGroups,['groups','values'],[['groups','riskGroup']])
    
    fees = pd.json_normalize(allFees,'fees')
    
    for period in fees['period'].unique():
        dfNormalized.loc[dfNormalized['period'] == period,'gyraMaisFee'] = fees['gyraMaisFee'][(fees['period'] == period)].values[0]
        dfNormalized.loc[dfNormalized['period'] == period,'bankFee'] = fees['bankFee'][(fees['period'] == period)].values[0]

    df = pd.DataFrame([])
    for i in partners.iterrows():
        copy = dfNormalized.copy()
        copy.loc[:,'partnerFee'] = i[1]['partnerFee']
        copy.loc[:,'type'] = i[1]['cnpj']
        df = pd.concat([df,copy],axis=0)
        
    cols = []
    for col in df.columns:
        if '.' in col:
            cols.append(col.split('.')[-1])
        else:
            cols.append(col)
    df.columns = cols

    df.to_csv('gyra_fees.csv',index=False)

if __name__ == "__main__":
    main()