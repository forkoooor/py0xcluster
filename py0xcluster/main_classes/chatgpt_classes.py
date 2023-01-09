from datetime import datetime
import os 

import pandas as pd

from py0xcluster.utils.query_utils import *

class PoolSelector:
    def __init__(
            self, 
            subgraph_url: str,
            min_daily_volume_USD: int = 100000, 
            start_date: tuple = None, 
            end_date: tuple = None,
            days_batch_size: int = 15,
            min_days_active: int = None
            ) -> pd.DataFrame:
        
            self.subgraph_url = subgraph_url
            self.min_daily_volume_USD = min_daily_volume_USD
            self.start_date = start_date
            self.end_date = end_date
            self.days_batch_size = days_batch_size
            self.min_days_active = min_days_active
    
    def _normalize_pools_data(self, pools_data: list):
        # first level of normalization
        df = pd.json_normalize(pools_data, meta=['pool.inputTokens'])
        df_input_tokens = pd.json_normalize(df['pool.inputTokens'])

        # normalize all columns from df_input_tokens
        df_list = list()

        for col in df_input_tokens.columns:
            v = pd.json_normalize(df_input_tokens[col])
            v.columns = [f'token{col}_{c}' for c in v.columns]
            df_list.append(v)

            # combine into one dataframe
            df_normalized = pd.concat([df.iloc[:, 0:7]] + df_list, axis=1)

        return df_normalized

    def get_pools_data(self, verbose: bool = False):

        root_folder = os.path.abspath(os.path.join(__file__, '..', '..'))
        query_file_path = os.path.join(root_folder, 'queries', 'messari_getActivePools.gql')
                
        # Create the client
        client = GraphQLClient(self.subgraph_url)
        
        # Generate list of 2 items tuple, start and end date of the date batch
        days_batch_lim = [dates_lim for dates_lim in 
            days_interval_tuples(self.start_date, self.end_date, self.days_batch_size)]
        
        full_results = []
        for days_batch in days_batch_lim:
            start_batch = timestamp_tuple_to_unix(days_batch[0])
            end_batch = timestamp_tuple_to_unix(days_batch[1])

            if verbose:
                print(f'Queriying from {days_batch[0]} to {days_batch[1]}')

            variables = {
                'start_date': start_batch,
                'end_date': end_batch,
                'minVolumeUSD': self.min_daily_volume_USD
                }


            # Run the GraphQL query
            result = client.run_query(query_file_path, variables=variables)
            
            # Break the loop if there are no more results
            if len(result) == 0:
                print('no data for this batch, exiting query')
                break

            # Add the results to the list
            full_results.extend(result)

        # normalize data from liquidityPoolDailySnapshots
        df_pools_data = self._normalize_pools_data(full_results)
        
        return df_pools_data
            
    def select_active_pairs(self, df):
        # Filter the DataFrame to only include pairs that have at least
        # `self.min_trades` trades and have been active for at least
        # `self.min_days_active` days
        df = df[df['trades'] >= self.min_trades]
        df = df[df['daysActive'] >= self.min_days_active]
        
        # Sort the DataFrame by `daysActive` in descending order
        df = df.sort_values('daysActive', ascending=False)
        
        return df
        
    def select_recent_pairs(self, df):
        # Get the current timestamp
        current_timestamp = datetime.now().timestamp()
        
        # Filter the DataFrame to only include pairs that have been inactive for
        # less than `self.max_days_inactive` days
        df = df[(current_timestamp - df['lastTrade']) / (3600 * 24) < self.max_days_inactive]
        
        return df
        
    def get_selected_pairs(self):
        # Get the pair data
        df = self.get_pair_data()
        
        # Select active pairs
        df = self.select_active_pairs(df)
        
        # Select recently inactive pairs
        df = self.select_recent_pairs(df)
        
        return df