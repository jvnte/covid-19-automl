import requests
import json

import numpy as np
import pandas as pd

from gluonts.dataset.common import ListDataset
from sktime.forecasting.model_selection import temporal_train_test_split
from datetime import datetime, timedelta


def fetch_timeseries(country: str = 'Germany'):
    # POST to API
    url = 'https://pomber.github.io/covid19/timeseries.json'
    response = requests.get(url=url)

    # Convert to data frame
    df = pd.DataFrame(json.loads(response.text)[country])

    # Rename columns
    df.columns = ['date', 'cum_cases', 'cum_deaths', 'cum_recoveries']

    # Create new features
    df['cases'] = df['cum_cases'].diff().fillna(0).astype(np.int64)
    df['deaths'] = df['cum_deaths'].diff().fillna(0).astype(np.int64)
    df['recoveries'] = df['cum_recoveries'].diff().fillna(0).astype(np.int64)

    return df


def prep_univariate(df, pred_start, horizon, type, freq):
    # Get covid cases
    df = df[['date', 'cases']]

    # Convert to Series object and set index
    df = df.set_index('date').iloc[:, 0]

    # Convert index to period index
    df.index = pd.to_datetime(df.index).to_period('D')

    # Define cutoff
    cut_off = (datetime.strptime(pred_start, "%Y-%m-%d")
               - timedelta(days=1)
               + timedelta(days=horizon)).strftime('%Y-%m-%d')

    # Cut timeseries
    df = df.loc[:cut_off]

    if type == 'deepar':
        # Get timeseries
        ts = df.to_numpy()

        start = df.index[0].to_timestamp(freq=freq)

        # train dataset: cut the last window of length "prediction_length", add "target" and "start" fields
        y_train = ListDataset([{'target': ts[:-horizon], 'start': start}],
                              freq=freq)
        # test dataset: use the whole dataset, add "target" and "start" fields
        y_test = ListDataset([{'target': ts, 'start': start}],
                             freq=freq)

    else:
        # Make temporal split
        y_train, y_test = temporal_train_test_split(df, test_size=horizon)

    return y_train, y_test


def prep_prophet(y_train, y_test):
    # Transform Series to Dataframe and rename columns
    y_train = y_train.to_frame().reset_index().rename(columns={'date': 'ds', 'cases': 'y'})
    y_test = y_test.to_frame().reset_index().rename(columns={'date': 'ds', 'cases': 'y'})

    # Transform date column to datetime
    y_train['ds'] = pd.to_datetime(y_train['ds'].astype('str'))
    y_test['ds'] = pd.to_datetime(y_test['ds'].astype('str'))

    return y_train, y_test
