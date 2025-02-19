import boto3
import json
import os
import pandas as pd


class BedrockService:
# 클래스 초기화
## AWS Bedrock 서비스 클라이언트 초기화
## us-east-1 리전 사용 (리전은 oregon으로 설정했습니다)
## Claude 3 Sonnet 을 기본 모델로 설정 (변경 필요하면 시도해보셔도 좋습니다)

    def __init__(self):
        self.bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name='us-east-1'
        )
        self.model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'

# 모델 호출
## Bedrock 모델 호출
## Prompt: 입력 텍스트
## max_tokens : 최대 응답 토큰 수
## temperature : 응답의 창의성 정도 (실험 필요시 조정하여 활용하실 수 있습니다)
    
    def invoke_model(self, prompt, max_tokens=1000, temperature=0.7):
        try:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": temperature
            }
            
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
            
        except Exception as e:
            print(f"Error invoking Bedrock model: {str(e)}")
            return None

# open search 연결 전 레벨에서의 자연어 쿼리 처리
## 자연어로 된 쿼리를 AWS 리소스 필터 파라미터로 전환
## 반환값: service_type, region, status를 포함하는 JSON 객체
## JSON 파싱로직 포함

    def process_natural_language_query(self, query):
        try:
            prompt = f"""
            Convert this natural language query to AWS resource filter parameters.
            Query: {query}
            
            Return only a JSON object with these exact fields:
            {{
                "service_type": "EC2" or "RDS" or "Lambda" or "S3",
                "region": "region name if specified, otherwise null",
                "status": "status if specified, otherwise null"
            }}
            """
            
            response = self.invoke_model(prompt, max_tokens=500, temperature=0)
            if response:
                try:
                    # JSON 문자열에서 실제 JSON 객체 부분만 추출
                    json_str = response.strip()
                    if '{' in json_str and '}' in json_str:
                        json_str = json_str[json_str.find('{'):json_str.rfind('}')+1]
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON response: {str(e)}")
                    return {
                        "service_type": None,
                        "region": None,
                        "status": None
                    }
            return None
        except Exception as e:
            print(f"Error in process_natural_language_query: {str(e)}")
            return None

# 비용 인사이트 생성
## AWS 비용 데이터를 분석하여 인사이트 제공
## 주요 비용 요인, 비정상패턴, 최적화 기회, 트랜드 등 분석
## DataFrame을 dict로 변환하여 처리함

    def generate_cost_insights(self, cost_data):
        try:
            cost_data_dict = {
                'service_costs': cost_data['service_costs'].to_dict(orient='records'),
                'region_costs': cost_data['region_costs'].to_dict(orient='records'),
                'daily_costs': cost_data['daily_costs'].to_dict(orient='records') if 'daily_costs' in cost_data else []
            }
    
            prompt = f"""
            다음 AWS 비용 데이터를 분석하여 상세한 인사이트를 제공해주세요:
            {json.dumps(cost_data_dict)}
            
            다음 항목들에 대해 분석해주세요:
            1. 주요 비용 발생 요인
            2. 비정상적인 패턴이나 급격한 비용 증가
            3. 비용 최적화가 가능한 영역
            4. 전반적인 비용 추세와 향후 예측
            
            분석 결과를 다음과 같은 형식으로 제공해주세요:
    
            ### 주요 비용 발생 요인
            - [구체적인 분석 내용]
    
            ### 이상 패턴 분석
            - [비정상적인 비용 패턴 설명]
    
            ### 최적화 기회
            - [구체적인 최적화 방안]
    
            ### 비용 추세
            - [추세 분석 및 예측]
            """
            return self.invoke_model(prompt, max_tokens=1500, temperature=0.3)
        except Exception as e:
            print(f"Error generating cost insights: {str(e)}")
            return "현재 비용 분석을 생성할 수 없습니다."
    

#추천 사항 강화
## AWS 리소스에 대한 최적화 추천사항 제공
## 구체적인 행동 계획, 비용 절감 가능성, 성능 영향 등 포함
## DataFrame 혹은 dict 형태의 데이터 처리 가능
    
    def enhance_recommendations(self, resource_data):
        try:
            if isinstance(resource_data, pd.DataFrame):
                resource_data = resource_data.to_dict(orient='records')
    
            prompt = f"""
            다음 AWS 리소스에 대한 상세한 최적화 전략을 제공해주세요:
            {json.dumps(resource_data)}
            
            다음 내용을 포함하여 자연스러운 문장으로 작성해주세요:
    
            1. 현재 상황 분석과 문제점
            2. 구체적인 최적화 방안과 기대효과
            3. 예상되는 비용 절감 효과
            4. 구현 시 고려사항과 주의점
            5. AWS 모범 사례 기반의 권장사항
    
            기술적인 내용을 포함하되, 이해하기 쉽게 설명해주세요.
            단계별 나열이나 목록 형태를 피하고, 자연스러운 문단 형태로 작성해주세요.
            resource id를 필수로 포함해주시고, tags 등 추가 정보가 있으면 함께 활용해주세요.
            """
            return self.invoke_model(prompt, max_tokens=1000, temperature=0.7)
        except Exception as e:
            print(f"Error enhancing recommendations: {str(e)}")
            return "현재 추천 사항을 생성할 수 없습니다."




# AWS 전문가 채팅
## AWS 관련 질문에 대한 전문가 수준의 응답제공
## 추가 컨텍스트 정보 활용
## 기술적이면서도 이해하기 쉬운 응답 생성
    
    def chat_with_aws_expert(self, user_question, context=None):
        try:
            # context가 DataFrame인 경우 dict로 변환
            if isinstance(context, pd.DataFrame):
                context = context.to_dict(orient='records')
            elif isinstance(context, dict):
                for key, value in context.items():
                    if isinstance(value, pd.DataFrame):
                        context[key] = value.to_dict(orient='records')

            prompt = f"""
            You are an AWS expert. Answer this question about AWS resources:
            Question: {user_question}
            
            Context (if available):
            {json.dumps(context) if context else 'No additional context provided'}
            
            Provide a detailed, technical, yet easy to understand response.
            """
            return self.invoke_model(prompt, max_tokens=2000, temperature=0.7)
        except Exception as e:
            print(f"Error in chat with AWS expert: {str(e)}")
            return "Unable to process your question at this time."
