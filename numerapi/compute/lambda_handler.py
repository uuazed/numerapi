import pandas as pd
from numerapi import NumerAPI
import boto3
import json
import logging

logger = logging.getLogger(__name__)

secretsmanager = boto3.client('secretsmanager')
api_keys_secret = secretsmanager.get_secret_value(SecretId='numerai-api-keys')
secret = json.loads(api_keys_secret['SecretString'])


def run(event, context):
    print(event)
    print(context)

    napi = NumerAPI(
        public_id=secret['public_id'],
        secret_key=secret['secret_key']
    )

    model_id = event['model_id']

    request_id = context.aws_request_id
    log_stream_name = context.log_stream_name
    set_lambda_status(context.function_name, model_id, request_id, "in_progress", napi, log_stream_name)

    try:

        current_round = napi.get_current_round()
        napi.download_dataset("v4/live.parquet", f"/tmp/v4/live_{current_round}.parquet")
        live_data = pd.read_parquet(f'/tmp/v4/live_{current_round}.parquet')

        s3 = boto3.client('s3')
        aws_account_id = boto3.client('sts').get_caller_identity().get('Account')
        s3.download_file(f'numerai-compute-{aws_account_id}', f'{model_id}/model.pkl', '/tmp/model.pkl')
        model = pd.read_pickle(f"/tmp/model.pkl")

        model_name = 'model'
        s3.download_file(f'numerai-compute-{aws_account_id}', f'{model_id}/features.json', '/tmp/features.json')
        f = open('/tmp/features.json')
        features = json.load(f)

        live_data.loc[:, f"preds_{model_name}"] = model.predict(
            live_data.loc[:, features])

        live_data["prediction"] = live_data[f"preds_{model_name}"].rank(pct=True)

        predict_output_path = f"/tmp/live_predictions_{current_round}.csv"
        live_data["prediction"].to_csv(predict_output_path)

        print(f'submitting {predict_output_path}')
        napi.upload_predictions(predict_output_path, model_id=model_id)
        print('submission complete!')

    except Exception as ex:
        set_lambda_status(context.function_name, model_id, request_id, "error", napi, log_stream_name)
        return False

    set_lambda_status(context.function_name, model_id, request_id, "complete", napi, log_stream_name)

    return True


def set_lambda_status(function_name, model_id, request_id, status, napi, log_stream_name=None):
    query = f'''
        mutation setModelLambdaStatus($function_name: String!, $model_id: String!, $request_id: String!, $status: String!, $log_stream_name: String) {{
          modelLambdaStatus(
            functionName: $function_name, 
            modelId: $model_id, 
            requestId: $request_id, 
            status: $status,
            logStreamName: $log_stream_name) {{
            requestId
          }}
        }}
        '''
    napi.raw_query(
        query=query,
        authorization=True,
        variables={
            'function_name': function_name,
            'model_id': model_id,
            'request_id': request_id,
            'status': status,
            'log_stream_name': log_stream_name
        }
    )


if __name__ == '__main__':
    run({}, {})
