# lambda/index.py
import json
import os
import boto3
import re  # 正規表現モジュールをインポート
from botocore.exceptions import ClientError
import urllib.request

#event：API Gateway などから渡されるリクエスト情報全体の辞書
#context：Lambda 実行時に AWS が渡すメタ情報（関数名・ARN・残り実行時間など）

#FastAPI用
def lambda_handler(event, context):
    try:

        # Cognitoで認証されたユーザー情報を取得
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")

        #リクエストボディ解析
        body = json.loads(event['body'])
        prompt = body['message']
        if prompt is None:
            raise ValueError("No 'message' in request body")

        #外部 API 呼び出し
        url = "https://86a8-34-125-31-86.ngrok-free.app/generate"
        payload = {
            "prompt": prompt,
            "max_new_tokens": 512,
            "do_sample": True,
            "temperature": 0.7,
            "top_p": 0.9
        }
        #HTTP通信においてデータはバイト列で送られるので、utf-8でエンコード
        #pythonのデータ構造→JSON文字列→バイト列
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=200) as res:
            text   = res.read().decode("utf-8")
            result = json.loads(text)

        # ──────────── レスポンス整形 ────────────
        generated = result.get("generated_text")
        response_body = {
            "success":        True,
            "generated_text": generated,
            "response_time":  result.get("response_time", 0)
        }

        return {
            "statusCode": 200,
            "headers":    { "Content-Type": "application/json"},
            "body":       json.dumps(response_body)
        }

    except urllib.error.HTTPError as e:
        # 4xx/5xx エラー
        err_body = e.read().decode("utf-8")
        return {
            "statusCode": e.code,
            "body":       json.dumps({"success": False, "error": err_body})
        }

    except Exception as e:
        # それ以外の例外
        return {
            "statusCode": 500,
            "body":       json.dumps({"success": False, "error": str(e)})
        }
