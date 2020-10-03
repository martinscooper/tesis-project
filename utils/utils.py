import numpy
import pandas as pd
from scipy.stats.stats import pearsonr
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import MinMaxScaler
import os

pd.options.mode.chained_assignment = None

numpy.random.seed(7)


def get_user_data(data, userId):
    """
    Get data of a specific user

    """
    result = data.loc[data.index.get_level_values(0) == userId]
    assert (result.shape[0] != 0), 'The user does not exist.'
    return result


def get_not_user_data(data, userId):
    """

    :return: all the data except that of the user specidied

    """
    return data.loc[data.index.get_level_values(0) != userId].sort_index(level=1)


def create_classifier_model(clf):
    '''
    Makes a pipeline from the clf param and a MinMaxScaler

    '''

    transformer = ColumnTransformer([('scale', MinMaxScaler(), numeric_cols)],
                                    remainder='passthrough')
    return make_pipeline(transformer, clf)


def file_exists(file):
    return os.path.exists(file)


def get_granularity_from_minutes(nb_min):
    if nb_min % 60 == 0:
        gran = f'{int(nb_min/60)}h'
    else:
        gran = f'{nb_min}min'
    return gran


def add_per_to_all_experiments():
    '''
    add _per to all experiment pkl in case I forget to do it
    '''
    path_to_file = './pkl/experiments'
    c = 0
    for fn in os.listdir(path_to_file):
        nfn = fn[:-4] + '_per' + fn[-4:]
        os.rename(f'{path_to_file}/{fn}', f'{path_to_file}/{nfn}')
