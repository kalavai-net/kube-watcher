import argparse
import json
import os
import pathlib


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str)
    parser.add_argument("--output-filename", type=str, default="config.json")
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)

    args = parser.parse_args()

    config = {
        "host": args.host,
        "port": args.port,
        "models": [{
            "model": args.model,
            "model_alias": args.model,
            #"chat_format": "chatml",
            # "n_gpu_layers": -1,
            # "n_threads": 12,
            # "n_batch": 512,
            # "n_ctx": 2048
        }]
    }
    print(json.dumps(config, indent=2))

    with open(args.output_filename, "w") as f:
        json.dump(config, f)
