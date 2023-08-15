"""Find out prometheus server on kube-control-plane:

kubectl get svc

"""
import logging

import plotly.express as px
from prometheus_api_client import PrometheusConnect, MetricRangeDataFrame
from prometheus_api_client.utils import parse_datetime
from datetime import timedelta


logger = logging.getLogger("prometheus_api")
logging.basicConfig(level=logging.INFO)


class PrometheusAPI():
    def __init__(self, url, **kwargs):
      self.prom = PrometheusConnect(url=url, **kwargs)

    def query(self, query):
        return self.prom.custom_query(query=query)


if __name__ == "__main__":
    client = PrometheusAPI(url="http://localhost:9090", disable_ssl=True) # works as long as we are port forwarding from control plane
    # how to make a cluster IP available?? https://kubernetes.io/docs/tasks/access-application-cluster/access-cluster-services/#manually-constructing-apiserver-proxy-urls
    # clusterIP is accessible from pods in a cluster, not from the node. Should be available through our kalavai-connect
    #client = PrometheusAPI(url="http://10.8.0.1/api/v1/namespaces/default/services/prometheus-kube-prometheus-prometheus:9090/proxy", disable_ssl=True)
    
    logger.info("connected")

    result = client.query("""sum (scrape_samples_scraped) by (_ARMS_AGENT_ID)[1h:]""")
    print(result)

    start_time = parse_datetime("1h")
    end_time = parse_datetime("now")
    chunk_size = timedelta(minutes=1)
    metric = client.prom.get_metric_range_data(
        metric_name='kube_node_status_condition{condition="Ready", status="true", node="carlos-g5-md"}',
        start_time=start_time,
        end_time=end_time,
        chunk_size=chunk_size
    )
    metric_df = MetricRangeDataFrame(metric).reset_index()
    metric_df.to_csv("_test.csv")
    fig = px.bar(
        metric_df,
        x="timestamp",
        y="value",
        title='Cluster Nodes up time',
        color="node"
    )
    fig.show()
    
    