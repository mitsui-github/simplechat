# lambda/index.py
import json
import os
import boto3
import re  # 正規表現モジュールをインポート
from botocore.exceptions import ClientError
import urllib.request

# Lambda コンテキストからリージョンを抽出する関数
def extract_region_from_arn(arn):
    # ARN 形式: arn:aws:lambda:region:account-id:function:function-name
    match = re.search('arn:aws:lambda:([^:]+):', arn)
    if match:
        return match.group(1)
    return "us-east-1"  # デフォルト値

# グローバル変数としてクライアントを初期化（初期値）
bedrock_client = None

# モデルID
#デプロイ時やテスト時に、環境変数経由で簡単に呼び出すモデルを切り替えられるようにするため
MODEL_ID = os.environ.get("MODEL_ID", "us.amazon.nova-lite-v1:0")

#event：API Gateway などから渡されるリクエスト情報全体の辞書
#context：Lambda 実行時に AWS が渡すメタ情報（関数名・ARN・残り実行時間など）
# def lambda_handler(event, context):
#     # try:
#         # コンテキストから実行リージョンを取得し、クライアントを初期化
#         global bedrock_client
#         if bedrock_client is None:
#             region = extract_region_from_arn(context.invoked_function_arn)
#             bedrock_client = boto3.client('bedrock-runtime', region_name=region)
#             print(f"Initialized Bedrock client in region: {region}")
        
#         print("Received event:", json.dumps(event))
        
#         # Cognitoで認証されたユーザー情報を取得
#         user_info = None
#         if 'requestContext' in event and 'authorizer' in event['requestContext']:
#             user_info = event['requestContext']['authorizer']['claims']
#             print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")
        
#         # リクエストボディの解析
#         #event は API Gateway から渡された Lambda イベント全体の辞書で、HTTP リクエストの「生の本文」は文字列として event['body'] に入っています。
#         body = json.loads(event['body'])
#         message = body['message']
#         conversation_history = body.get('conversationHistory', [])
        
#         print("Processing message:", message)
#         print("Using model:", MODEL_ID)
        
#         # 会話履歴を使用
#         messages = conversation_history.copy()
        
#         # ユーザーメッセージを追加
#         messages.append({
#             "role": "user",
#             "content": message
#         })
        
        # Nova Liteモデル用のリクエストペイロードを構築
        # 会話履歴を含める
        # bedrock_messages = []
        # for msg in messages:
        #     if msg["role"] == "user":
        #         bedrock_messages.append({
        #             "role": "user",
        #             "content": [{"text": msg["content"]}]
        #         })
        #     elif msg["role"] == "assistant":
        #         bedrock_messages.append({
        #             "role": "assistant", 
        #             "content": [{"text": msg["content"]}]
        #         })
        
        # # invoke_model用のリクエストペイロード
        # request_payload = {
        #     "messages": bedrock_messages,
        #     "inferenceConfig": {
        #         "maxTokens": 512,
        #         "stopSequences": [],
        #         "temperature": 0.7,
        #         "topP": 0.9
        #     }
        # }

#FastAPI用
def lambda_handler(event, context):
    # ──────────────── request body 解析 ────────────────
    body = json.loads(event['body'])
    prompt = body['message']  # フロントから送られたメッセージ

    # ──────────────── ngrok エンドポイント設定 ────────────────
    url = "https://0641-35-247-128-210.ngrok-free.app/generate"
    payload = {
        "prompt": prompt,
        "max_new_tokens": 512,
        "do_sample": True,
        "temperature": 0.7,
        "top_p": 0.9
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}

    # ──────────────── Request オブジェクト作成 ────────────────
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        # ──────────────── ネットワーク送信 ────────────────
        with urllib.request.urlopen(req, timeout=200) as res:
            text = res.read().decode("utf-8")    # バイト→文字列
            result = json.loads(text)           # 文字列→辞書

        # ──────────────── generated_text を抽出 ────────────────
        generated = result.get("generated_text", "")

        # ──────────────── Lambda の返却フォーマット ────────────────
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type":                "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers":"Content-Type",
                "Access-Control-Allow-Methods":"OPTIONS,POST"
            },
            "body": json.dumps({
                "success":        True,
                "generated_text": generated,
                "response_time":  result.get("response_time")
            })
        }

    except urllib.error.HTTPError as e:
        # 4xx/5xx エラー
        err_body = e.read().decode()
        return {
            "statusCode": e.code,
            "body":        json.dumps({"success": False, "error": err_body})
        }

    except urllib.error.URLError as e:
        # ネットワーク到達失敗など
        return {
            "statusCode": 502,
            "body":        json.dumps({"success": False, "error": str(e.reason)})
        }
        # url = "https://0641-35-247-128-210.ngrok-free.app/generate"

        # request_payload ={
        # "prompt": message,
        # "max_new_tokens": 512,
        # "do_sample":True,
        # "temperature": 0.7,
        # "top_p": 0.9
        # }

        # data = json.dumps(request_payload).encode("utf-8")

        # headers = {
        #     "Content-Type": "application/json",
        # }

        # response = urllib.request.Request(url, data=data, headers=headers)
        
        # print("Calling Bedrock invoke_model API with payload:", json.dumps(request_payload))
        
        # invoke_model APIを呼び出し
        # response = bedrock_client.invoke_model(
        #     modelId=MODEL_ID,
        #     body=json.dumps(request_payload),
        #     contentType="application/json"
        # )
        
        # # レスポンスを解析
        # response_body = json.loads(response['generated_text'].read())
        # return json.dumps(response_body, default=str)
        
    #     # 応答の検証
    #     if not response_body.get('output') or not response_body['output'].get('message') or not response_body['output']['message'].get('content'):
    #         raise Exception("No response content from the model")
        
    #     # アシスタントの応答を取得
    #     assistant_response = response_body['output']['message']['content'][0]['text']
        
    #     # アシスタントの応答を会話履歴に追加
    #     messages.append({
    #         "role": "assistant",
    #         "content": assistant_response
    #     })
        
    #     # 成功レスポンスの返却
    #     return {
    #         "statusCode": 200,
    #         "headers": {
    #             "Content-Type": "application/json",
    #             "Access-Control-Allow-Origin": "*",
    #             "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    #             "Access-Control-Allow-Methods": "OPTIONS,POST"
    #         },
    #         "body": json.dumps({
    #             "success": True,
    #             "response": assistant_response,
    #             "conversationHistory": messages
    #         })
    #     }
        
    # except Exception as error:
    #     print("Error:", str(error))
        
    #     return {
    #         "statusCode": 500,
    #         "headers": {
    #             "Content-Type": "application/json",
    #             "Access-Control-Allow-Origin": "*",
    #             "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    #             "Access-Control-Allow-Methods": "OPTIONS,POST"
    #         },
    #         "body": json.dumps({
    #             "success": False,
    #             "error": str(error)
    #         })
    #     }
