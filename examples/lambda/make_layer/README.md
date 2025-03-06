# AWS Lambda Layer를 활용한 Python 패키지 배포

이 문서는 AWS Lambda에서 **외부 Python 패키지** (예: `boto3`, `pandas`, `numpy`, `plotly` 등)을 **Lambda Layer**로 배포하는 방법을 설명합니다.

---

## 1. Lambda Layer란?

AWS Lambda Layer는 여러 Lambda 함수에서 공통으로 사용할 수 있는 라이브러리 패키지를 저장하는 공간입니다.  
Layer를 사용하면 Lambda 함수의 크기를 줄이고, 여러 함수에서 동일한 라이브러리를 공유할 수 있습니다.

---

## 2. `requirements.txt` 파일 생성

배포할 패키지를 정의하는 `requirements.txt` 파일을 생성합니다.

```sh
echo "numpy" >> requirements.txt
echo "plotly" >> requirements.txt
```
	참고: concurrent.futures는 Python 표준 라이브러리에 포함되어 있으므로, requirements.txt에 포함하지 않습니다.

⸻

## 3. Python 패키지 설치

pip install -r 명령어를 사용하여, requirements.txt에 있는 패키지를 Lambda Layer에서 사용할 python/ 폴더에 설치합니다.
필요 없는 캐시 파일을 포함하지 않도록 --no-cache-dir 옵션을 추가하면 도움이 됩니다.
```sh
mkdir -p python
pip install -r requirements.txt -t python/ --no-cache-dir
```
	•	-t python/ 옵션을 사용하면 패키지가 python/ 폴더에 설치됩니다.
	•	AWS Lambda는 Layer 내부의 /python 폴더를 자동으로 인식하므로, 이 폴더명을 유지해야 합니다.

⸻

## 4. Layer ZIP 파일 생성

설치된 패키지를 ZIP 파일로 압축합니다.
```sh
zip -r layer.zip python/
```
생성된 layer.zip 파일을 AWS Lambda Layer로 업로드할 수 있습니다.

⸻

## 5. AWS Lambda Layer 업로드

다음 명령어로 layer.zip 파일을 AWS Lambda Layer로 업로드합니다. 만약 50메가 이상의 패키지 압축파일의 경우 S3에 업로드 후 참조합니다. 
```sh
aws lambda publish-layer-version \
    --layer-name my-python-layer \
    --zip-file fileb://layer.zip \
    --compatible-runtimes python3.9 python3.8 python3.7 python3.11 python3.12
```
	•	Layer 이름: my-python-layer
	•	호환 런타임: Python 3.7, 3.8, 3.9

## 6. pandas Lambda Layer 업로드 방법 

pandas는 데이터 처리와 분석을 위한 풍부한 기능을 제공하다 보니 내부에 많은 모듈과 의존성을 포함하고 있습니다.
기본 S3및 업로드기능을 사용하면 용량 lambda 용량 초과됩니다. 컨테이너 레이어를 사용하거나(10G까지 가능) Lambda 함수에서 
Add a layer에서 아래 ARN을 지정합니다. 

- https://github.com/keithrozario/Klayers

S3 경로를 사용하여 새 레이어 버전 게시방법
```sh
aws lambda publish-layer-version \
    --layer-name my-python-layer \
    --content S3Bucket=YOUR_BUCKET_NAME,S3Key=layer.zip \
    --compatible-runtimes python3.9 python3.8 python3.7 python3.11 python3.12
```


⸻

## 7. Lambda 함수에서 Layer 사용하기

Lambda 콘솔에서 생성한 Layer를 추가하는 방법은 다음과 같습니다:
	1.	AWS Lambda 콘솔로 이동
	2.	기존 Lambda 함수 선택 또는 새 함수 생성
	3.	Layers 탭에서 Add a layer 클릭
	4.	Custom Layer 선택 후 my-python-layer 추가
	5.	Lambda 코드에서 패키지 사용 가능

⸻

## 8. Lambda에서 패키지 정상 동작 확인

Layer를 추가한 후, Lambda 함수에서 아래와 같이 패키지가 정상적으로 작동하는지 확인합니다.
```python
import boto3
import pandas as pd
import numpy as np
import plotly.express as px

def lambda_handler(event, context):
    print("Lambda Layer loaded successfully!")
    df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
    print(df)
    return {"statusCode": 200, "body": "Lambda with Layer is working!"}
```
위 코드가 정상 실행되면, Lambda Layer가 성공적으로 적용된 것입니다.

⸻

## 8. Lambda Layer 배포 프로세스 정리

Lambda Layer 배포 과정은 다음과 같습니다:
	1.	requirements.txt 파일 생성 (예: boto3, pandas, numpy, plotly 등)
	2.	pip install -r requirements.txt -t python/ 실행하여 패키지를 /python 폴더에 설치
	3.	zip -r layer.zip python/ 명령어로 ZIP 파일 생성
	4.	aws lambda publish-layer-version 명령어로 AWS Layer에 업로드
	5.	Lambda 함수에서 생성한 Layer 추가 후 사용

⸻

필요한 패키지를 추가하여 원하는 대로 Layer를 활용해 보세요.

콘솔 설정의 경우 아래 링크를 참조하세요. 
- https://catalog.us-east-1.prod.workshops.aws/workshops/86f59566-0ae7-44be-80ab-9044b83c88f2/ko-KR/agent/lambda

