import json
import requests
import datetime
import yaml

URL = "http://localhost:8000" # "https://kube.cogenai.kalavai.net"
API_KEY = "cb5bc93a-6bd4-4f03-b195-bd79bb6833fd"
USER_SPACE = "default"


def test_stream_logs(labels, namespace=None, tail_lines=20, follow=True, max_events=50, timeout=120):
    """Call POST /v1/stream_logs_for_label and print SSE events as they arrive."""
    payload = {
        "labels": labels,
        "tail_lines": tail_lines,
        "follow": follow,
    }
    if namespace is not None:
        payload["force_namespace"] = namespace
    print(f"POST {URL}/v1/stream_logs_for_label payload={json.dumps(payload)}")
    with requests.post(
        f"{URL}/v1/stream_logs_for_label",
        headers={"X-API-KEY": API_KEY, "USER": "carlosfm"},
        json=payload,
        stream=True,
        timeout=timeout,
    ) as response:
        print(f"status: {response.status_code} content-type: {response.headers.get('content-type')}")
        if response.status_code != 200:
            print(response.text)
            return
        seen = 0
        buffer = ""
        for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
            if not chunk:
                continue
            buffer += chunk
            # SSE events are delimited by blank line
            while "\n\n" in buffer:
                raw_event, buffer = buffer.split("\n\n", 1)
                lines = [l for l in raw_event.splitlines() if l.startswith("data:")]
                if not lines:
                    continue
                data = "\n".join(l[len("data:"):].strip() for l in lines)
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    print(f"<non-json event> {data!r}")
                    continue
                seen += 1
                pod = event.get("pod", "?")
                seq = event.get("seq", "?")
                if "log" in event:
                    print(f"[{seen}][{pod}#{seq}] {event['log']}")
                else:
                    print(f"[{seen}][{pod}] {json.dumps(event)}")
                if max_events is not None and seen >= max_events:
                    print(f"Reached max_events={max_events}, closing stream.")
                    return


if __name__ == "__main__":

    # --- streaming logs test (new endpoint) ---
    test_stream_logs(
        labels={"kalavai.job.name": "2fb3394b-a934-495b-9f63-15cf25c9bc9c"},
        namespace=USER_SPACE,
        tail_lines=20,
        follow=True,   # set True to keep following live logs
        max_events=50,
    )

    