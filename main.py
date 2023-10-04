from utils import *

data = pd.read_csv("data/endpoints.csv")

for row in data.iterrows():
    endpoint = row[1]['EndPoint']
    request_body = json.loads(row[1]['Json'])
    for api_call_count in range(API_CALLS):
        logger.info(f"API call count: {api_call_count}")
        make_post_request(endpoint, request_body, HEADERS, TIMEOUT)