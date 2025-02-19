import pytest
from aws_services import AWSResourceCollector

# Dummy Cost Explorer to simulate boto3 response behavior
class DummyCostExplorer:
    def __init__(self, response=None, raise_exception=False):
        self.response = response
        self.raise_exception = raise_exception

    def get_cost_and_usage(self, **kwargs):
        if self.raise_exception:
            raise Exception("Simulated exception")
        return self.response

@pytest.fixture
def collector():
    coll = AWSResourceCollector()
    return coll

# def test_get_resource_cost_success(collector):
#     # Simulate a successful response
#     response = {
#         "ResultsByTime": [
#             {
#                 "Total": {
#                     "UnblendedCost": {"Amount": "123.45"}
#                 }
#             }
#         ]
#     }
#     collector.ce = DummyCostExplorer(response=response)
#     cost = collector.get_resource_cost("i-1234567890abcdef0", "EC2", "us-east-1")
#     #print("success cost: ", cost, flush=True)
#     assert cost == 123.45

# def test_get_resource_cost_no_results(collector):
#     # Simulate response with no cost data
#     response = { "ResultsByTime": [] }
#     collector.ce = DummyCostExplorer(response=response)
#     cost = collector.get_resource_cost("i-1234567890abcdef0", "EC2", "us-east-1")
#     #print(" no cost: ", cost, flush=True)
#     assert cost == 0.0

# def test_get_resource_cost_exception(collector):
#     # Simulate an exception in the Cost Explorer call
#     collector.ce = DummyCostExplorer(raise_exception=True)
#     cost = collector.get_resource_cost("i-1234567890abcdef0", "EC2", "us-east-1")
#     #print("exception cost: ", cost,  flush=True)
#     assert cost == 0.0

def test_get_resource_cost_integration_ec2(collector):
    # 실제 AWS에 호출하여 실제 cost 값을 반환하는 통합 테스트
    instance_id = "i-00b6987ae47b25462"#"i-0090d4c6d48cbb703" #i-00b6987ae47b25462 #i-017311bb1a7813c08
    service = "EC2"
    region = "us-east-1"
    cost = collector.get_jhs_cost(instance_id, service, region)
    print("integration cost: ", cost, flush=True)
    # cost가 숫자인지 확인
    assert isinstance(cost, float)
    
# def test_get_resource_cost_integration_rds(collector):
#     # 실제 AWS에 호출하여 실제 cost 값을 반환하는 통합 테스트
#     instance_id = "bedrockchatstack-vectorstoreclusterwriter113530f5-qfyfv73ciugt"#"i-0090d4c6d48cbb703" #i-00b6987ae47b25462 #i-017311bb1a7813c08
#     service = "RDS"
#     region = "us-east-1"
#     cost = collector.get_resource_cost(instance_id, service, region)
#     print("integration cost: ", cost, flush=True)
#     # cost가 숫자인지 확인
#     assert isinstance(cost, float)