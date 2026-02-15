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
      self.prom = PrometheusConnect(url=url, headers={"X-Scope-OrgID": "anonymous"}, **kwargs)

    def query(self, query):

        return self.prom.custom_query(query=query)

    def get_nodes_stats(self, node_ids, start_time, end_time, resources=["amd_com_gpu", "nvidia_com_gpu"], step="1h", phase="Running", aggregate_node_results=False):
        """
        Retrieves both node status (Ready condition) and aggregated resource requests 
        for a list of nodes and custom resources over a time range.

        :param node_ids: List of node names to query status for.
        :param resources: List of custom resource names (e.g., 'amd_com_gpu') to query requests for.
        :param start_time: Start of the query time range (e.g., '2025-11-01T00:00:00Z').
        :param end_time: End of the query time range.
        :param step: Step size for the range query (e.g., '1h', '5m').
        :param aggregate_node_results: If True, aggregates the node status result into a single sum.
        :return: Dictionary containing the merged time series data, or an error dict.
        """
        try:
            # 1. Prepare time and query arguments
            start_time_dt = parse_datetime(start_time)
            end_time_dt = parse_datetime(end_time)

            # --- 2. Node Status Query ---
            node_str = "|".join(node_ids)
            node_status_query = f"""
            avg_over_time(
                kube_node_status_condition{{condition="Ready", status="true", node=~"{node_str}"}}
                [{step}]
            )
            """
            if aggregate_node_results:
                node_status_query = f"sum({node_status_query})"
                
            # Execute Node Status Query
            node_metric = self.prom.custom_query_range(
                query=node_status_query,
                start_time=start_time_dt,
                end_time=end_time_dt,
                step=step
            )
            if len(node_metric) == 0:
                return {"error": "No nodes matched"}
            
            # Convert to DataFrame
            node_df = MetricRangeDataFrame(node_metric).reset_index()

            # --- 3. Resource Utilization Query ---
            resources_str = "|".join(resources)
            # Note: I've added phase="Running" to the kube_pod_status_phase selector 
            # as it's common to only look at resources requested by running pods. 
            # You may adjust this phase if needed (e.g., to "").
            resource_query = f"""
            sum(
                max by (namespace, pod) (
                    kube_pod_container_resource_requests{{resource=~"{resources_str}", node=~"{node_str}"}}
                )
                * on(namespace, pod) group_left()
                (kube_pod_status_phase{{phase="{phase}"}} == 1)
            )
            """

            # Execute Resource Utilization Query
            resource_metric = self.prom.custom_query_range(
                query=resource_query,
                start_time=start_time_dt,
                end_time=end_time_dt,
                step=step
            )

            if len(resource_metric) == 0:
                return {"error": "No resources matched"}
            
            # Convert to DataFrame
            # The result of this query is a single time series (since it's a sum over all series)
            resource_df = MetricRangeDataFrame(resource_metric).reset_index()

            # --- 4. Merge DataFrames ---
            # Both DataFrames share the 'index' (which is the timestamp).
            # We merge them to align the time series data.
            # This assumes your 'step' and 'time range' are identical for both queries, which they are.
            
            # Step 1: Clean up column names for the merge
            # Node Status DF columns: ['__name__', 'node', 'instance', 'job', 'timestamp', 'value']
            # Resource DF columns: ['__name__', 'instance', 'job', 'timestamp', 'value']
            
            # Rename the 'value' column to be descriptive before merging
            node_df = node_df.rename(columns={'value': 'node_status_ready'})
            resource_df = resource_df.rename(columns={'value': 'total_resource_requests'})

            # The 'node_df' has multiple rows per timestamp (one per node/metric label),
            # while 'resource_df' has only one row per timestamp (the total sum).
            # We perform a left merge on the 'node_df' to include the single-row resource data.
            
            # Select key columns before the merge for simplicity
            # We use a melt-like approach for the final output, so a time-based merge is key.
            
            # Get common timestamp column
            timestamp_col = 'timestamp'

            
            # Get only the relevant columns for merging
            # Note: If 'aggregate_node_results' is True, 'node' column won't exist in node_df.
            if aggregate_node_results:
                node_value_cols = [timestamp_col, 'node_status_ready']
            else:
                # We keep 'node' to differentiate the status of each node
                node_value_cols = [timestamp_col, 'node', 'node_status_ready'] 

            # Merge on the shared 'timestamp' column
            merged_df = node_df[node_value_cols].merge(
                resource_df[[timestamp_col, 'total_resource_requests']],
                on=timestamp_col,
                how='left'
            )
            merged_df = merged_df.fillna(value=0)

            # Convert the final merged DataFrame to a dictionary
            return merged_df.to_dict(orient="list")

        except Exception as e:
            # A more descriptive error message
            return {"error": f"Error when querying Prometheus for metrics. Details: {str(e)}"}
    
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
            metric_df = metric_df.fillna(value=0)
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
        node_ids=None,
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
            node_ids: list[str] of node names to include
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
            if node_ids:
                nodes_str = "|".join(node_ids)
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
    PROMETHEUS = "http://localhost:32298"
    # import requests
    # response = requests.get(
    #     f"{PROMETHEUS}/api/v1/query",
    #     params={'query': 'up'},
    #     headers={'X-Scope-OrgID': 'anonymous'}
    # ).json()
    # print(response)
    # exit()

    client = PrometheusAPI(url=PROMETHEUS, disable_ssl=True) # works as long as we are port forwarding from control plane
    
    logger.info("connected")

    result = client.get_nodes_stats(
        node_ids=['pop-os-482bc5e0'],
        resources=["cpu"],
        start_time="4h",
        end_time="now",
        step="10m",
        aggregate_node_results=False
    )
    # result = client.get_cumulative_compute_usage(
    #     node_ids=["cogenai-worker-scw-l40s-2-a7638c30"],
    #     resources=["amd_com_gpu", "nvidia_com_gpu"],
    #     start_time="1h",
    #     end_time="now",
    #     step_seconds=60
    # )
    print(result)
    
