import pandas as pd
import numpy as np
from utils import get_user_data


def shift_hours(df, n, columns=None):
    '''
    Shift the dataset n hours. If

    :param n: number of hours to shift
    :param columns: the columns that should be shifted,
    :return:
    '''
    dfcopy = df.copy().sort_index()
    if columns is None:
        columns = df.columns
    for ind, row in dfcopy.iterrows():
        try:
            dfcopy.loc[(ind[0], ind[1]), columns] = dfcopy.loc[(ind[0], ind[1] + pd.DateOffset(hours=n)), columns]
        except KeyError:
            dfcopy.loc[(ind[0], ind[1]), columns] = np.nan
    # print(dfcopy.isna().sum())
    dfcopy.dropna(inplace=True)
    return dfcopy


def series_to_supervised(df, dropnan=True, number_of_lags=None, period=1):
    '''
    Creates the lagged dataset calling shift_hours for every lag and then combines all the lagged datasets

    :param period: separation of lags, for example: if period = 3 and lag = 3, por a time t we will have features of t-3,
    t-6 and t-9.
    :return:
    '''
    lags = range(period * number_of_lags, 0, -period)
    columns = df.columns
    n_vars = df.shape[1]
    print(lags, columns, n_vars)
    data, names = list(), list()
    # print('Generating {0} time-lags with period equal {1} ...'.format(number_of_lags, period))
    # input sequence (t-n, ... t-1)
    for i in range(len(lags), 0, -1):
        data.append(shift_hours(df, lags[i - 1], df.columns))
        names += [('{0}(t-{1})'.format(columns[j], lags[i - 1])) for j in range(n_vars)]
    data.append(df)
    names += [('{0}(t)'.format(columns[j])) for j in range(n_vars)]

    # put it all together
    agg = pd.concat(data, axis=1)
    agg.columns = names
    # drop rows w   ith NaN values
    if dropnan:
        agg.dropna(inplace=True)
    return agg


def make_lagged_datasets(lags=None, period=1, gran='1h'):
    '''
    Calls series_to_supervised for every user (otherwise user information would be merged) and then combines it.
    The resulting dataset is saved in the path 'pkl/datasets/gran{}_period{}_lags{}.pkl'

    :param gran: granularity. e.g. '1h', '30m', '2h', etc
    '''

    df = pd.read_pickle('pkl/dataset_gran{0}.pkl'.format(gran))
    data = list()
    for i in df.index.get_level_values(0).drop_duplicates():
        d = series_to_supervised(get_user_data(df, i), number_of_lags=lags, period=period)
        data.append(d)
    df = pd.concat(data, axis=0)
    df.to_pickle('pkl/datasets/gran{2}_period{1}_lags{0}.pkl'.format(lags, period, gran))
    del df


