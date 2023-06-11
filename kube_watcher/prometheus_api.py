"""Find out prometheus server on kube-control-plane:

kubectl get svc

"""
import logging

from prometheus_api_client import PrometheusConnect, MetricSnapshotDataFrame, MetricRangeDataFrame
from prometheus_api_client.utils import parse_datetime
from datetime import timedelta


logger = logging.getLogger("prometheus_api")
logger.setLevel(logging.DEBUG)


class PrometheusAPI():
    def __init__(self, url, **kwargs):
      self.prom = PrometheusConnect(url=url, **kwargs)

    def query(self, query):
        return self.prom.custom_query(query=query)


if __name__ == "__main__":
    # This is only accessible from within the cluster!
    client = PrometheusAPI(url="http://10.43.200.148:9090", disable_ssl=True)
    logger.info("connected")

    result = client.query("""sum by (node) (kube_node_status_condition{condition="Ready", status="true"})[1h:]""")
    print(result)

    start_time = parse_datetime("1h")
    end_time = parse_datetime("now")
    chunk_size = timedelta(minutes=1)
    result = client.prom.get_metric_range_data(
        metric_name='kube_node_status_condition{condition="Ready", status="true"}',
        start_time=start_time,
        end_time=end_time,
        chunk_size=chunk_size
    )

    metric_df = MetricRangeDataFrame(result)
    metric_df.to_csv("_test.csv")
    print(metric_df.head())