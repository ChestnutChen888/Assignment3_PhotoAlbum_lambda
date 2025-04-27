import json
import boto3
import requests
from requests_aws4auth import AWS4Auth

region = 'us-east-1' # For example, us-west-1
service = 'es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

host = 'https://search-photos-mm5eyjsilg65lx5qv4qsmnf2rm.aos.us-east-1.on.aws' # The OpenSearch domain endpoint with https:// and without a trailing slash
index = 'photos1'
url = host + '/' + index + '/_search'

lex_client = boto3.client('lexv2-runtime')

def lambda_handler(event, context):

    query = (event.get('queryStringParameters') or {}).get('q', '')
    if not query:
        return {
            'statusCode': 400,
            'body': json.dumps({"error": "Missing required query parameter"})
        }

    response = lex_client.recognize_text(
        botId='PSGZMGSANW',
        botAliasId='TSTALIASID',
        localeId='en_US',
        sessionId="test_session",
        text=query
    )

    slots = response['sessionState']['intent']['slots']

    response1 = slots['Keyword1']['value']['interpretedValue'] if slots.get('Keyword1') and slots['Keyword1'].get('value') and slots['Keyword1']['value'].get('interpretedValue') else None
    response2 = slots['Keyword2']['value']['interpretedValue'] if slots.get('Keyword2') and slots['Keyword2'].get('value') and slots['Keyword2']['value'].get('interpretedValue') else None

    keyword1 = response1.lower() if response1 else ""
    keyword2 = response2.lower() if response2 else ""

    query_string = f"{keyword1} {keyword2}".strip()

    query = {
                "query": {
                    "multi_match": {
                        "query": query_string,
                        "fields": ["labels"],
                        "analyzer": "english",
                        "operator": "or"
                    }
                }  
            }

    headers = { "Content-Type": "application/json" }

    response = requests.get(url, auth=awsauth, headers=headers, data=json.dumps(query))

    results = []

    for hit in response.json()['hits']['hits']:
        objectKey = hit['_source']['objectKey']
        bucket = hit['_source']['bucket']
        object_url = f"https://{bucket}.s3.amazonaws.com/{objectKey}"
        labels = hit['_source']['labels']
        results.append({
            "url": object_url,
            "labels": labels
        })

    response = {
        "results": results
    }


    return {
        'statusCode': 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        'body': json.dumps(response)
    }
