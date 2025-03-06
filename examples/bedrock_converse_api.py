import boto3
import json
import sys

def chunk_handler(chunk):
    print(chunk, end='')

def get_streaming_response(prompt, model_id, streaming_callback):
    session = boto3.Session()
    
    bedrock = session.client(service_name='bedrock-runtime')

    message = {
        "role": "user",
        "content": [{"text": prompt}]
    }
    
    try:
        response = bedrock.converse_stream(
            modelId=model_id,
            messages=[message],
            inferenceConfig={
                "maxTokens": 2000,
                "temperature": 0.0
            }
        )

        print("---- Streaming Response ----")
        stream = response.get('stream')
        for event in stream:
            if "contentBlockDelta" in event:
                streaming_callback(event['contentBlockDelta']['delta']['text'])

            if "metadata" in event:
                print("\n\n---- usage ----")
                print(json.dumps(event['metadata']['usage'], indent=4))
                print("\n---- metrics ----")
                print(json.dumps(event['metadata']['metrics'], indent=4))
    except Exception as e:
        print(f"Error occurred: {e}")



def main():
    model_id = 'anthropic.claude-3-5-sonnet-20240620-v1:0'
    prompt = "대한민국에 섬은 총 몇개인가요?"
    get_streaming_response(prompt, model_id, chunk_handler)

if __name__ == '__main__':
    main()