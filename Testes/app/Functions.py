from configparser import ConfigParser
from datetime import datetime
import pandas as pd
import numpy as np
import pymongo
import pickle

######################
#                    #
#  OTHER FUNCTIONS   #
#                    #
######################

def save_to_file(objeto, nome_arquivo):
    with open(nome_arquivo, 'wb') as output:
        pickle.dump(objeto, output, pickle.HIGHEST_PROTOCOL)


def load_file(nome_arquivo):
    with open(nome_arquivo, 'rb') as input:
        objeto = pickle.load(input)
    return objeto

def config(filename='./mongodb.ini', section='mongodb'):
    parser = ConfigParser()
    parser.read(filename)
    # get section, default to postgresql
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))
    return db

def return_backward_months(anomes,qtd,actualmonth=True):
    if actualmonth == True:
        meses = [anomes]
    else:
        meses = []
    mes = anomes
    for i in range(0,qtd):
        if (mes // 10**0 % 100) == 1:
            mes = mes + 11
            mes = mes - 100
        else:
            mes = mes - 1
        meses.append(int(mes))
    return meses