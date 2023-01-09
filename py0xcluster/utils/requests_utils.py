import requests
import pandas as pd
import gql

# Pagination parameter
NB_BY_QUERY = 1000

def run_gql_query(subgraph_url, query, variables):
    # Construct the GraphQL client using the `gql` package
    client = gql.client(subgraph_url)

    # Execute the query and store the result
    result = client.execute(gql(query), variables=variables)

    # Return the result
    return result


def run_query(subgraph_url, query, variables, verbose): # A simple function to use requests.post to make the API call. Note the json= section.
    
    # variables = dict({(k, v) for (k, v) in variables.items()})
    # max_rows, skip, pair_address, dex_name, timestamp_start, timestamp_end
    # print(variables, type(variables))

    request = requests.post(subgraph_url, json={'query': query, 'variables': variables}) #, headers=self.headers)
    # print(request.status_code)
    if request.status_code == 200:
        #print(request.json())
        return request.json()
    else:
        raise Exception("Query failed to run by returning code of {}. {}. {}".format(request.status_code, request.json()['errors'], query))    

def df_from_queries(subgraph_url, queryTemplate, variables, baseobjects, verbose=False):
    full_df = pd.DataFrame()
    
    variables['max_rows'] = NB_BY_QUERY
    variables['skip'] = 0

    resp = run_query(subgraph_url, queryTemplate, variables, verbose)
    if 'errors' in resp.keys():
        print(resp['errors'])
        # disable exception to allow other results to be aggregated
        # despite an error 
        # raise Exception('Query error, see response above')
    
    else:
        resp_df = pd.json_normalize(resp['data'][baseobjects],  max_level=2)
        # print(resp_df)'swaps'
        while resp_df.shape[0] > 0:
            resp = run_query(subgraph_url, queryTemplate, variables, verbose)
            if verbose:
                print('skip varriable:', variables['skip'] + variables['max_rows'])
            try:
                resp_df = pd.json_normalize(resp['data'][baseobjects],  max_level=2)
                full_df = pd.concat([full_df, resp_df], axis=0)
                variables['skip'] += variables['max_rows']
            except:
                print('request aborted')
                print(resp)
                break

        
    return full_df
