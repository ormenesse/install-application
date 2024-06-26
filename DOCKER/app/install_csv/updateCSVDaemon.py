#######################
# !!! DEAD SCRIPT !!! #
#######################

import pandas as pd
import numpy as np
import datetime
import pymongo
import base64
import time
import os

def generateClient(section='mongodbRead'):

    if section == 'mongodb':
        return pymongo.MongoClient(base64.b64decode(os.getenv('mongodb', default=None)).decode(), ssl=True)
    elif section == 'mongodbRead':
        return pymongo.MongoClient(base64.b64decode('bW9uZ29kYitzcnY6Ly9haXJmbG93OmtBQ3cyTHR4Z0Z6ZVB0bkBneXJhbWFpcy1wcm9kdWN0aW9uLmxod3RiLm1vbmdvZGIubmV0L2d5cmFtYWlzP3JldHJ5V3JpdGVzPXRydWUmcmVhZFByZWZlcmVuY2U9c2Vjb25kYXJ5JnJlYWRQcmVmZXJlbmNlVGFncz1ub2RlVHlwZTpBTkFMWVRJQ1Mmdz1tYWpvcml0eQ==').decode(), ssl=True)
    else:
        raise Exception("MongoDB env not found.")
    
def main():
    
    while True:
        
        client = generateClient()
        #allPartners = list(client['gyramais']['InterestFeesPartners'].aggregate([
        #    {
        #        '$match' : {
        #            'document': 'PartnerGyra'
        #        }
        #    }
        #]))
        #
        allPartners = list(client['gyramais']['Business'].aggregate([
            {
                '$match' : {
                    'fee' : { '$exists' : True }
                }
            },
            {
                '$project' : {
                    'cnpj' : 1,
                    'partnerFee' : { '$multiply' : [ '$fee', 1/100 ] },
                    'collectionFee' : { '$multiply' : [ '$collectionFee', 1/100 ] }
                }
            }
        ]))
        allPartners.append(
            {
                'cnpj' : 'GYRA',
                'partnerFee' : 0,
                'collectionFee' : 0
            }
        )
        partners = pd.json_normalize(allPartners)
        partners['maxInterest'] = np.nan
        partners['minInterest'] = np.nan
        #
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

        dfNormalized = pd.json_normalize(riskGroups,['groups','values'],[['groups','riskGroup']])
        
        fees = pd.json_normalize(allFees,'fees')
        
        for period in fees['period'].unique():
            dfNormalized.loc[dfNormalized['period'] == period,'gyraMaisFee'] = fees['gyraMaisFee'][(fees['period'] == period)].values[0]
            dfNormalized.loc[dfNormalized['period'] == period,'bankFee'] = fees['bankFee'][(fees['period'] == period)].values[0]

        df = pd.DataFrame([])
        for i in partners.iterrows():
            copy = dfNormalized.copy()
            copy.loc[:,'partnerFee'] = i[1]['partnerFee']
            copy.loc[:,'type'] = i[1]['cnpj'] + ','
            if ~np.isnan(i[1]['maxInterest']):
                copy.loc[copy['interest'] > i[1]['maxInterest'], 'interest'] = i[1]['maxInterest']
            if ~np.isnan(i[1]['minInterest']):
                copy.loc[copy['interest'] < i[1]['minInterest'], 'interest'] = i[1]['minInterest']
            df = pd.concat([df,copy],axis=0)

        cols = []
        for col in df.columns:
            if '.' in col:
                cols.append(col.split('.')[-1])
            else:
                cols.append(col)
        df.columns = cols

        df = df.groupby(['period','interest','riskGroup','gyraMaisFee','bankFee','partnerFee'],as_index=False).sum()

        df.to_csv('gyra_fees.csv',index=False)
        
        time.sleep(43200)

if __name__ == "__main__":
    main()