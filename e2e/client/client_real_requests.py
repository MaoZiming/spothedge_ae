import argparse
import asyncio
import json
import os
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

import aiohttp
import numpy as np
from policies.workloads import arena_workload

payload: Optional[Dict[str, Any]] = {
    "model": "meta-llama/Llama-2-70b-chat-hf",
    "messages": [
        {
            "role": "system",
            "content": "You are a helpful assistant.",
        },
        {
            "role": "user",
            "content": "Tell me a real real long story",
        },
    ],
    "max_tokens": 512,
    "temperature": 0,
}


def get_dir(args: argparse.Namespace):
    return f"workdir/client_result/{args.group}/{args.desc}"


async def send_request(
    api_url: str,
    index: int,
    timeout: int,
    latency_distribution: List[float] = None,
    conversation: List[Dict[str, str]] = None,
) -> None:
    print(f"Sending request {index}...")

    request_start_time = time.perf_counter()
    start_timestamp = time.time()

    new_payload = payload.copy()
    is_failed = True
    if conversation is not None and payload is not None:
        new_payload["messages"] = conversation

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=5 * 60)
    ) as session:
        method = session.get if new_payload is None else session.post
        kwargs = {} if new_payload is None else {"json": new_payload}

        kwargs["timeout"] = timeout
        print(f"request {index}: {new_payload}")
        output_length = None
        try:
            async with method(api_url, **kwargs) as response:
                if response.status == 200:
                    resp = await response.json()
                    output_length = resp["usage"]["completion_tokens"]
                    print(f"request {index}", "completion_tokens", output_length, resp)
                    is_failed = False
                else:
                    print(f"Failed request {index}: {response.status}")
                    is_failed = await response.text()
                    print(f"Details: {is_failed}")
        except asyncio.TimeoutError:
            print("Timeout occurred while making the HTTP request")
        except Exception as e:
            is_failed = f"[{type(e)}]: {e}"
            print("Unexpected error occurred while making the HTTP request:", is_failed)
    request_end_time = time.perf_counter()

    request_latency = request_end_time - request_start_time
    latency_distribution[index] = request_latency
    print(f"Request {index} finished. Latency: {request_latency:.2f} s")

    with open(f"{get_dir(args)}/latencies.jsonl", "a") as f:
        data = {
            "index": index,
            "start_time": start_timestamp,
            "latency": request_latency,
            "is_failed": is_failed,
            "output_length": output_length,
        }
        f.write(json.dumps(data) + "\n")


async def get_request(
    max_request_num: int,
    workload: arena_workload.ArenaWorkload,
) -> AsyncGenerator[int, None]:
    for i in range(max_request_num):
        interval, conversation = workload.get_next_interval_and_conversation()
        yield i, conversation
        if i != max_request_num - 1:
            await asyncio.sleep(interval)


async def benchmark(
    api_url: str,
    workload: arena_workload.ArenaWorkload,
    max_request_num: int,
    latency_distribution: Optional[List[float]] = None,
) -> None:
    tasks: List[asyncio.Task] = []

    async for i, conversation in get_request(max_request_num, workload):
        task = asyncio.create_task(
            send_request(
                api_url, i, workload.timeout, latency_distribution, conversation
            )
        )
        tasks.append(task)
    await asyncio.gather(*tasks)


def main(args: argparse.Namespace):
    print(args)

    max_request_num = args.max_request_num

    print("Loading arena dataset...")
    workload = arena_workload.ArenaWorkload(use_simulator=False, seed=args.seed, arena_trace_scale=args.arena_trace_scale)
    print("Done.")

    if args.run_time is not None:
        max_request_num = workload.calculate_max_request_num(args.run_time)
        print(f"Max request num for runtime {args.run_time}: " f"{max_request_num}")

    print(f"Max request num: {max_request_num}")
    latency_distribution = [-1 for _ in range(max_request_num)]

    path = "chat/completions" if payload is not None else "models"
    api_url = f"http://{args.host}:{args.port}/v1/{path}"

    result_dict = {
        "metadata": {
            "max_request_num": max_request_num,
            "seed": args.seed,
            "arena_trace_scale": workload.trace_scale,
        },
    }
    os.makedirs(get_dir(args), exist_ok=True)
    with open(f"{get_dir(args)}/latencies.jsonl", "w") as f:
        # clear the file
        pass
    with open(f"{get_dir(args)}/final.json", "w") as f:
        json.dump(result_dict, f, indent=4)

    benchmark_start_time = time.perf_counter()
    asyncio.run(
        benchmark(
            api_url=api_url,
            max_request_num=max_request_num,
            latency_distribution=latency_distribution,
            workload=workload,
        )
    )
    benchmark_end_time = time.perf_counter()

    benchmark_time = benchmark_end_time - benchmark_start_time
    throughput = max_request_num / benchmark_time
    mean_latency = np.mean(latency_distribution)
    p50_latency = np.percentile(latency_distribution, 50)
    p90_latency = np.percentile(latency_distribution, 90)
    p99_latency = np.percentile(latency_distribution, 99)
    p999_latency = np.percentile(latency_distribution, 99.9)
    print(f"Total requests: {max_request_num}")
    print(f"Total time: {benchmark_time:.2f} s")
    print(f"Throughput: {throughput:.2f} requests/s")
    print(f"Mean latency: {mean_latency:.2f} s")
    print(f"p50 latency: {p50_latency:.2f} s")
    print(f"p90 latency: {p90_latency:.2f} s")
    print(f"p99 latency: {p99_latency:.2f} s")
    print(f"p999 latency: {p999_latency:.2f} s")
    result_dict.update(
        {
            "analysis": {
                "benchmark_time": benchmark_time,
                "throughput": throughput,
                "mean_latency": mean_latency,
                "p50_latency": p50_latency,
                "p90_latency": p90_latency,
                "p99_latency": p99_latency,
                "p999_latency": p999_latency,
            },
            "latency_distribution": latency_distribution,
        }
    )
    with open(f"{get_dir(args)}/final.json", "w") as f:
        json.dump(result_dict, f, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Benchmark the online serving throughput."
    )
    parser.add_argument("--desc", type=str, required=True)
    parser.add_argument("--host", type=str, required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--group", type=str, required=True)
    parser.add_argument("--max-request-num", type=int, default=10)
    parser.add_argument("--arena-trace-scale", type=int, default=None)
    parser.add_argument("--request-rate", type=float, default=None)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--run-time", type=float, default=None)
    args = parser.parse_args()

    main(args)
