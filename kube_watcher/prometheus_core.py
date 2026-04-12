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
        aggregate_node_results=False,
        namespaces=None
    ):
        """
        Retrieves both node status (Ready condition) and comprehensive resource metrics 
        for a list of nodes and custom resources over a time range.

        :param node_ids: List of node names to query status for.
        :param resources: List of custom resource names (e.g., 'amd_com_gpu') to query requests for.
        :param start_time: Start of the query time range (e.g., '2025-11-01T00:00:00Z').
        :param end_time: End of the query time range.
        :param step: Step size for the range query (e.g., '1h', '5m').
        :param phase: Pod phase to filter (default "Running").
        :param aggregate_node_results: If True, aggregates the node status result into a single sum.
        :param namespaces: List of namespaces to filter workloads by (default None for all namespaces).
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
            
            # Build namespace filter if specified
            namespace_filter = ""
            if namespaces:
                namespaces_str = "|".join(namespaces)
                namespace_filter = f',namespace=~"{namespaces_str}"'
            
            used_query = f"""
            sum(
                max by (namespace, pod) (
                    kube_pod_container_resource_requests{{resource=~"{resources_str}", node=~"{node_str}"{namespace_filter}}}
                )
                * on(namespace, pod) group_left()
                (max by (namespace, pod) (kube_pod_status_phase{{phase="{phase}"}} == 1))
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
                (max by (namespace, pod) (kube_pod_status_phase{{phase="{phase}"}} == 1))
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
        pod_labels=None,
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
            pod_labels: dict[str, str] of label key=value pairs to filter pods
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

            # Label filtering - add labels directly to resource metric
            if pod_labels:
                label_filters = []
                for key, value in pod_labels.items():
                    label_filters.append(f'{key}="{value}"')
                
                if label_filters:
                    label_selector = ",".join(label_filters)
                    filters.append(label_selector)
                    logger.debug(f"Added labels to resource filter: {label_selector}")
                    
                    # Test this approach
                    try:
                        test_filter = ",".join(filters)
                        test_query = f'kube_pod_container_resource_requests{{{test_filter}}}'
                        test_result = self.prom.custom_query(query=test_query)
                        logger.debug(f"Label filter test: {len(test_result)} results")
                        if test_result:
                            logger.debug(f"Label filtering approach successful")
                        else:
                            logger.warning(f"Label filtering returned no results, labels may not be available on resource metrics")
                    except Exception as e:
                        logger.warning(f"Label filter test failed: {e}")

            # Base resource metric with all filters applied
            resource_selector = ",".join(filters)
            base = f'kube_pod_container_resource_requests{{{resource_selector}}}'

            # Node filtering (requires join with kube_pod_info)
            # kube_pod_info exposes pod->node mapping
            if node_ids:
                nodes_str = "|".join(node_ids)
                node_filter = f'node=~"{nodes_str}"'
                # Use max() to deduplicate kube_pod_info entries for the same pod
                pod_info = f'max by (namespace, pod, node) (kube_pod_info{{{node_filter}}})'
                # Join the resource requests with pod_info to limit to selected nodes
                left_expr = f'({base}) * on(namespace, pod) group_left(node) ({pod_info})'
            else:
                left_expr = base

            # Filter to only Running pods
            # Use max() to deduplicate kube_pod_status_phase entries from multiple kube-state-metrics instances
            running = f'max by (namespace, pod) (kube_pod_status_phase{{phase="{phase}"}} == 1)'

            query = f"""
            max by (namespace, pod, resource) (
                {left_expr}
            )
            * on(namespace, pod) group_left()
            {running}
            """
            t = time.time()
            logger.debug(f"Full query: {query}")
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
    # test on server: kubectl port-forward --address 0.0.0.0 -n monitoring svc/thanos-query-frontend 9090:9090
    PROMETHEUS = "http://51.159.177.196:9090"
    client = PrometheusAPI(url=PROMETHEUS, disable_ssl=True)
    logger.info("connected")

#     # Convert time strings to datetime objects
#     start_time_dt = parse_datetime("8h")
#     end_time_dt = parse_datetime("now")

#     result = client.prom.custom_query_range(
#         query="""sum(
#   container_memory_usage_bytes{container!=""} 
#   * on(pod, namespace) 
#   group_left(label_role) 
#   kube_pod_labels{label_role="leader"}
# ) by (pod)""",
#         start_time=start_time_dt,
#         end_time=end_time_dt,
#         step="1m"
#     )
#     print(result)
#     exit()
    

    # result = client.get_nodes_stats(
    #     node_ids=[
    #         "kalavai-camtl01-0-d24a95db-6dac9105",
    #         "kalavai-camtl01-1-251518e2-defe1ded",
    #         "kalavai-camtl01-10-41fdff0c-dc1efdef",
    #         "kalavai-camtl01-11-6557449b-a5c276c9",
    #         "kalavai-camtl01-12-4c5d261a-82493df4",
    #         "kalavai-camtl01-13-9dc21be4-907516d0",
    #         "kalavai-camtl01-14-cf4eeb07-3f9c98ff",
    #         "kalavai-camtl01-15-b28a44ea-3639dbc8",
    #         "kalavai-camtl01-16-cce2c392-b080b803",
    #         "kalavai-camtl01-17-a289c09e-1c0b01c9",
    #         "kalavai-camtl01-18-65ac7277-0c6c0e0f",
    #         "kalavai-camtl01-19-e5c71e6c-bc7db06d",
    #         "kalavai-camtl01-2-03188cee-a4344d5f",
    #         "kalavai-camtl01-3-bb317fa4-fc8ea816",
    #         "kalavai-camtl01-4-4874f925-fdf7f22c",
    #         "kalavai-camtl01-5-87e07ebc-e0123c85",
    #         "kalavai-camtl01-6-f2fa4195-b9e260cd",
    #         "kalavai-camtl01-7-96da0f93-7faf6d75",
    #         "kalavai-camtl01-8-674b4211-e274d4c7",
    #         "kalavai-camtl01-9-168a13e3-e991a7f9",
    #         "kalavai-frsbg01-aware-bluegill-db4ba4d3",
    #         "kalavai-frsbg01-blessed-gar-e54b5e6d",
    #         "kalavai-frsbg01-dashing-collie-759d2ed4",
    #         "kalavai-frsbg01-destined-kit-74c620a3",
    #         "kalavai-frsbg01-diverse-lacewing-f8d1e486",
    #         "kalavai-frsbg01-dominant-pangolin-3b18aef1",
    #         "kalavai-frsbg01-endless-aphid-6e39c49f",
    #         "kalavai-frsbg01-endless-mustang-5fe96f48",
    #         "kalavai-frsbg01-growing-oriole-7db4bbd5",
    #         "kalavai-frsbg01-improved-kingfish-534cd322",
    #         "kalavai-frsbg01-loving-magpie-2887e099",
    #         "kalavai-frsbg01-polite-tetra-e8652e1f",
    #         "kalavai-frsbg01-positive-man-bcb7efb2",
    #         "kalavai-frsbg01-possible-stallion-28a969e8",
    #         "kalavai-frsbg01-refined-badger-73aa0d21",
    #         "kalavai-frsbg01-right-weasel-f961183e",
    #         "kalavai-frsbg01-saved-sloth-028b0a8d",
    #         "kalavai-frsbg01-stable-oriole-3559f020",
    #         "kalavai-frsbg01-teaching-tetra-aed113af",
    #         "kalavai-frsbg01-united-feline-4cec52e8",
    #         "kalavai-uspor01-0-e7dee8e0-3ea4c8cb",
    #         "kalavai-uspor01-1-c9ccc729-5d28baf3",
    #         "kalavai-uspor01-10-ef48ced6-aae3e4a7",
    #         "kalavai-uspor01-11-894ce924-323d02da",
    #         "kalavai-uspor01-12-91883fe3-d86f7e6e",
    #         "kalavai-uspor01-13-50d8aa5b-72592ab1",
    #         "kalavai-uspor01-14-b4cc92eb-0c4ab032",
    #         "kalavai-uspor01-15-92b1620b-5d03fda5",
    #         "kalavai-uspor01-16-5a899e7b-1b4936af",
    #         "kalavai-uspor01-17-245bc70d-cca17a04",
    #         "kalavai-uspor01-18-03d0152f-5c048f82",
    #         "kalavai-uspor01-19-5531f387-b36b8957",
    #         "kalavai-uspor01-2-a70cded6-70ac4b0b",
    #         "kalavai-uspor01-3-149a065c-5e06f7eb",
    #         "kalavai-uspor01-4-a2474c70-288ca8a8",
    #         "kalavai-uspor01-5-b993d2b6-365f2201",
    #         "kalavai-uspor01-6-807c71e4-ce9cdb9d",
    #         "kalavai-uspor01-7-2b093d4d-e81376f4",
    #         "kalavai-uspor01-8-7dd54296-4b17abb2",
    #         "kalavai-uspor01-9-d7774fe9-b776c292"

    #     ],
    #     resources=["nvidia_com_gpu", "amd_com_gpu"],
    #     start_time="7d",
    #     end_time="now",
    #     step="2h",
    #     aggregate_node_results=True,
    #     namespaces=["shadow"]
    # )
    # print(result)
    # exit()

    start_time_dt = parse_datetime("38d")
    end_time_dt = parse_datetime("7d")
    print(start_time_dt)
    print(end_time_dt)
    result = client.get_cumulative_compute_usage(
        namespaces=[
            "shadow"
        ],
        node_ids=[
            "kalavai-frsbg01-aware-bluegill-db4ba4d3",
            "kalavai-frsbg01-blessed-gar-e54b5e6d",
            "kalavai-frsbg01-dashing-collie-759d2ed4",
            "kalavai-frsbg01-destined-kit-74c620a3",
            "kalavai-frsbg01-diverse-lacewing-f8d1e486",
            "kalavai-frsbg01-dominant-pangolin-3b18aef1",
            "kalavai-frsbg01-endless-aphid-6e39c49f",
            "kalavai-frsbg01-endless-mustang-5fe96f48",
            "kalavai-frsbg01-growing-oriole-7db4bbd5",
            "kalavai-frsbg01-improved-kingfish-534cd322",
            "kalavai-frsbg01-loving-magpie-2887e099",
            "kalavai-frsbg01-polite-tetra-e8652e1f",
            "kalavai-frsbg01-positive-man-bcb7efb2",
            "kalavai-frsbg01-possible-stallion-28a969e8",
            "kalavai-frsbg01-refined-badger-73aa0d21",
            "kalavai-frsbg01-right-weasel-f961183e",
            "kalavai-frsbg01-saved-sloth-028b0a8d",
            "kalavai-frsbg01-stable-oriole-3559f020",
            "kalavai-frsbg01-teaching-tetra-aed113af",
            "kalavai-frsbg01-united-feline-4cec52e8",
            # "kalavai-camtl01-0-d24a95db-6dac9105",
            # "kalavai-camtl01-1-251518e2-defe1ded",
            # "kalavai-camtl01-10-41fdff0c-dc1efdef",
            # "kalavai-camtl01-11-6557449b-a5c276c9",
            # "kalavai-camtl01-12-4c5d261a-82493df4",
            # "kalavai-camtl01-13-9dc21be4-907516d0",
            # "kalavai-camtl01-14-cf4eeb07-3f9c98ff",
            # "kalavai-camtl01-15-b28a44ea-3639dbc8",
            # "kalavai-camtl01-16-cce2c392-b080b803",
            # "kalavai-camtl01-17-a289c09e-1c0b01c9",
            # "kalavai-camtl01-18-65ac7277-0c6c0e0f",
            # "kalavai-camtl01-19-e5c71e6c-bc7db06d",
            # "kalavai-camtl01-2-03188cee-a4344d5f",
            # "kalavai-camtl01-3-bb317fa4-fc8ea816",
            # "kalavai-camtl01-4-4874f925-fdf7f22c",
            # "kalavai-camtl01-5-87e07ebc-e0123c85",
            # "kalavai-camtl01-6-f2fa4195-b9e260cd",
            # "kalavai-camtl01-7-96da0f93-7faf6d75",
            # "kalavai-camtl01-8-674b4211-e274d4c7",
            # "kalavai-camtl01-9-168a13e3-e991a7f9",
            # "kalavai-uspor01-0-e7dee8e0-3ea4c8cb",
            # "kalavai-uspor01-1-c9ccc729-5d28baf3",
            # "kalavai-uspor01-10-ef48ced6-aae3e4a7",
            # "kalavai-uspor01-11-894ce924-323d02da",
            # "kalavai-uspor01-12-91883fe3-d86f7e6e",
            # "kalavai-uspor01-13-50d8aa5b-72592ab1",
            # "kalavai-uspor01-14-b4cc92eb-0c4ab032",
            # "kalavai-uspor01-15-92b1620b-5d03fda5",
            # "kalavai-uspor01-16-5a899e7b-1b4936af",
            # "kalavai-uspor01-17-245bc70d-cca17a04",
            # "kalavai-uspor01-18-03d0152f-5c048f82",
            # "kalavai-uspor01-19-5531f387-b36b8957",
            # "kalavai-uspor01-2-a70cded6-70ac4b0b",
            # "kalavai-uspor01-3-149a065c-5e06f7eb",
            # "kalavai-uspor01-4-a2474c70-288ca8a8",
            # "kalavai-uspor01-5-b993d2b6-365f2201",
            # "kalavai-uspor01-6-807c71e4-ce9cdb9d",
            # "kalavai-uspor01-7-2b093d4d-e81376f4",
            # "kalavai-uspor01-8-7dd54296-4b17abb2",
            # "kalavai-uspor01-9-d7774fe9-b776c292"

        ],
        resources=["nvidia_com_gpu"],
        start_time=start_time_dt,
        end_time=end_time_dt,
        step_seconds=600,  # Use 10 minute steps for longer range
        #pod_labels={"role": "leader"}  # Temporarily disable to test base query
    )
    print(result)
    
    # Example with label filtering - only count pods with specific labels
    # result_with_labels = client.get_cumulative_compute_usage(
    #     resources=["cpu", "memory"],
    #     start_time="1d",
    #     end_time="now",
    #     labels={"app": "nginx", "tier": "frontend"}  # Only pods with app=nginx AND tier=frontend
    # )
    # print("Label-filtered result:", result_with_labels)
    
