# MAI-UI GUI Grounding Evaluation

This repository contains the evaluation code for the **MAI-UI** model series on GUI grounding tasks. Our training paradigm follows [UI-Ins](https://arxiv.org/abs/2510.20286) (Code: [UI-Ins GitHub](https://github.com/alibaba/UI-Ins)), with specific adaptations tailored for MAI-UI.

## 🛠️ Environment Setup

To set up the environment, run the following commands:

```bash
conda create -n grounding python=3.12
conda activate grounding
pip install -r requirements.txt
```

## 📂 Data Preparation

To facilitate a standardized evaluation across different benchmarks, we have reformatted several popular datasets—including **OSWorld-G**, **MMBench**—to align with the **ScreenSpot-Pro** format. These processed datasets are available in the `data/` directory.

## 🚀 Usage

We provide two methods for evaluation: Local Inference and VLLM Server Inference.

### Option 1: Local Inference

Use the command below to evaluate the MAI-UI model directly.

**Note:** While our evaluation script supports "guide text" (prompt pre-filling), this feature is explicitly **disabled** (`--use_guide_text False`) for MAI-UI to align with its standard inference mode.

```bash
CUDA_VISIBLE_DEVICES=0,1,2,3 python eval_local.py \
    --model_type MAI_UI \
    --model_name_or_path Tongyi-MAI/MAI-UI-8B \
    --screenspot_imgs <Your_Image_Dir> \
    --screenspot_test data/ScreenSpot_Pro_data \
    --task all \
    --language en \
    --gt_type positive \
    --log_path output/SSPro.json \
    --inst_style instruction \
    --max_pixels 6553600 \
    --use_guide_text False
```

### Option 2: VLLM Server Inference

For faster inference or deployment scenarios, you can use VLLM.

**Step 1: Start the VLLM Server**

Launch the OpenAI-compatible API server using the following command:

```bash
python -m vllm.entrypoints.openai.api_server \
    --model Tongyi-MAI/MAI-UI-8B \
    --served-model-name MAI-UI-8B \
    --host 0.0.0.0 \
    --port 8001 \
    --tensor-parallel-size 1 \
    --trust-remote-code
```

**Step 2: Run the Evaluation Client**

Once the server is running, use the client script to perform the evaluation:

```bash
python eval_server.py \
    --dataset_dir data/ScreenSpot_Pro_data \
    --image_root <Your_Image_Dir>\
    --output_file ./SSPro.jsonl \
    --server_ip 0.0.0.0 \
    --server_port 8001 \
    --model_name MAI-UI-8B \
    --api_key EMPTY \
    --num_workers 16
```

## 📊 Results

For reference, we provide the evaluation results of **MAI-UI-8B**, tested using the script above, in the `output_local` and `output_server` directory. We summarized these results in the following table:

<div align="center">

| Setting | UI-Vision | MMBench-GUI L2 | ScreenSpot-Pro | ScreenSpot-V2 | OSWorld-G | OSWorld-G Refine |
|------------|-----------|---------|-------|------|------|-------------|
| MAI-UI-8B (Tech Report) | 40.7 | 88.8 | 65.8 | **95.2** |60.1 | 68.6 |
| MAI-UI-8B (eval locally)  | **40.9**    | **88.9**  | 66.1| 95.1| 60.9| 68.7      |
| MAI-UI-8B (eval by vllm api) | 40.3 | 88.7 | **67.0** | 94.9 | **61.7** | **69.5** | 
</div>