import requests
import time
import json
import os
from constants import API_KEY, ROOT_ID, BASE_URL, PAGE_SIZE, MAX_DEPTH

headers = {
    "Api-Key":    API_KEY,
    "Start-Item": ROOT_ID
}


def fetch_node(node_id):
    url    = f"{BASE_URL}/item/{node_id}"
    params = {"expand": "properties[$all]"}
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.json()


def fetch_children(parent_id, skip=0, take=PAGE_SIZE):
    print(f"⮕ paging children of {parent_id} @ skip={skip}")
    params = {
        "expand":    "properties[$all]",
        "fetch":     f"children:{parent_id}",
        "skip":      skip,
        "take":      take
    }
    r = requests.get(BASE_URL, headers=headers, params=params)
    time.sleep(0.5)
    r.raise_for_status()
    return r.json().get("items", [])


def fetch_flat_descendants(parent_id, skip=0, take=PAGE_SIZE):
    print(f"⮕ flat descendants of {parent_id} @ skip={skip}")
    params = {
        "expand":    "properties[$all]",
        "fetch":     f"descendants:{parent_id}",
        "skip":      skip,
        "take":      take
    }
    r = requests.get(BASE_URL, headers=headers, params=params)
    time.sleep(0.5)
    r.raise_for_status()
    return r.json().get("items", [])


def fetch_all_descendants(root_id):
    all_items = []
    # queue holds (node_id, depth)
    queue = [(root_id, 0)]

    while queue:
        current, depth = queue.pop(0)
        # 1) fetch the node itself
        node = fetch_node(current)
        all_items.append(node)

        if depth < MAX_DEPTH:
            # 2) page through its immediate children, enqueue for next level
            skip = 0
            while True:
                children = fetch_children(current, skip=skip)
                if not children:
                    break
                all_items.extend(children)
                queue.extend((c["id"], depth+1) for c in children)
                skip += len(children)
                if len(children) < PAGE_SIZE:
                    break
        else:
            # 3) at max depth: fetch ALL descendants flat (<=10k)
            skip = 0
            while True:
                desc = fetch_flat_descendants(current, skip=skip)
                if not desc:
                    break
                all_items.extend(desc)
                skip += len(desc)
                if len(desc) < PAGE_SIZE:
                    break

        print(f"Fetched total so far: {len(all_items)}")
    return all_items


def remove_duplicates(list_of_items):
    print(f"Removing duplicates from {len(list_of_items)} items...")
    unique_items = []
    seen_ids = set()

    for item in list_of_items:
        item_id = item.get("id")
        if item_id is not None and item_id not in seen_ids:
            unique_items.append(item)
            seen_ids.add(item_id)
    print(f"Count after removing duplicates: {len(unique_items)}")
    return unique_items


def save_to_file(data, output_file="raw_data/umbraco-export.v1.jsonl"):
    print(f"Saving {len(data)} items to '{output_file}'...")
    total_items_written = 0
    try:
        output_dir = os.path.dirname(output_file)
        if output_dir: # Check if output_dir is not empty (i.e., not just a filename)
            os.makedirs(output_dir, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in data:
                json_string = json.dumps(item, ensure_ascii=False)
                f.write(json_string + '\n')
                total_items_written += 1
        print(f"✅ Successfully saved {total_items_written} items to '{output_file}'")
    except Exception as e:
        print(f"❌ Error writing to file: {e}")


if __name__ == "__main__":
    descendants = fetch_all_descendants(ROOT_ID)
    print(f"✅ Total nodes fetched: {len(descendants)}")
    descendants_no_duplicates = remove_duplicates(descendants)
    save_to_file(descendants_no_duplicates)
    print("✅ Finished processing all nodes.")