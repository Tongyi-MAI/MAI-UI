import torch
from transformers import AutoProcessor
import re
import os
from PIL import Image
from tqdm import tqdm
from qwen_vl_utils import process_vision_info, smart_resize
import multiprocessing as mp

mp.set_start_method('spawn', force=True)
os.environ["VLLM_WORKER_MULTIPROC_METHOD"] = "spawn"

def parse_coordinates(raw_string):
    matches = re.findall(r'\[(\d+),(\d+)\]', raw_string)
    matches = [tuple(map(int, match)) for match in matches]
    if len(matches) == 0:
        return -1, -1
    else:
        return matches[0]

def get_qwen3_vl_prompt_msg(image, instruction):
    messages = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": """You are a GUI grounding agent. 
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
"""}
            ]
        }
    ]

    messages.append(
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": instruction + "\n"
                },
                {"type": "image", "image": image}
            ]
        }
    )
    return messages

class CustomQwen3_VL_VLLM_Model():
    def __init__(self):
        from multiprocessing import current_process
        process = current_process()
        if process.daemon:
            print("Latest vllm versions spawns children processes, therefore can not be started in a daemon process. Are you using multiprocess.Pool? Try multiprocess.Process instead.")

    def load_model(self, model_name_or_path="Qwen/Qwen3-VL-30B-A3B-Instruct", max_pixels=99999999):
        from vllm import LLM
        self.max_pixels = max_pixels
        self.model = LLM(
            model=model_name_or_path,
            limit_mm_per_prompt={"image": 1,},
            trust_remote_code=True,
            dtype="auto",
            tensor_parallel_size=torch.cuda.device_count(),
            gpu_memory_utilization=0.90,
            max_model_len=32768,
            mm_processor_kwargs={
                "min_pixels": 16 * 16 * 4,
                "max_pixels": self.max_pixels,
            },
        )
        self.processor = AutoProcessor.from_pretrained(model_name_or_path, trust_remote_code=True, do_resize=False)

    def set_generation_config(self, **kwargs):
        pass

    def ground_only_positive(self, instruction, image, use_guide_text=False):
        from vllm import SamplingParams
        if isinstance(image, str):
            image_path = image
            assert os.path.exists(image_path) and os.path.isfile(image_path), "Invalid input image path."
            image = Image.open(image_path).convert('RGB')
        assert isinstance(image, Image.Image), "Invalid input image."

        resized_height, resized_width = smart_resize(
            image.height,
            image.width,
            factor=16 * 2,
            min_pixels=16 * 16 * 4,
            max_pixels=self.max_pixels,
        )
        resized_image = image.resize((resized_width, resized_height))

        inputs = [{
            "prompt": get_qwen3_vl_prompt_msg(
                image_path, 
                instruction, 

            ),
            "multi_modal_data": {"image": resized_image}
        }]
        if use_guide_text:
            guide_text = "<tool_call>\n{\"name\": \"grounding\", \"arguments\": {\"action\": \"click\", \"coordinate\": ["
            inputs[0]["prompt"] += guide_text

        generated = self.model.generate(inputs, sampling_params=SamplingParams(temperature=0.0, max_tokens=256))

        response = generated[0].outputs[0].text.strip()
        print(response)
        if use_guide_text:
            response = """<tool_call>\n{"name": "grounding", "arguments": {"action": "click", "coordinate": [""" + response

        cut_index = response.rfind('}')
        if cut_index != -1:
            response = response[:cut_index + 1]
        print(response)

        result_dict = {
            "result": "positive",
            "format": "x1y1x2y2",
            "raw_response": response,
            "bbox": None,
            "point": None
        }

        try:
            x, y = parse_coordinates(response)
            coordinates = [x, y]
            if len(coordinates) == 2:
                point_x, point_y = coordinates
            elif len(coordinates) == 4:
                x1, y1, x2, y2 = coordinates
                point_x = (x1 + x2) / 2
                point_y = (y1 + y2) / 2
            else:
                raise ValueError("Wrong output format")
            print(point_x, point_y)
            result_dict["point"] = [point_x / resized_width, point_y / resized_height]
        except (IndexError, KeyError, TypeError, ValueError) as e:
            pass
        
        return result_dict

    def batch_ground_only_positive(self, instructions, images, use_guide_text=False):
        from vllm import SamplingParams
        assert len(instructions) == len(images), "Number of instructions and images must match"
        
        batch_inputs = []
        resized_images = []
        resized_dimensions = []
        
        print("Processing {} images and inputs...".format(len(instructions)))
        for instruction, image in tqdm(zip(instructions, images)):
            if isinstance(image, str):
                image_path = image
                assert os.path.exists(image_path) and os.path.isfile(image_path), f"Invalid input image path: {image_path}"
                image = Image.open(image_path).convert('RGB')
            assert isinstance(image, Image.Image), "Invalid input image."

            resized_height, resized_width = smart_resize(
                image.height,
                image.width,
                factor=14 * 2,
                min_pixels=28 * 28,
                max_pixels=self.max_pixels,
            )
            
            messages = get_qwen3_vl_prompt_msg(
                image_path, 
                instruction, 
            )

            prompt = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            if use_guide_text:
                guide_text = "<tool_call>\n{\"name\": \"grounding\", \"arguments\": {\"action\": \"click\", \"coordinate\": ["
                prompt += guide_text

            image_inputs, _, _ = process_vision_info(messages, image_patch_size=16, return_video_kwargs=True, return_video_metadata=True)
            resized_dimensions.append((resized_width, resized_height))
            
            batch_inputs.append({
                "prompt": prompt,
                "multi_modal_data": {"image": image_inputs} if image_inputs is not None else {},
                "metadata": {"image_path": image_path, "original_data": instruction}
            })

        sampling_params = SamplingParams(temperature=0.01, max_tokens=256)
        batch_outputs = self.model.generate(batch_inputs, sampling_params=sampling_params, use_tqdm=True)
        
        results = []
        for output, (resized_width, resized_height) in zip(batch_outputs, resized_dimensions):
            response = output.outputs[0].text.strip()
            if use_guide_text:
                response = """<tool_call>\n{"name": "grounding", "arguments": {"action": "click", "coordinate": [""" + response

            result_dict = {
                "result": "positive",
                "format": "x1y1x2y2",
                "raw_response": response,
                "bbox": None,
                "point": None
            }

            cut_index = response.rfind('}')
            if cut_index != -1:
                response = response[:cut_index + 1]

            try:
                x, y = parse_coordinates(response)
                coordinates = [x, y]
                if len(coordinates) == 2:
                    point_x, point_y = coordinates
                elif len(coordinates) == 4:
                    x1, y1, x2, y2 = coordinates
                    point_x = (x1 + x2) / 2
                    point_y = (y1 + y2) / 2
                else:
                    raise ValueError("Wrong output format")
                result_dict["point"] = [point_x / 1000, point_y / 1000]
            except (IndexError, KeyError, TypeError, ValueError) as e:
                pass
            
            results.append(result_dict)

        for i in range(len(results)):
            print("index:", i)
            print("prompt:", "\n".join(batch_inputs[i]["prompt"].split("\n")[-4:]))
            print("raw_response:", results[i]["raw_response"])
            print("===="*20)
        
        return results