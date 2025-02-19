import boto3
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import plotly.express as px
from concurrent.futures import ThreadPoolExecutor


# class 초기화 및 기본 설정
## AWS 서비스들과 상호작용하기 위한 boto3 client들을 초기화
## CloudWatch, EC2, RDS, Lambda, S3, Cost Exploere 서비스들에 대한 클라이언트 생성

class AWSResourceCollector:
    def __init__(self):
        print("Initializing AWSResourceCollector")
        self.cloudwatch = boto3.client('cloudwatch')
        self.ec2 = boto3.client('ec2')
        self.rds = boto3.client('rds')
        self.lambda_client = boto3.client('lambda')
        self.s3 = boto3.client('s3')
        self.ce = boto3.client('ce') # Cost Explorer 클라이언트 추가
        
        self.service_mapping = {
            'EC2': 'Amazon Elastic Compute Cloud - Compute',
            'RDS': 'Amazon Relational Database Service',
            'Lambda': 'AWS Lambda',
            'S3': 'Amazon Simple Storage Service'
        }
        
        # 모든 리전 목록 가져오기
        try:
            self.regions = [region['RegionName'] for region in self.ec2.describe_regions()['Regions']]
        except Exception as e:
            print(f"Error getting regions: {str(e)}")
            self.regions = ['us-east-1', 'us-west-2', 'ap-northeast-2']  # 기본 리전
            
        print("AWSResourceCollector initialized")

# CloudWatch metric 수집
## 각 AWS 리소스의 성능 메트릭을 수집
## CPU 사용률, 네트웤 I/O, 디스크사용량 등 서비스별 주요 메트릭을 가져옴
## 최근 1시간 동안의 데이터 수집 --> Customizing 필요한 경우 꼭 바꿔주세요!
    
    def get_cloudwatch_metrics(self, resource_id, service_type, region, period=3600):
        """CloudWatch 메트릭 데이터 수집"""
        try:
            cloudwatch = boto3.client('cloudwatch', region_name=region)
            metrics_data = {}
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)

            metric_configs = {
                'EC2': {
                    'namespace': 'AWS/EC2',
                    'dimension_name': 'InstanceId',
                    'metrics': [
                        ('CPUUtilization', 'Percent'),
                        ('NetworkIn', 'Bytes'),
                        ('NetworkOut', 'Bytes'),
                        ('DiskReadBytes', 'Bytes'),
                        ('DiskWriteBytes', 'Bytes')
                    ]
                },
                'RDS': {
                    'namespace': 'AWS/RDS',
                    'dimension_name': 'DBInstanceIdentifier',
                    'metrics': [
                        ('CPUUtilization', 'Percent'),
                        ('FreeableMemory', 'Bytes'),
                        ('DatabaseConnections', 'Count'),
                        ('ReadIOPS', 'Count/Second'),
                        ('WriteIOPS', 'Count/Second')
                    ]
                },
                'Lambda': {
                    'namespace': 'AWS/Lambda',
                    'dimension_name': 'FunctionName',
                    'metrics': [
                        ('Invocations', 'Count'),
                        ('Duration', 'Milliseconds'),
                        ('Errors', 'Count'),
                        ('Throttles', 'Count')
                    ]
                }
            }

            if service_type in metric_configs:
                config = metric_configs[service_type]
                dimension = [{'Name': config['dimension_name'], 'Value': resource_id}]

                for metric_name, unit in config['metrics']:
                    try:
                        response = cloudwatch.get_metric_statistics(
                            Namespace=config['namespace'],
                            MetricName=metric_name,
                            Dimensions=dimension,
                            StartTime=start_time,
                            EndTime=end_time,
                            Period=period,
                            Statistics=['Average']
                        )

                        if response['Datapoints']:
                            metrics_data[metric_name] = {
                                'value': round(response['Datapoints'][-1]['Average'], 2),
                                'unit': unit
                            }
                    except Exception as e:
                        print(f"Error getting metric {metric_name}: {str(e)}")

            return metrics_data

        except Exception as e:
            print(f"Error getting CloudWatch metrics: {str(e)}")
            return {}


# 리소스 비용 조회
## AWS Cost Explorer를 사용하여 특정 리소스의 비용 정보 조회
## 최근 30일간의 비용 데이터를 가져옴 --> 이부분도 Customizing 시에 변경해주세요!
    
    def get_resource_cost(self, resource_id, service_type, region):
        """리소스별 비용 조회"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            response = self.ce.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metrics=['UnblendedCost'],
                Filter={
                    'And': [
                        {'Dimensions': {'Key': 'REGION', 'Values': [region]}},
                        {'Dimensions': {'Key': 'SERVICE', 'Values': [self.service_mapping[service_type]]}},
                    #    {'Dimensions': {'Key': 'SERVICE', 'Values': [self.service_mapping.get(service_type, service_type)]}},
                    #    {'Dimensions': {'Key': 'RESOURCE_ID', 'Values': [resource_id]}}
                    ]
                }
            )
            print("service : ", [self.service_mapping[service_type]])
            print(f"Cost Explorer response for {resource_id}: {response}", flush=True)  # 응답 출력
            
            if response['ResultsByTime']:
                return float(response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount'])
            return 0.0
            
        except Exception as e:
            print(f"Error getting resource cost: {str(e)}")
            return 0.0

    def get_jhs_cost(self, resource_id, service_type, region):
        """리소스별 비용 조회"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            tags = self.ec2.describe_tags(Filters=[{'Name': 'resource-id', 'Values': [resource_id]}])['Tags']
            name_tag = next((tag['Value'] for tag in tags if tag['Key'] == 'Name'), None)
            print(f"Tag name for resource {resource_id}: {name_tag}")
            
            response = self.ce.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metrics=['UnblendedCost'],
                Filter={
                    'And': [
                        {'Dimensions': {'Key': 'REGION', 'Values': [region]}},
                        {'Dimensions': {'Key': 'SERVICE', 'Values': [self.service_mapping[service_type]]}},
                        {'Tags': {'Key': 'Name', 'Values': [name_tag]}}
                    ]
                }
            )
            print("service : ", [self.service_mapping[service_type]])
            print(f"Cost Explorer response for {resource_id}: {response}", flush=True)  # 응답 출력
            
            if response['ResultsByTime']:
                return float(response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount'])
            return 0.0
            
        except Exception as e:
            print(f"Error getting resource cost: {str(e)}")
            return 0.0

# EC2 데이터 수집
## 모든 리전의 EC2 instance 정보를 수집
## 인스턴스 ID, Status, Type, IP주소 등의 상세 정보를 수집 --> 필요시 이부분도 원하시는대로 변경해주세요
## CloudWatch 메트릭과 비용정보도 함께 수집
    
    def collect_ec2_data(self):
        """EC2 인스턴스 데이터 수집"""
        print("Collecting EC2 data...")
        try:
            ec2_data = []
            
            for region in self.regions:
                try:
                    ec2_client = boto3.client('ec2', region_name=region)
                    response = ec2_client.describe_instances()
                    
                    for reservation in response['Reservations']:
                        for instance in reservation['Instances']:
                            try:
                                metrics = self.get_cloudwatch_metrics(
                                    instance['InstanceId'], 
                                    'EC2', 
                                    region
                                )
                                
                                cost = self.get_resource_cost(
                                    instance['InstanceId'],
                                    'EC2',
                                    region
                                )
                                
                                instance_data = {
                                    'resource_id': instance['InstanceId'],
                                    'service_type': 'EC2',
                                    'region': region,
                                    'status': instance['State']['Name'],
                                    'creation_date': instance['LaunchTime'].strftime('%Y-%m-%d %H:%M:%S'),
                                    'last_modified': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    'tags': json.dumps({tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}),
                                    'cost': cost,
                                    'details': {
                                        'instance_type': instance['InstanceType'],
                                        'private_ip': instance.get('PrivateIpAddress', ''),
                                        'public_ip': instance.get('PublicIpAddress', ''),
                                        'vpc_id': instance.get('VpcId', ''),
                                        'subnet_id': instance.get('SubnetId', ''),
                                        'metrics': metrics
                                    }
                                }
                                ec2_data.append(instance_data)
                            except Exception as e:
                                print(f"Error processing EC2 instance {instance['InstanceId']}: {str(e)}")
                                continue
                except Exception as e:
                    print(f"Error processing region {region}: {str(e)}")
                    continue
            
            return pd.DataFrame(ec2_data)
            
        except Exception as e:
            print(f"Error collecting EC2 data: {str(e)}")
            return pd.DataFrame()


# RDS 데이터 수집
## 모든 리전의 RDS 데이터베이스 인스턴스 정보 수집
## 데이터베이스 엔진, 버전, 스토리지 크기 등의 정보 수집
    
    def collect_rds_data(self):
        """RDS 인스턴스 데이터 수집"""
        print("Collecting RDS data...")
        try:
            rds_data = []
            
            for region in self.regions:
                try:
                    rds_client = boto3.client('rds', region_name=region)
                    response = rds_client.describe_db_instances()
                    
                    for instance in response['DBInstances']:
                        try:
                            metrics = self.get_cloudwatch_metrics(
                                instance['DBInstanceIdentifier'],
                                'RDS',
                                region
                            )
                            
                            cost = self.get_resource_cost(
                                instance['DBInstanceIdentifier'],
                                'RDS',
                                region
                            )
                            
                            instance_data = {
                                'resource_id': instance['DBInstanceIdentifier'],
                                'service_type': 'RDS',
                                'region': region,
                                'status': instance['DBInstanceStatus'],
                                'creation_date': instance['InstanceCreateTime'].strftime('%Y-%m-%d %H:%M:%S'),
                                'last_modified': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'tags': json.dumps({tag['Key']: tag['Value'] for tag in instance.get('TagList', [])}),
                                'cost': cost,
                                'details': {
                                    'engine': instance['Engine'],
                                    'engine_version': instance['EngineVersion'],
                                    'instance_class': instance['DBInstanceClass'],
                                    'storage': instance['AllocatedStorage'],
                                    'endpoint': instance.get('Endpoint', {}).get('Address', ''),
                                    'metrics': metrics
                                }
                            }
                            rds_data.append(instance_data)
                        except Exception as e:
                            print(f"Error processing RDS instance {instance['DBInstanceIdentifier']}: {str(e)}")
                            continue
                except Exception as e:
                    print(f"Error processing region {region}: {str(e)}")
                    continue
            
            return pd.DataFrame(rds_data)
            
        except Exception as e:
            print(f"Error collecting RDS data: {str(e)}")
            return pd.DataFrame()


# Lambda 데이터 수집
## 모든 리전의 Lambda 함수 정보를 수집
## 함수명, 런타임, 메모리 설정, 타임아웃 정보 수집
    
    def collect_lambda_data(self):
        """Lambda 함수 데이터 수집"""
        print("Collecting Lambda data...")
        try:
            lambda_data = []
            
            for region in self.regions:
                try:
                    lambda_client = boto3.client('lambda', region_name=region)
                    paginator = lambda_client.get_paginator('list_functions')
                    
                    for page in paginator.paginate():
                        for function in page['Functions']:
                            try:
                                metrics = self.get_cloudwatch_metrics(
                                    function['FunctionName'],
                                    'Lambda',
                                    region
                                )
                                
                                cost = self.get_resource_cost(
                                    function['FunctionName'],
                                    'Lambda',
                                    region
                                )
                                
                                # 태그 정보 가져오기
                                tags_response = lambda_client.list_tags(
                                    Resource=function['FunctionArn']
                                )
                                
                                # LastModified 처리
                                if isinstance(function['LastModified'], str):
                                    last_modified = function['LastModified']
                                else:
                                    try:
                                        last_modified = function['LastModified'].strftime('%Y-%m-%d %H:%M:%S')
                                    except:
                                        last_modified = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                
                                function_data = {
                                    'resource_id': function['FunctionName'],
                                    'service_type': 'Lambda',
                                    'region': region,
                                    'status': 'Active',
                                    'creation_date': last_modified,
                                    'last_modified': last_modified,
                                    'tags': json.dumps(tags_response.get('Tags', {})),
                                    'cost': cost,
                                    'details': {
                                        'runtime': function.get('Runtime', ''),
                                        'memory': function.get('MemorySize', 0),
                                        'timeout': function.get('Timeout', 0),
                                        'handler': function.get('Handler', ''),
                                        'metrics': metrics
                                    }
                                }
                                lambda_data.append(function_data)
                            except Exception as e:
                                print(f"Error processing Lambda function {function['FunctionName']}: {str(e)}")
                                continue
                except Exception as e:
                    print(f"Error processing region {region}: {str(e)}")
                    continue
            
            return pd.DataFrame(lambda_data)
            
        except Exception as e:
            print(f"Error collecting Lambda data: {str(e)}")
            return pd.DataFrame()

# S3 데이터 수집
## 모든 S3 버킷의 정보를 수집
## 버킷 이름, 생성일, 태그 등의 정보 수집
    
    def collect_s3_data(self):
        """S3 버킷 데이터 수집"""
        print("Collecting S3 data...")
        try:
            s3_data = []
            
            response = self.s3.list_buckets()
            
            for bucket in response['Buckets']:
                try:
                    # 버킷 리전 확인
                    region = self.s3.get_bucket_location(Bucket=bucket['Name'])
                    region = region['LocationConstraint'] or 'us-east-1'
                    
                    # 버킷 태그 가져오기
                    try:
                        tags_response = self.s3.get_bucket_tagging(Bucket=bucket['Name'])
                        tags = {tag['Key']: tag['Value'] for tag in tags_response['TagSet']}
                    except:
                        tags = {}
                    
                    cost = self.get_resource_cost(
                        bucket['Name'],
                        'S3',
                        region
                    )
                    
                    bucket_data = {
                        'resource_id': bucket['Name'],
                        'service_type': 'S3',
                        'region': region,
                        'status': 'Active',
                        'creation_date': bucket['CreationDate'].strftime('%Y-%m-%d %H:%M:%S'),
                        'last_modified': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'tags': json.dumps(tags),
                        'cost': cost,
                        'details': {
                            'creation_date': bucket['CreationDate'].strftime('%Y-%m-%d %H:%M:%S')
                        }
                    }
                    s3_data.append(bucket_data)
                except Exception as e:
                    print(f"Error processing bucket {bucket['Name']}: {str(e)}")
                    continue
            
            return pd.DataFrame(s3_data)
            
        except Exception as e:
            print(f"Error collecting S3 data: {str(e)}")
            return pd.DataFrame()

# 병렬로 모든 리소스 데이터 수집
    
    def collect_all_resources(self):
        """모든 리소스 데이터 수집"""
        print("Collecting all resources...")
        dfs = []
        collection_methods = [
            self.collect_ec2_data,
            self.collect_rds_data,
            self.collect_lambda_data,
            self.collect_s3_data
        ]
        
        # 병렬로 데이터 수집
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda method: method(), collection_methods))
            
        for df in results:
            if not df.empty:
                dfs.append(df)
        
        result = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
        print(f"All resources collected: {len(result)} resources")
        return result


# 비용 분석 및 예측
## 서비스별, 리전별, 일별 비용 데이터를 수집하고 분석
## 향후 비용 예측을 위한 데이터 생성
    
    def get_cost_analysis(self):
        """비용 분석 데이터 수집"""
        print("Getting cost analysis...")
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            # 서비스별 비용
            service_response = self.ce.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metrics=['UnblendedCost'],
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
            )
            
            service_costs = pd.DataFrame([
                {
                    'SERVICE': group['Keys'][0],
                    'cost': float(group['Metrics']['UnblendedCost']['Amount'])
                }
                for group in service_response['ResultsByTime'][0]['Groups']
            ])
            
            # 리전별 비용
            region_response = self.ce.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metrics=['UnblendedCost'],
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'REGION'}]
            )
            
            region_costs = pd.DataFrame([
                {
                    'REGION': group['Keys'][0],
                    'cost': float(group['Metrics']['UnblendedCost']['Amount'])
                }
                for group in region_response['ResultsByTime'][0]['Groups']
            ])
            
            # 일별 비용
            daily_response = self.ce.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['UnblendedCost'],
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
            )
            
            daily_costs = []
            for time_period in daily_response['ResultsByTime']:
                date = time_period['TimePeriod']['Start']
                for group in time_period['Groups']:
                    daily_costs.append({
                        'date': date,
                        'SERVICE': group['Keys'][0],
                        'cost': float(group['Metrics']['UnblendedCost']['Amount'])
                    })
            
            daily_costs_df = pd.DataFrame(daily_costs)
            
            return {
                'service_costs': service_costs,
                'region_costs': region_costs,
                'daily_costs': daily_costs_df
            }
            
        except Exception as e:
            print(f"Error in cost analysis: {str(e)}")
            return None


# 비용예측
## 현재 간단한 로직으로 구성하였지만 해커톤 이후 예측 모델을 개발하시거나 혹은 가지고 계신 모델이 있으시면 이부분에 embedding 하시면 편리하게 활용하실 수 있습니다.
## days 도 필요시 변경해주세요!
    
    def predict_costs(self, days=30):
        """비용 예측"""
        print("Predicting costs...")
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 서비스별 비용 데이터 수집
            response = self.ce.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['UnblendedCost'],
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
            )
            
            # 서비스별 비용 예측
            predictions = {}
            for service in self.service_mapping.keys():
                service_costs = []
                dates = []
                for time_period in response['ResultsByTime']:
                    for group in time_period['Groups']:
                        if group['Keys'][0] == self.service_mapping[service]:
                            cost = float(group['Metrics']['UnblendedCost']['Amount'])
                            if cost > 0:  # 0이 아닌 비용만 포함
                                service_costs.append(cost)
                                dates.append(pd.to_datetime(time_period['TimePeriod']['Start']))
                
                if service_costs:
                    df = pd.DataFrame({'date': dates, 'cost': service_costs})
                    df = df.set_index('date')
                    
                    # 간단한 선형 회귀로 변경
                    current_daily_avg = df['cost'].mean()
                    if len(df) > 1:
                        trend = (df['cost'].iloc[-1] - df['cost'].iloc[0]) / len(df)
                    else:
                        trend = 0
                    
                    predicted_daily_avg = current_daily_avg + trend
                    
                    predictions[service] = {
                        'current_daily_avg': current_daily_avg,
                        'predicted_daily_avg': max(0, predicted_daily_avg),  # 음수 방지
                        'trend': 'increasing' if trend > 0 else 'decreasing' if trend < 0 else 'stable',
                        'predicted_next_month': max(0, predicted_daily_avg * 30)
                    }
            
            print(f"Cost predictions generated: {predictions}")
            return predictions
            
        except Exception as e:
            print(f"Error predicting costs: {str(e)}")
            return None

# 활용을 위한 최적화 추천
## 리소스 사용 패턴을 활용해서 비용 최적화 추천사항을 생성 (향후 로직 embedding  )
## 저사용 인스턴스, 중지된 리소스 등을 식별
    
    def get_optimization_recommendations(self):
        """리소스 최적화 추천"""
        print("Getting optimization recommendations...")
        try:
            recommendations = []
            
            # EC2 인스턴스 분석
            ec2_data = self.collect_ec2_data()
            if not ec2_data.empty:
                for _, instance in ec2_data.iterrows():
                    metrics = instance['details'].get('metrics', {})
                    
                    # CPU 사용률 기반 추천
                    if 'CPUUtilization' in metrics:
                        cpu_util = metrics['CPUUtilization']['value']
                        if cpu_util < 20:
                            recommendations.append({
                                'resource_id': instance['resource_id'],
                                'tags': instance['tags'],
                                'service_type': 'EC2',
                                'recommendation_type': 'Downsizing',
                                'reason': f'Low CPU utilization ({cpu_util}%)',
                                'potential_savings': instance['cost'] * 0.5,
                                'action': 'Consider using a smaller instance type'
                            })
                    
                    # 중지된 인스턴스 확인
                    if instance['status'] == 'stopped':
                        recommendations.append({
                            'resource_id': instance['resource_id'],
                            'tags': instance['tags'],
                            'service_type': 'EC2',
                            'recommendation_type': 'Termination',
                            'reason': 'Instance is stopped',
                            'potential_savings': instance['cost'],
                            'action': 'Consider terminating if not needed'
                        })
            
            # RDS 인스턴스 분석
            rds_data = self.collect_rds_data()
            if not rds_data.empty:
                for _, instance in rds_data.iterrows():
                    metrics = instance['details'].get('metrics', {})
                    
                    # 연결 수 기반 추천
                    if 'DatabaseConnections' in metrics:
                        connections = metrics['DatabaseConnections']['value']
                        if connections < 5:
                            recommendations.append({
                                'resource_id': instance['resource_id'],
                                'service_type': 'RDS',
                                'recommendation_type': 'Downsizing',
                                'reason': f'Low number of connections ({connections})',
                                'potential_savings': instance['cost'] * 0.4,
                                'action': 'Consider using a smaller instance class'
                            })
            
            print(f"Recommendations generated: {recommendations}")
            return pd.DataFrame(recommendations)
            
        except Exception as e:
            print(f"Error generating recommendations: {str(e)}")
            return pd.DataFrame()

# 시각화 (비용)
## Plotly를 사용하여 비용 데이터를 시각화
## 파이차트, 라인 차트, 바 차트 등 생성 (취향에 맞게 나중에 재구성 해셔도 좋을 것 같습니다!)
    
    def create_cost_visualizations(self):
        """비용 시각화"""
        print("Creating cost visualizations...")
        try:
            cost_data = self.get_cost_analysis()
            if not cost_data:
                print("No cost data available")
                return None
                
            visualizations = {}
            
            # 서비스별 비용 파이 차트
            fig_pie = px.pie(
                cost_data['service_costs'],
                values='cost',
                names='SERVICE',
                title='Cost Distribution by Service'
            )
            visualizations['service_pie'] = fig_pie
            
            # 일별 비용 트렌드 라인 차트
            fig_line = px.line(
                cost_data['daily_costs'],
                x='date',
                y='cost',
                color='SERVICE',
                title='Daily Cost Trend by Service'
            )
            visualizations['daily_trend'] = fig_line
            
            # 리전별 비용 바 차트
            fig_bar = px.bar(
                cost_data['region_costs'],
                x='REGION',
                y='cost',
                title='Cost by Region'
            )
            visualizations['region_bar'] = fig_bar
            
            print(f"Visualizations created: {list(visualizations.keys())}")
            return visualizations
                
        except Exception as e:
            print(f"Error creating visualizations: {str(e)}")
            return None
