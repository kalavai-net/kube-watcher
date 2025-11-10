"""
Metrics documentation: https://github.com/kubernetes/kube-state-metrics/blob/main/docs/

Find out prometheus server on kube-control-plane:

kubectl get svc

PROMETHEUS QUERIES:
- Flops between ready and not ready in the last 10h: sum(changes(kube_node_status_condition{status="true",condition="Ready"}[10h])) by (node) > 2
- CPU Utilisation per node: 100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[10m]) * 100) * on(instance) group_left(nodename) (node_uname_info))
- Load per instance overtime: sum by (instance) (node_load5) / count by (instance) (node_cpu_seconds_total{mode="user"}) * 100
- List pods in a specific node: kube_pod_info{node="carlosfm-desktop-1"}

"""
import logging
from collections import defaultdict
from dateutil.parser import parse as parse_datetime
import math

from prometheus_api_client import PrometheusConnect, MetricRangeDataFrame
from prometheus_api_client.utils import parse_datetime


logger = logging.getLogger("prometheus_api")
logging.basicConfig(level=logging.INFO)


class PrometheusAPI():
    def __init__(self, url, **kwargs):
      self.prom = PrometheusConnect(url=url, **kwargs)

    def query(self, query):
        return self.prom.custom_query(query=query)
    
    def get_node_stats(self, node_ids, start_time, end_time, step="1h", aggregate_results=False):
        try:
            start_time = parse_datetime(start_time)
            end_time = parse_datetime(end_time)

            # query = f"""
            # avg_over_time(
            #     kube_node_status_condition{{condition="Ready", status="true", node="{node_id}"}}
            #     [{step}]
            # )
            # """
            node_str = "|".join(node_ids)
            query = f"""
            avg_over_time(
                kube_node_status_condition{{condition="Ready", status="true", node=~"{node_str}"}}
                [{step}]
            )
            """
            if aggregate_results:
                query = f"sum({query})"
            metric = self.prom.custom_query_range(
                query=query,
                start_time=start_time,
                end_time=end_time,
                step=step
            )

            metric_df = MetricRangeDataFrame(metric).reset_index()
            return metric_df.to_dict(orient="list")
        except Exception as e:
            return {"error": f"Error when inspecting node {node_ids}. Does it exist? {str(e)}"}

    def get_compute_stats(self, start_time, end_time, resources=["amd_com_gpu", "nvidia_com_gpu"], phase="Running", step="1h", aggregate_results=False):
        try:
            start_time = parse_datetime(start_time)
            end_time = parse_datetime(end_time)

            resources_str = "|".join(resources)
            query = f"""
            sum(
                max by (namespace, pod) (
                    kube_pod_container_resource_requests{{resource=~"{resources_str}"}}
                )
                * on(namespace, pod) group_left()
                (kube_pod_status_phase{{phase="{phase}"}} == 1)
            )
            """
            if aggregate_results:
                query = f"sum({query})"
            metric = self.prom.custom_query_range(
                query=query,
                start_time=start_time,
                end_time=end_time,
                step=step
            )

            metric_df = MetricRangeDataFrame(metric).reset_index()
            return metric_df.to_dict(orient="list")
        except Exception as e:
            return {"error": f"Error when extracting compute for resources {resources_str}. Does it exist? {str(e)}"}

    def get_cumulative_compute_usage(
        self,
        start_time,
        end_time,
        resources,
        phase="Running",
        step_seconds=300,
        normalize=False,
        namespaces=None,
        nodes=None,
    ):
        """
        Collapse a Prometheus range query into resource-hours for selected pods.

        Args:
            start_time, end_time: str|datetime
            resources: list[str] -> e.g. ["cpu","memory","amd_com_gpu","nvidia_com_gpu"]
            phase: filter by pod phase (default "Running")
            step_seconds: Prometheus query step
            normalize: if True, average over window length (hours)
            namespaces: list[str] of namespaces to include
            nodes: list[str] of node names to include
        Returns:
            dict[resource] -> hours (total) or average (per hour)
        """
        try:
            start_time = parse_datetime(start_time)
            end_time = parse_datetime(end_time)
            duration_hours = (end_time - start_time).total_seconds() / 3600.0

            # Build resource filter
            resources_str = "|".join(resources)
            filters = [f'resource=~"{resources_str}"']

            # Namespace filter
            if namespaces:
                ns_str = "|".join(namespaces)
                filters.append(f'namespace=~"{ns_str}"')

            # Base resource metric with namespace filter
            resource_selector = ",".join(filters)
            base = f'kube_pod_container_resource_requests{{{resource_selector}}}'

            # Node filtering (requires join with kube_pod_info)
            # kube_pod_info exposes pod->node mapping
            if nodes:
                nodes_str = "|".join(nodes)
                node_filter = f'node=~"{nodes_str}"'
                pod_info = f'kube_pod_info{{{node_filter}}}'
                # Join the resource requests with pod_info to limit to selected nodes
                left_expr = f'({base}) * on(namespace, pod) group_left(node) ({pod_info})'
            else:
                left_expr = base

            # Filter to only Running pods
            running = f'(kube_pod_status_phase{{phase="{phase}"}} == 1)'

            query = f"""
            max by (namespace, pod, resource) (
                {left_expr}
            )
            * on(namespace, pod) group_left()
            {running}
            """

            metric = self.prom.custom_query_range(
                query=query,
                start_time=start_time,
                end_time=end_time,
                step=f"{step_seconds}s",
            )

            resource_hours = {resource: 0.0 for resource in resources}

            for series in metric:
                resource = series["metric"].get("resource", "unknown")
                values = series["values"]
                if not values:
                    continue

                samples = [float(v) for _, v in values]
                timestamps = [float(ts) for ts, _ in values]
                if len(timestamps) > 1:
                    avg_step = (timestamps[-1] - timestamps[0]) / (len(timestamps) - 1)
                else:
                    avg_step = step_seconds

                total_seconds = sum(samples) * avg_step

                resource_hours[resource] += total_seconds / 3600.0

            # Optional normalization (to average per hour)
            if normalize and duration_hours > 0:
                for r in resource_hours:
                    resource_hours[r] /= duration_hours

            return dict(resource_hours)

        except Exception as e:
            return {
                "error": f"Error when extracting compute for resources {resources}: {str(e)}"
            }

if __name__ == "__main__":
    client = PrometheusAPI(url="http://51.159.173.70:9090", disable_ssl=True) # works as long as we are port forwarding from control plane
    
    logger.info("connected")

    result = client.get_cumulative_compute_usage(
        start_time="12h",
        end_time="now",
        step_seconds=300,
        resources=["cpu"],
        normalize=True
    )
    print(result)
    aggregate_map = {"amd_com_gpu": "gpu", "nvidia_com_gpu": "gpu", "memory": "ram"}
    aggregate = defaultdict(float)
    for resource, value in result.items():
        if resource in aggregate_map:
            key = aggregate_map[resource]
            aggregate[key] += value
        else:
            aggregate[resource] = value
    print(aggregate)
    
