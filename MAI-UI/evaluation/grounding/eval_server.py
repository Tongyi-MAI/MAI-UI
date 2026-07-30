import os
import json
import base64
import re
import threading
import argparse
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from PIL import Image
from openai import OpenAI
from qwen_vl_utils import smart_resize
from collections import defaultdict

try:
    from tqdm import tqdm
except ImportError:
    tqdm = lambda x, total=None: x

SYSTEM_PROMPT = """You are a GUI grounding agent. 
## Task
Given a screenshot and the user's grounding instruction. Your task is to accurately locate a UI element based on the user's instructions.
First, you should carefully examine the screenshot and analyze the user's instructions,  translate the user's instruction into a effective reasoning process, and then provide the final coordinate.
## Output Format
Return a json object with a reasoning process in <grounding_think></grounding_think> tags, a [x,y] format coordinate within <answer></answer> XML tags:
<grounding_think>...</grounding_think>
<answer>
{"coordinate": [x,y]}
</answer>
## Input instruction
"""

file_write_lock = threading.Lock()

def parse_coordinates(raw_string):
    matches = re.findall(r'\[(\d+),(\d+)\]', raw_string)
    matches = [tuple(map(int, match)) for match in matches]
    if len(matches) == 0:
        return -1, -1
    else:
        return matches[0]

def pil_to_base64(screenshot_path):
    try:
        image = Image.open(screenshot_path).convert('RGB')
    except FileNotFoundError:
        return None, 0, 0
    
    buffer = BytesIO()
    ori_width = image.width
    ori_height = image.height
    
    resized_height, resized_width = smart_resize(
        image.height,
        image.width,
        factor=16 * 2,
        min_pixels=16 * 16 * 4,
        max_pixels=6553600,
    )
    resized_image = image.resize((resized_width, resized_height))
    resized_image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8"), ori_width, ori_height

def process_case(case, image_root, output_file, client, model_name):
    try:
        image_path = os.path.join(image_root, case['img_filename'])
        base64_img, ori_width, ori_height = pil_to_base64(image_path)
        
        if base64_img is None:
            print(f"Image not found: {image_path}")
            return

        completion = client.chat.completions.create(
            model=model_name, 
            messages=[
                {   
                    "role": "system",
                    "content": [
                        {"type": "text", "text": SYSTEM_PROMPT}
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": case['instruction'] + "\n"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_img}"}},
                    ],
                },
            ],
            temperature=0.0,
            max_tokens=256,
        )

        response_content = completion.choices[0].message.content
        related_x, related_y = parse_coordinates(response_content)
        
        if related_x == -1 or related_y == -1:
            norm_x, norm_y = None, None
            abs_x, abs_y = None, None
        else:
            norm_x = related_x / 1000.0
            norm_y = related_y / 1000.0
            abs_x = norm_x * ori_width
            abs_y = norm_y * ori_height
        
        bbox = case['bbox']
        result = case.copy()
        result['raw_response'] = response_content
        result['pred'] = [abs_x, abs_y] if abs_x is not None else None
        result['pred_norm'] = [norm_x, norm_y] if norm_x is not None else None  
        
        if norm_x is None or norm_y is None:
            result['correctness'] = 'wrong_format'
        else:
            img_size = case.get('img_size', [ori_width, ori_height])
            if len(img_size) == 2:
                img_width, img_height = img_size[0], img_size[1]
            else:
                img_width, img_height = ori_width, ori_height
            
            bbox_norm = [
                bbox[0] / img_width,
                bbox[1] / img_height,
                bbox[2] / img_width,
                bbox[3] / img_height
            ]
            
            if (bbox_norm[0] <= norm_x <= bbox_norm[2]) and (bbox_norm[1] <= norm_y <= bbox_norm[3]):
                result['correctness'] = 'correct'
            else:
                result['correctness'] = 'incorrect'

        with file_write_lock:
            with open(output_file, 'a') as f:
                f.write(json.dumps(result, ensure_ascii=False) + '\n')
                
    except Exception as e:
        print(f"Error processing case {case.get('img_filename', 'unknown')}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process GUI grounding datasets using VLLM server.")
    
    # Dataset arguments
    parser.add_argument("--dataset_dir", type=str, required=True, help="Directory containing JSON dataset files")
    parser.add_argument("--image_root", type=str, required=True, help="Root directory for images")
    parser.add_argument("--output_file", type=str, default="./results.jsonl", help="Path to save the single output file (default: ./results.jsonl)")
    
    # Server configuration arguments
    parser.add_argument("--server_ip", type=str, default="localhost", help="VLLM server IP address (default: localhost)")
    parser.add_argument("--server_port", type=int, default=8001, help="VLLM server port (default: 8001)")
    parser.add_argument("--model_name", type=str, default="MAI-UI-8B", help="Model name served by VLLM (default: MAI-UI-8B)")
    parser.add_argument("--api_key", type=str, default="EMPTY", help="API Key for VLLM server (default: EMPTY)")
    
    # Performance arguments
    parser.add_argument("--num_workers", type=int, default=16, help="Number of concurrent workers (default: 16)")
    
    args = parser.parse_args()

    vllm_base_url = f"http://{args.server_ip}:{args.server_port}/v1"

    client = OpenAI(
        api_key=args.api_key,
        base_url=vllm_base_url,
    )

    output_dir = os.path.dirname(args.output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)


    with open(args.output_file, 'w') as f:
        pass

    json_files = glob.glob(os.path.join(args.dataset_dir, "*.json"))
    
    if not json_files:
        print(f"No JSON files found in {args.dataset_dir}")
        exit(1)

    print(f"Connecting to VLLM server: {vllm_base_url}")
    print(f"Using model: {args.model_name}")
    print(f"Image Root: {args.image_root}")
    print(f"Dataset Directory: {args.dataset_dir}")
    print(f"Output File: {args.output_file}")
    print(f"Found {len(json_files)} dataset files.")
    print(f"Concurrent workers: {args.num_workers}")
    print("-" * 60)

    all_tasks = []

    for json_file in json_files:
        dataset_filename = os.path.basename(json_file)
        
        with open(json_file, 'r') as f:
            data = json.load(f)
            print(f"Loaded {len(data)} samples from {dataset_filename}")
            
            for case in data:
                case_with_source = case.copy()
                case_with_source['dataset_source'] = dataset_filename
                
                all_tasks.append({
                    "case": case_with_source,
                    "image_root": args.image_root,
                    "output_file": args.output_file
                })

    print(f"Total tasks across all files: {len(all_tasks)}")
    print("Start processing...")

    with ThreadPoolExecutor(max_workers=args.num_workers) as executor:
        futures = [
            executor.submit(
                process_case, 
                task["case"], 
                task["image_root"], 
                task["output_file"], 
                client, 
                args.model_name
            ) for task in all_tasks
        ]
        
        for _ in tqdm(as_completed(futures), total=len(all_tasks)):
            pass

    print("\nProcessing complete. Calculating aggregated accuracy...")

    stats = defaultdict(lambda: {'total': 0, 'correct': 0})
    total_samples = 0
    total_correct = 0

    if os.path.exists(args.output_file):
        with open(args.output_file, 'r') as f:
            for line in f:
                try:
                    result = json.loads(line)
                    source = result.get('dataset_source', 'unknown')
                    
                    stats[source]['total'] += 1
                    total_samples += 1
                    
                    if result.get('correctness') == 'correct':
                        stats[source]['correct'] += 1
                        total_correct += 1
                except json.JSONDecodeError:
                    continue
        

        print("-" * 60)
        for source, data in sorted(stats.items()):
            file_total = data['total']
            file_correct = data['correct']
            if file_total > 0:
                acc = file_correct / file_total
                print(f"Dataset: {source:30} - Accuracy: {acc:.4f} ({file_correct}/{file_total})")
        
        # Print overall accuracy
        if total_samples > 0:
            total_acc_rate = total_correct / total_samples
            print("-" * 60)
            print(f"Total Samples: {total_samples}")
            print(f"Total Correct: {total_correct}")
            print(f"Overall Accuracy: {total_acc_rate:.4f}")
        else:
            print("No valid results found in output file.")
            
    else:
        print("Output file not found.")