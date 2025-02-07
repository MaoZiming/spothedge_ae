import json
import os
from typing import Optional
import datasets

_ARENA_DATASET_CACHE_FILE = "workloads/arena/arena_dataset_cache.json"
_ARENA_TRACE_SCALE = 20


def load_arena_dataset(arena_trace_scale: Optional[float] = _ARENA_TRACE_SCALE):
    if os.path.exists(_ARENA_DATASET_CACHE_FILE):
        with open(_ARENA_DATASET_CACHE_FILE, "r") as f:
            cached_data = json.load(f)
            original_intervals = cached_data["original_intervals"]
            if arena_trace_scale is not None:
                intervals = [
                    interval / arena_trace_scale for interval in original_intervals
                ]
            else:
                intervals = original_intervals
            conversations = cached_data["conversations"]
            return intervals, conversations

    ds = datasets.load_dataset("lmsys/chatbot_arena_conversations")
    train_ds = ds["train"]
    timestamps = []
    conversations = []
    for data in train_ds:
        timestamps.append(data["tstamp"])
        filtered_conversation = []
        # conversation = data['conversation_a']
        next_role = "user"
        for conversation in data["conversation_a"]:
            # Conversation roles must alternate user/assistant/user/assistant...
            if conversation["role"] == next_role:
                filtered_conversation.append(conversation)
                if next_role == "user":
                    next_role = "assistant"
                else:
                    next_role = "user"
            else:
                raise ValueError(f'Invalid conversation {data["conversation_a"]}')
        if not filtered_conversation:
            raise ValueError(f'Invalid conversation {data["conversation_a"]}')
        # Pop the last assistant message if it exists to let our LLM
        # answer the last user message.
        if filtered_conversation[-1]["role"] == "assistant":
            filtered_conversation.pop(-1)
        conversations.append(filtered_conversation)

    timestamps.sort()
    original_intervals = [
        timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)
    ]
    if arena_trace_scale is not None:
        intervals = [interval / arena_trace_scale for interval in original_intervals]
    else:
        intervals = original_intervals

    # Scale intervals.
    print(intervals[:5])
    with open(_ARENA_DATASET_CACHE_FILE, "w") as f:
        json.dump(
            {
                "original_intervals": original_intervals,
                "conversations": conversations,
            },
            f,
            indent=4,
        )
    return intervals, conversations
