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
import time
import logging
from collections import defaultdict
from dateutil.parser import parse as parse_datetime
import math

from prometheus_api_client import PrometheusConnect, MetricRangeDataFrame
from prometheus_api_client.utils import parse_datetime
import pandas as pd


logger = logging.getLogger("prometheus_api")
logging.basicConfig(level=logging.INFO)


def safe_prometheus_to_df(result):
    # Prometheus API returns [] if no data matches
    if not result:
        # Return an empty DF with the columns your downstream 
        # code expects so it doesn't crash on .reset_index()
        return pd.DataFrame(columns=['timestamp', 'value', 'node', 'resource', 'namespace', 'pod'])
    
    # If using prometheus-pandas specifically:
    return MetricRangeDataFrame(result).reset_index()


class PrometheusAPI():
    def __init__(self, url, **kwargs):
      self.url = url
      self.prom = PrometheusConnect(url=url, headers={"X-Scope-OrgID": "anonymous"}, **kwargs)

    def query(self, query):
        return self.prom.custom_query(query=query)

    def get_nodes_stats(
        self,
        node_ids,
        start_time,
        end_time,
        resources=["amd_com_gpu", "nvidia_com_gpu"],
        step="1h",
        phase="Running",
        aggregate_node_results=False
    ):
        """
        Retrieves both node status (Ready condition) and comprehensive resource metrics 
        for a list of nodes and custom resources over a time range.

        :param node_ids: List of node names to query status for.
        :param resources: List of custom resource names (e.g., 'amd_com_gpu') to query requests for.
        :param start_time: Start of the query time range (e.g., '2025-11-01T00:00:00Z').
        :param end_time: End of the query time range.
        :param step: Step size for the range query (e.g., '1h', '5m').
        :param aggregate_node_results: If True, aggregates the node status result into a single sum.
        :return: Dictionary containing the merged time series data with fields:
                 - node_status_ready: Node readiness status over time
                 - total_resources: Total allocatable resources in the cluster
                 - used_resources: Resources currently used by running pods
                 - unused_resources: Available resources not currently used
                 or an error dict.
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
            t = time.time()
            node_metric = self.prom.custom_query_range(
                query=node_status_query,
                start_time=start_time_dt,
                end_time=end_time_dt,
                step=step
            )
            logger.debug(f"Node status query: {node_status_query}")
            logger.info(f"Node status query took {time.time() - t} seconds")
            # Convert to DataFrame
            node_df = safe_prometheus_to_df(node_metric)

            # --- 3. Resource Capacity and Utilization Queries ---
            resources_str = "|".join(resources)
            
            # 3a. Total resource capacity (what the cluster has)
            capacity_query = f"""
            sum(
                kube_node_status_allocatable{{resource=~"{resources_str}", node=~"{node_str}"}}
            )
            """

            # Execute Resource Capacity Query
            t = time.time()
            capacity_metric = self.prom.custom_query_range(
                query=capacity_query,
                start_time=start_time_dt,
                end_time=end_time_dt,
                step=step
            )
            logger.debug(f"Capacity query: {capacity_query}")
            logger.info(f"Capacity query took {time.time() - t} seconds")
            capacity_df = safe_prometheus_to_df(capacity_metric)

            # Execute Resource Used Query
            # 3b. Used resources (what's currently requested by running pods)
            # Note: I've added phase="Running" to the kube_pod_status_phase selector 
            # as it's common to only look at resources requested by running pods. 
            # You may adjust this phase if needed (e.g., to "").
            used_query = f"""
            sum(
                max by (namespace, pod) (
                    kube_pod_container_resource_requests{{resource=~"{resources_str}", node=~"{node_str}"}}
                )
                * on(namespace, pod) group_left()
                (kube_pod_status_phase{{phase="{phase}"}} == 1)
            )
            """
            t = time.time()
            used_metric = self.prom.custom_query_range(
                query=used_query,
                start_time=start_time_dt,
                end_time=end_time_dt,
                step=step
            )
            logger.debug(f"Used query: {used_query}")
            logger.info(f"Used query took {time.time() - t} seconds")
            used_df = safe_prometheus_to_df(used_metric)

            # --- 4. Merge DataFrames ---
            # All DataFrames share the 'index' (which is the timestamp).
            # We merge them to align the time series data.
            # This assumes your 'step' and 'time range' are identical for all queries, which they are.
            
            # Step 1: Clean up column names for the merge
            # Node Status DF columns: ['__name__', 'node', 'instance', 'job', 'timestamp', 'value']
            # Resource DF columns: ['__name__', 'instance', 'job', 'timestamp', 'value']
            
            # Rename the 'value' column to be descriptive before merging
            node_df = node_df.rename(columns={'value': 'node_status_ready'})
            capacity_df = capacity_df.rename(columns={'value': 'total_resources'})
            used_df = used_df.rename(columns={'value': 'used_resources'})

            # The 'node_df' has multiple rows per timestamp (one per node/metric label),
            # while the resource DataFrames have only one row per timestamp (the total sum).
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

            # Merge all dataframes on the shared 'timestamp' column
            merged_df = node_df[node_value_cols].merge(
                capacity_df[[timestamp_col, 'total_resources']],
                on=timestamp_col,
                how='left'
            ).merge(
                used_df[[timestamp_col, 'used_resources']],
                on=timestamp_col,
                how='left'
            )
            
            # Calculate unused resources
            #merged_df['unused_resources'] = merged_df['total_resources'] - merged_df['used_resources']
            
            # Fill NaN values with 0
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

            metric_df = safe_prometheus_to_df(metric)
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
            t = time.time()
            logger.debug(f"Node filter Query: {query}")
            metric = self.prom.custom_query_range(
                query=query,
                start_time=start_time,
                end_time=end_time,
                step=f"{step_seconds}s",
            )
            logger.info(f"Node filter Query took {time.time() - t} seconds")
            
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
    PROMETHEUS = "http://51.159.177.196:9090"
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
        node_ids=[
            "kalavai-frsbg01-aware-bluegill-2ba2c072",
            "kalavai-frsbg01-blessed-gar-d92348fe",
            "kalavai-frsbg01-dashing-collie-0d0184ae",
            "kalavai-frsbg01-destined-kit-b6638d61", 
            "kalavai-frsbg01-diverse-lacewing-a7e1c610",
            "kalavai-frsbg01-dominant-pangolin-2f4cb88e",
            "kalavai-frsbg01-endless-aphid-b8b93325", 
            "kalavai-frsbg01-endless-mustang-eab4b5b",
            "kalavai-frsbg01-growing-oriole-d70c5758",
            "kalavai-frsbg01-improved-kingfish-cf789ecb",
            "kalavai-frsbg01-loving-magpie-40096628",
            "kalavai-frsbg01-polite-tetra-403f00bc",
            "kalavai-frsbg01-positive-man-5a3ade83",
            "kalavai-frsbg01-possible-stallion-d68a8954",
            "kalavai-frsbg01-refined-badger-ceaf7f58",
            "kalavai-frsbg01-right-weasel-6ab3f965",
            "kalavai-frsbg01-saved-sloth-1d73c6b0",
            "kalavai-frsbg01-stable-oriole-24455ec0",
            "kalavai-frsbg01-teaching-tetra-dd1ffb81",
            "kalavai-frsbg01-united-feline-0fc9f66a"
        ],
        resources=["nvidia_com_gpu", "amd_com_gpu"],
        start_time="24h",
        end_time="now",
        step="1h",
        aggregate_node_results=False
    )
    # result = client.get_cumulative_compute_usage(
    #     node_ids=[
    #         "kalavai-frsbg01-aware-bluegill-2ba2c072",
    #         "kalavai-frsbg01-blessed-gar-d92348fe",
    #         "kalavai-frsbg01-dashing-collie-0d0184ae",
    #         "kalavai-frsbg01-destined-kit-b6638d61", 
    #         "kalavai-frsbg01-diverse-lacewing-a7e1c610",
    #         "kalavai-frsbg01-dominant-pangolin-2f4cb88e",
    #         "kalavai-frsbg01-endless-aphid-b8b93325", 
    #         "kalavai-frsbg01-endless-mustang-eab4b5b",
    #         "kalavai-frsbg01-growing-oriole-d70c5758",
    #         "kalavai-frsbg01-improved-kingfish-cf789ecb",
    #         "kalavai-frsbg01-loving-magpie-40096628",
    #         "kalavai-frsbg01-polite-tetra-403f00bc",
    #         "kalavai-frsbg01-positive-man-5a3ade83",
    #         "kalavai-frsbg01-possible-stallion-d68a8954",
    #         "kalavai-frsbg01-refined-badger-ceaf7f58",
    #         "kalavai-frsbg01-right-weasel-6ab3f965",
    #         "kalavai-frsbg01-saved-sloth-1d73c6b0",
    #         "kalavai-frsbg01-stable-oriole-24455ec0",
    #         "kalavai-frsbg01-teaching-tetra-dd1ffb81",
    #         "kalavai-frsbg01-united-feline-0fc9f66a"
    #     ],
    #     resources=["amd_com_gpu", "nvidia_com_gpu"],
    #     start_time="4h",
    #     end_time="now",
    #     step_seconds=10
    # )
    #print(result)
    
