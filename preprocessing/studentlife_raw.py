from sklearn.preprocessing import LabelEncoder
import pandas as pd
import numpy as np
from collections import Counter
from utils.utils import file_exists
from datetime import datetime


'''

#Audio Inference
#ID	Description
#0	Silence
#1	Voice
#2	Noise
#3	Unknown

#Activity Inference ID	Description
#0	Stationary
#1  Walking
#2	Running
#3	Unknown

cuando la actividad que mas se lleva a cabo es unknown, el porcentaje de actividad
sedentaria para esa hora es similar al promedio de actividad sedentaria para las
hora donde la act q mas se lleva a cabo es 1 (walking), por eso se lo va a tomar
como si fuera de ese tipo

activitymajor
0    0.937012
1    0.296808
2    0.073199
3    0.201710


#
#
# ## Feature generation ##
#
# **Features:**
# * Stationaty mean per hour
# * Day of the week (weekday,saturday or sunday)
# * Hour of the day
# * activityMajor: the type of activity with the most instances in a 1-hour time bucket
# * audioMajor
# * latitude average and stv
# * longitud avg and stv
# * is Charging

#como tratar los valores nulos??
    # los deadlines son solo de 44 de 49 estudiantes
    # los datos de audio no estan para todas la horas de todos los estudiantes
    # los datos de ubicacion son infimos


hay 14420.575126 en promedio de muestros de actividad por hora
'''

'''
def get_total_harversine_distance_traveled(x):
    d = 0.0
    samples = x.shape[0]
    for i in np.arange(0, samples):
        try:
            d += haversine(x.iloc[i, :].values, x.iloc[i + 1, :].values)
        except IndexError:
            pass
    return d
'''

def downgrade_datatypes(df):
    df_int = df.select_dtypes(include=['int'])
    converted_int = df_int.apply(pd.to_numeric, downcast='signed')
    df[converted_int.columns] = converted_int
    df_float = df.select_dtypes(include=['float'])
    converted_float = df_float.apply(pd.to_numeric, downcast='float')
    df[converted_float.columns] = converted_float
    return df


def create_sensing_table(sensor):
    """
    Creates one dataframe from all the sensor data of all users

    dataset raw data should be at dataset/sensing/ in the project folder
    """
    filename = f'pkl/sensing_data/{sensor}.pkl'
    if file_exists(filename):
        print(f'{sensor} data already generated')
    else:
        path = 'dataset/sensing/' + sensor + '/' + sensor + '_u'
        df = pd.read_csv(path + '00' + '.csv', index_col=False)
        df['userId'] = '00'
        for a in range(1, 60):
            userId = '0' + str(a) if a < 10 else str(a)
            try:
                aux = pd.read_csv(path + userId + '.csv', index_col=False)
                aux['userId'] = a
                df = df.append(aux)
            except:
                pass
        df['userId'] = df['userId'].astype('int8')

        #downgrade datatypes

        df = downgrade_datatypes(df)

        df.to_pickle(filename)


def create_sensing_tables():
    sensor_data_files = ['activity', 'audio', 'bt','gps', 'dark',
                         'phonelock', 'wifi', 'phonecharge', 'bt',
                         'calendar', 'wifi_location', 'conversation']
    for file in sensor_data_files:
        create_sensing_table(file)


def get_sensor_data(sensor) -> pd.DataFrame:
    return downgrade_datatypes(pd.read_pickle(f'pkl/sensing_data/{sensor}.pkl'))


def get_studentlife_dataset(freq='1h'):

    def floor_time(df, col='time'):
        df[col] = pd.to_datetime(df[col], unit='s').dt.floor(freq)
        return df


    def Most_Common(lst):
        data = Counter(lst)
        return data.most_common(1)[0][0]


    def fill_by_interval(df, col):
        tuples = list()
        for _, t in df.iterrows():
            tuples +=  [ (t.userId, d) for d in pd.date_range(start=t['start'], end=t['end'], freq=freq)]

        #drop duplicates cause there are intervals that matches the hour if finish and the hour of start
        ind = pd.MultiIndex.from_tuples(tuples, names = ['f','s']).drop_duplicates() 

        aux_series = pd.Series(index=ind, dtype='bool')
        aux_series[:] = True
        s[col] = aux_series
        s.loc[:,col].fillna(False, inplace=True)


    def count_by_interval(df, col):
        tuples = list()
        for _, t in df.iterrows():
            if t['start'] == t['end']:
                r = pd.date_range(start=t['start'], end=t['end'], freq=freq)
            else:
                r = [t['start']]
            tuples +=  [ (t.userId, d) for d in r]
        #drop duplicates cause there are intervals that matches the hour if finish and the hour of start are equal
        ind = pd.MultiIndex.from_tuples(tuples, names = ['f','s'])
        aux_series = pd.Series(index=ind)
        convs_per_hour = aux_series.groupby(aux_series.index).size().astype('int')
        s[col] = convs_per_hour
        s.loc[:,col].fillna(0, inplace=True)

    filename = f'pkl/sedentarismdata_gran{freq}.pkl'
    if not file_exists(filename):
        print(f'{filename} does not exist. This may take a while...')
        # prepare activity data
        sdata = get_sensor_data('activity')
        sdata.columns = ['time', 'activityId', 'userId']
        sdata = sdata.loc[sdata['activityId'] != 3]
        sdata = floor_time(sdata)

        '''
        Set dataset index from the cartesian product between
        the users id and
        the minimun and maximun date found

        '''
        uindex = sdata['userId'].drop_duplicates()

        min_date = sdata.time.min()
        max_date = sdata.time.max()
        dindex = pd.date_range(min_date, max_date, freq=freq)
        index = pd.MultiIndex.from_product(iterables=[uindex, dindex],
                                            names=['userId', 'time'])
        s = pd.DataFrame(index = index)

        sdata = pd.concat([sdata, pd.get_dummies(sdata['activityId'], prefix='act')], axis=1, sort=False)

        # logs per activity
        count_per_activity = sdata.groupby(['userId', 'time'])[['act_0', 'act_1', 'act_2']].sum()

        for col in count_per_activity.columns:
            s[col] = count_per_activity[col].astype('int')

        # activitymajor
        s['activitymajor'] = sdata.groupby(['userId', 'time'])['activityId'].apply(Most_Common).astype('object')
        #s.dropna(how='all', inplace=True) #here all or ... is the same as if a columns is nan the other too


        seconds = s.index.get_level_values('time').seconds
        seconds_in_day = 24*60*60
        df['second_sin'] = np.sin(2*np.pi*seconds / seconds_in_day)
        df['second_cos'] = np.cos(2*np.pi*seconds / seconds_in_day)


        # dayofweek
        dayofweek = s.index.get_level_values('time').dayofweek
        days_in_week = 7
        s['dayofweek_sin'] = np.sin(2 * np.pi * dayofweek / days_in_week)
        s['dayofweek_cos'] = np.cos(2 * np.pi * dayofweek / days_in_week)

        # past minutes since the day began and remaining minutes of the day
        s['past_minutes'] = s.index.get_level_values(1).hour * 60 + s.index.get_level_values(1).minute
        s['remaining_minutes'] = 24 * 60 - s['past_minutes']

        s['is_weekend'] = ((s.index.get_level_values(1).dayofweek==0) | \
            (s.index.get_level_values(1).dayofweek==6))


        # prepare audio data
        adata = get_sensor_data('audio')
        adata.columns = ['time', 'audioId', 'userId']
        adata = floor_time(adata)

        # audiomajor
        s['audiomajor'] = adata.groupby(['userId', 'time'])['audioId'].apply(Most_Common)
        # los siguientes usuarios poseen horas completas en las cuales no tienen ningun registro de audio
        #s.loc[s['audiomajor'].isnull(), 'audiomajor'].groupby('userId').size()
        s.loc[:, 'audiomajor'].fillna(method='ffill', axis=0, inplace=True) #suponiendo que se deja de grabar cuando no hay ruido
        s.audiomajor = s.audiomajor.astype('object')    


        adata = pd.concat([adata, pd.get_dummies(adata['audioId'], prefix='audio')], axis=1, sort=False)


        count_per_audio = adata.groupby(['userId', 'time'])[['audio_0', 'audio_1', 'audio_2']].sum()


        for col in count_per_audio.columns:
            s[col] = count_per_audio[col].astype('int64')

        # latitude and longitude mean and std
        gpsdata = get_sensor_data('gps')
        #gpsdata = floor_time(gpsdata)

        gpsdata = gpsdata.loc[:,['latitude','longitude', 'time', 'userId']]
        gpsdata['time'] = pd.to_datetime(gpsdata['time'], unit='s')
        gpsdata_shifted = gpsdata.groupby('userId').shift(1)
        gpsdata_shifted.columns = [f's_{col}' for col in gpsdata.columns if col!='userId']
        gpsdata = pd.concat([gpsdata, gpsdata_shifted], axis=1)
        gpsdata.dropna(axis=0, inplace=True)
        gpsdata['diff_date'] = (gpsdata.time - gpsdata.s_time).dt.seconds
        gpsdata['diff_lat'] = gpsdata.latitude - gpsdata.s_latitude
        gpsdata['diff_lon'] = gpsdata.longitude - gpsdata.s_longitude
        gpsdata['instantaneous_speed'] = np.sqrt( np.square(gpsdata.diff_lat / gpsdata.diff_date) + 
                                    np.square(gpsdata.diff_lon / gpsdata.diff_date))
        gpsdata['lat_plus_lon'] = np.sqrt(np.square(gpsdata.diff_lat) + np.square(gpsdata.diff_lon))
        gpsdata.time = gpsdata.time.dt.floor(freq)
        g = gpsdata.groupby(['userId','time'])
        date_features = g.agg({'instantaneous_speed': ['mean','var'], 'lat_plus_lon': 'sum'})
        date_features.columns = ['speed_mean', 'speed_variance','total_distance']
        date_features.fillna(0, inplace=True)
        gps_grouped = gpsdata.groupby(['userId', 'time'])
        s['location_variance'] = gps_grouped['longitude'].var() + gps_grouped['latitude'].var()
        s['location_mean'] = gps_grouped['longitude'].mean() + gps_grouped['latitude'].mean()
        s = s.join(date_features)

        s.loc[:, 'location_mean'] = s.groupby(level=0)['location_mean'].fillna(method='ffill', axis=0). \
            groupby(level=0).fillna(method='bfill', axis=0)
        for col in ['location_variance', 'speed_mean', 'speed_variance','total_distance']:
            s.loc[:, col].fillna(0, axis=0, inplace=True) # if it is NaN I suppose the user did not move and so std=0

        # prepare charge data
        chargedata = get_sensor_data('phonecharge')
        chargedata = floor_time(chargedata, 'start')
        chargedata = floor_time(chargedata, 'end')



        fill_by_interval(chargedata, 'isCharging')
        #s.drop('numberOfConversations', axis=1, inplace=True)

        # prepare lock data
        lockeddata = get_sensor_data('phonelock')
        lockeddata = floor_time(lockeddata, 'start')
        lockeddata = floor_time(lockeddata, 'end')

        # isLocked
        fill_by_interval(lockeddata, 'isLocked')

        # prepare dark data
        darkdata = get_sensor_data('dark')
        darkdata = floor_time(darkdata, 'start')
        darkdata = floor_time(darkdata, 'end')
        # isInDark
        fill_by_interval(darkdata, 'isInDark')

        # prepare conversation data
        conversationData = get_sensor_data('conversation')
        conversationData.columns = ['start', 'end', 'userId']
        conversationData = floor_time(conversationData, 'start')
        conversationData = floor_time(conversationData, 'end')
        count_by_interval(conversationData, 'nbConv')

        calendardata = get_sensor_data('calendar')
        calendardata['time'] = pd.to_datetime(calendardata['DATE'] + ' ' + calendardata['TIME'])
        calendardata['time'] = calendardata['time'].dt.floor(freq)
        calendardata = calendardata.set_index(['userId', 'time'])

        s['hasCalendarEvent'] = False
        s.loc[s.index & calendardata.index, 'hasCalendarEvent'] = True

        # hay datos sobre los wifi mas cercano y ademas sobre los que el usuario estuvo
        # dentro del lugar dnd estaba el wifi,
        # hasta elmomento no se utilizan los datos de wifi cercanos
        # se deja el wifi mas cercano, ademas de la cantidad de wifis
        # a los que se conecto cada usuario en una hora, que puede ser un indicador
        # de sedentarismo

        wifidata = get_sensor_data('wifi_location')
        wifidata = floor_time(wifidata)
        wifidataIn = wifidata.loc[wifidata['location'].str.startswith('in')]
        label_encoder = LabelEncoder()
        integer_encoded = label_encoder.fit_transform(wifidataIn['location'].values)
        wifidataIn['location'] = integer_encoded

        # s['wifiMajor'] = 0.0
        # s['wifiMajor'] = wifidataIn.groupby(['userId', 'time'])['location'].apply(Most_Common)
        # s.loc[s['wifiMajor'].isna()] = 0
        wifidataIn.reset_index(inplace=True, drop=True)

        wifiChanges = wifidataIn.groupby(['userId', 'time'])['location'].nunique().astype('int')
        s.loc[:, 'wifiChanges'] = wifiChanges
        s.wifiChanges.fillna(0, inplace=True)
        # a = wifidataIn.groupby(['userId', 'time'])['location']
        # wifidataNear = wfidata.loc[wifidata['location'].str.startswith('near')]

        s.to_pickle(filename)
    else:
        print('Prepocessed StudentLife dataset already generated!')

    return downgrade_datatypes(pd.read_pickle(filename))



