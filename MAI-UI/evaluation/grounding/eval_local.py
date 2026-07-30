import copy
import itertools

import torch
import json
import re
import argparse
import os
from PIL import Image
import logging
from tqdm import tqdm
import pdb

logging.basicConfig(level=logging.INFO)
torch.manual_seed(114514)

GT_TYPES = ['positive', 'negative']
INSTRUCTION_STYLES = ['instruction', 'action', 'description']
LANGUAGES = ['en', 'cn']

def parse_args():
    def str_to_bool(val):
        return val.lower() in ('true', '1', 'yes', 'on', 'y')
    parser = argparse.ArgumentParser()
    parser.add_argument('--model_type', type=str, required=True)
    parser.add_argument('--model_name_or_path', type=str, required=False)
    parser.add_argument('--screenspot_imgs', type=str, required=True)
    parser.add_argument('--screenspot_test', type=str, required=True)
    parser.add_argument('--task', type=str, default="all")
    parser.add_argument('--inst_style', type=str, choices=INSTRUCTION_STYLES + ['all'], help="Instruction style to use.", default="instruction")
    parser.add_argument('--language', type=str, choices=LANGUAGES + ['all'], default='en')
    parser.add_argument('--gt_type', type=str, choices=GT_TYPES + ['all'], default="positive")
    parser.add_argument('--log_path', type=str, required=True)
    parser.add_argument('--use_guide_text', type=str_to_bool, default=True, help="Use guide text for Qwen2.5VL models.")
    parser.add_argument('--max_pixels', type=int, default=2116800, help="Maximum number of pixels for the model to process. Default is 2116800 (1440x1440).")

    args = parser.parse_args()
    return args

def build_model(args):
    model_type = args.model_type
    model_name_or_path = args.model_name_or_path
    max_pixels = args.max_pixels if hasattr(args, 'max_pixels') else 2116800

    if model_type == "MAI_UI":
        from models.MAI_UI import CustomQwen3_VL_VLLM_Model
        model = CustomQwen3_VL_VLLM_Model()
        model.load_model(model_name_or_path=model_name_or_path, max_pixels=max_pixels)



    else:
        raise ValueError(f"Unsupported model type {model_type}.")
    return model

def collect_results_to_eval(results, platform=None, group=None, application=None, language=None, gt_type=None, instruction_style=None, ui_type=None):
    filtered_results = []

    for sample in results:
        if (platform is None or sample.get("platform") == platform) and \
           (group is None or sample.get("group") == group) and \
           (application is None or sample.get("application") == application) and \
           (language is None or sample.get("language") == language) and \
           (gt_type is None or sample.get("gt_type") == gt_type) and \
           (instruction_style is None or sample.get("instruction_style") == instruction_style) and \
           (ui_type is None or sample.get("ui_type") == ui_type):
            filtered_results.append(sample)

    return filtered_results


def make_combinations(results, platform=False, group=None, application=False, language=False, gt_type=False, instruction_style=False, ui_type=False):
    unique_values = {
        "platform": set(),
        "group": set(),
        "application": set(),
        "language": set(),
        "gt_type": set(),
        "instruction_style": set(),
        "ui_type": set(),
    }

    for sample in results:
        if platform:
            unique_values["platform"].add(sample.get("platform"))
        if group:
            unique_values["group"].add(sample.get("group"))
        if application:
            unique_values["application"].add(sample.get("application"))
        if language:
            unique_values["language"].add(sample.get("language"))
        if gt_type:
            unique_values["gt_type"].add(sample.get("gt_type"))
        if instruction_style:
            unique_values["instruction_style"].add(sample.get("instruction_style"))
        if ui_type:
            unique_values["ui_type"].add(sample.get("ui_type"))

    filtered_values = {key: list(value) for key, value in unique_values.items() if value}
    if not filtered_values:
        return []

    attribute_combinations = list(itertools.product(*filtered_values.values()))

    combinations = []
    for combination in attribute_combinations:
        combinations.append(dict(zip(filtered_values.keys(), combination)))

    return combinations


def calc_metric_for_result_list(results):
    num_total = len(results)
    correct_num = sum(1 for res in results if res["correctness"] == "correct")
    wrong_format_num = sum(1 for res in results if res["correctness"] == "wrong_format")

    text_results = collect_results_to_eval(results, ui_type="text")
    icon_results = collect_results_to_eval(results, ui_type="icon")

    text_correct = sum(1 for res in text_results if res["correctness"] == "correct")
    text_total = len(text_results)
    icon_correct = sum(1 for res in icon_results if res["correctness"] == "correct")
    icon_total = len(icon_results)
    metrics = {
        "num_correct_action": correct_num,
        "num_total": num_total,
        "wrong_format_num": wrong_format_num,
        "action_acc": correct_num / num_total if num_total > 0 else 0,
        "text_acc": text_correct / text_total if text_total > 0 else 0,
        "icon_acc": icon_correct / icon_total if icon_total > 0 else 0
    }
    return metrics


def eval_sample_positive_gt(sample, response):
    bbox = sample["bbox"]
    bbox = [bbox[0], bbox[1], bbox[2], bbox[3]]
    img_size = sample["img_size"]
    bbox = [bbox[0] / img_size[0], bbox[1] / img_size[1], bbox[2] / img_size[0], bbox[3] / img_size[1]]
    
    click_point = response["point"]
    print(click_point)
    if click_point is None:
        return "wrong_format"
    if (bbox[0] <= click_point[0] <= bbox[2]) and (bbox[1] <= click_point[1] <= bbox[3]):
        return "correct"
    else:
        return "wrong"
    
def eval_sample_negative_gt(sample, response):
    if response["result"] == "negative":
        return "correct"
    elif response["result"] == "positive":
        return "wrong"
    else:
        return "wrong_format"

def evaluate_fine_grained(results):
    combinations = make_combinations(
        results, 
        platform=True, 
        application=True,
        instruction_style=True, 
        gt_type=True
    )

    evaluation_result = {}

    for combo in combinations:
        platform = combo.get("platform")
        application = combo.get("application")
        inst_style = combo.get("instruction_style")
        gt_type = combo.get("gt_type")
        
        filtered_results = collect_results_to_eval(
            results=results,
            platform=platform,
            application=application,
            instruction_style=inst_style,
            gt_type=gt_type
        )
        
        metrics = calc_metric_for_result_list(filtered_results)
        if metrics['num_total'] == 0:
            continue
        
        key = f"plat:{platform} app:{application} inst_style:{inst_style} gt_type:{gt_type}"
        evaluation_result[key] = metrics

    return evaluation_result

def evaluate_seeclick_paper_style(results):
    combinations = make_combinations(
        results, 
        platform=True, 
        instruction_style=True, 
        gt_type=True
    )

    evaluation_result = {}

    for combo in combinations:
        platform = combo.get("platform")
        inst_style = combo.get("instruction_style")
        gt_type = combo.get("gt_type")
        
        filtered_results = collect_results_to_eval(
            results=results,
            platform=platform,
            instruction_style=inst_style,
            gt_type=gt_type
        )
        
        metrics = calc_metric_for_result_list(filtered_results)
        if metrics['num_total'] == 0:
            continue
        
        key = f"plat:{platform} inst_style:{inst_style} gt_type:{gt_type}"
        evaluation_result[key] = metrics

    return evaluation_result

def evaluate_leaderboard_detailed_style(results):
    combinations = make_combinations(
        results, 
        application=True,
    )

    evaluation_result = {}

    for combo in combinations:
        application = combo.get("application")
        
        filtered_results = collect_results_to_eval(
            results=results,
            application=application,
        )
        
        metrics = calc_metric_for_result_list(filtered_results)
        if metrics['num_total'] == 0:
            continue
        
        key = f"app:{application}"
        evaluation_result[key] = metrics

    return evaluation_result

def evaluate_leaderboard_simple_style(results):
    combinations = make_combinations(
        results, 
        group=True,
    )

    evaluation_result = {}

    for combo in combinations:
        group = combo.get("group")
        
        filtered_results = collect_results_to_eval(
            results=results,
            group=group,
        )
        
        metrics = calc_metric_for_result_list(filtered_results)
        if metrics['num_total'] == 0:
            continue
        
        key = f"group:{group}"
        evaluation_result[key] = metrics

    return evaluation_result

def evaluate_overall(results):
    metrics = calc_metric_for_result_list(results)
    
    return metrics


def evaluate(results):
    result_report = {
        "details": [],
        "metrics": {}
    }

    result_report["metrics"]["fine_grained"] = evaluate_fine_grained(results)
    result_report["metrics"]["seeclick_style"] = evaluate_seeclick_paper_style(results)
    result_report["metrics"]["leaderboard_simple_style"] = evaluate_leaderboard_simple_style(results)
    result_report["metrics"]["leaderboard_detailed_style"] = evaluate_leaderboard_detailed_style(results)
    result_report["metrics"]["overall"] = evaluate_overall(results)

    result_report["details"] = results

    return result_report

def main(args):
    print(args)
    model = build_model(args)
    print("Load model success")

    if args.task == "all":
        task_filenames = [
            os.path.splitext(f)[0]
            for f in os.listdir(args.screenspot_test)
            if f.endswith(".json")
        ]
    else:
        task_filenames = args.task.split(",")

    if args.inst_style == "all":
        inst_styles = INSTRUCTION_STYLES
    else:
        inst_styles = args.inst_style.split(",")

    if args.language == "all":
        languages = LANGUAGES
    else:
        languages = args.language.split(",")

    if args.gt_type == "all":
        gt_types = GT_TYPES
    else:
        gt_types = args.gt_type.split(",")

    tasks_to_run = []
    for task_filename in task_filenames:
        dataset = task_filename + ".json"
        with open(os.path.join(args.screenspot_test, dataset), 'r') as f:
            task_data = json.load(f)

        for inst_style in inst_styles:
            for gt_type in gt_types:
                for lang in languages:
                    for task_instance in task_data:
                        task_instance = copy.deepcopy(task_instance)
                        task_instance["task_filename"] = task_filename
                        task_instance["gt_type"] = gt_type
                        task_instance["instruction_style"] = inst_style
                        task_instance["language"] = lang
                        if lang == "cn":
                            if inst_style!= 'instruction' or gt_type != 'positive':
                                raise AttributeError("Only positive samples and 'instruction' style are supported for Chinese instructions.")
                            task_instance["prompt_to_evaluate"] = task_instance["instruction_cn"]
                        elif lang == "en":
                            task_instance["prompt_to_evaluate"] = task_instance["instruction"]

                        tasks_to_run.append(task_instance)
        print(f"Num of sample in {task_filename}: {len(task_data)} * {len(inst_styles)} * {len(gt_types)} * {len(languages)} = {len(task_data) * len(inst_styles) * len(gt_types) * len(languages)}")
    print(f"Total tasks: {len(tasks_to_run)}")

    results = []
    batch_size = 100

    for batch_start in tqdm(range(0, len(tasks_to_run), batch_size)):
        batch_end = min(batch_start + batch_size, len(tasks_to_run))
        batch_samples = tasks_to_run[batch_start:batch_end]

        positive_samples = [s for s in batch_samples if s["gt_type"] == "positive"]
        negative_samples = [s for s in batch_samples if s["gt_type"] == "negative"]

        if positive_samples:
            positive_instructions = [s["prompt_to_evaluate"] for s in positive_samples]
            positive_images = [os.path.join(args.screenspot_imgs, s["img_filename"]) for s in positive_samples]

            try:
                positive_responses = model.batch_ground_only_positive(
                    instructions=positive_instructions,
                    images=positive_images,
                    use_guide_text=args.use_guide_text
                )
            except Exception as e:
                print(f"Error in batch processing positive samples: {e}")
                positive_responses = []
                for sample in tqdm(positive_samples):
                    try:
                        response = model.ground_only_positive(
                            instruction=sample["prompt_to_evaluate"],
                            image=os.path.join(args.screenspot_imgs, sample["img_filename"]),
                            use_guide_text=args.use_guide_text
                        )
                        print(f"Processed positive sample: {sample['img_filename']}")
                        print(sample["prompt_to_evaluate"])
                        print(response)
                        positive_responses.append(response)
                    except Exception as e:
                        print(f"Error processing single positive sample: {e}")
                        positive_responses.append({
                            "result": "positive",
                            "format": "x1y1x2y2",
                            "raw_response": "ERROR",
                            "bbox": None,
                            "point": None
                        })
        negative_responses = []
        if negative_samples:
            for sample in negative_samples:
                try:
                    response = model.ground_allow_negative(
                        instruction=sample["prompt_to_evaluate"],
                        image=os.path.join(args.screenspot_imgs, sample["img_filename"])
                    )
                    negative_responses.append(response)
                except Exception as e:
                    print(f"Error processing negative sample: {e}")
                    negative_responses.append({
                        "result": "negative",
                        "raw_response": "ERROR",
                        "bbox": None,
                        "point": None
                    })

        all_responses = []
        pos_idx = 0
        neg_idx = 0
        for sample in batch_samples:
            if sample["gt_type"] == "positive":
                all_responses.append(positive_responses[pos_idx])
                pos_idx += 1
            else:
                all_responses.append(negative_responses[neg_idx])
                neg_idx += 1

        for sample, response in zip(batch_samples, all_responses):
            point = response["point"]
            img_size = sample["img_size"]
            point_in_pixel = [point[0] * img_size[0], point[1] * img_size[1]] if point else None
            
            sample_result = {
                "id": sample["id"],
                "img_path": os.path.join(args.screenspot_imgs, sample["img_filename"]), 
                "group": sample["group"] if "group" in sample else None,
                "platform": sample["platform"],
                "application": sample["application"],
                "lang": sample["language"],
                "instruction_style": sample["instruction_style"],
                "prompt_to_evaluate": sample["prompt_to_evaluate"], 
                "gt_type": sample["gt_type"],
                "ui_type": sample["ui_type"], 
                "task_filename": sample["task_filename"], 
                "pred": point_in_pixel, 
                "raw_response": response["raw_response"]
            }

            if sample["gt_type"] == "positive":
                correctness = eval_sample_positive_gt(sample, response)
                sample_result.update({
                    "bbox": sample["bbox"], 
                })
            elif sample["gt_type"] == "negative":
                correctness = eval_sample_negative_gt(sample, response)
            else:
                raise ValueError("Wrong instruction type")

            sample_result.update({
                "correctness": correctness,
            })
            results.append(sample_result)
        
    result_report = evaluate(results)
    os.makedirs(os.path.dirname(args.log_path), exist_ok=True)
    with open(args.log_path, 'w') as f:
        json.dump(result_report, f, indent=4)
    logging.info("Evaluation of ScreenSpot finished.")


if __name__ == "__main__":
    main(parse_args())