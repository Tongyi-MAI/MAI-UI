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

Use the command below to evaluate the MAI-UI model.

**Note:** While our evaluation script supports "guide text" (prompt pre-filling), this feature is explicitly **disabled** (`--use_guide_text False`) for MAI-UI to align with its standard inference mode.

```bash
CUDA_VISIBLE_DEVICES=0,1,2,3 python eval_screenspot_pro.py \
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

## 📊 Results

For reference, we provide the evaluation results of **MAI-UI-8B**, tested using the script above, in the `output` directory. We summarized these results in the following table:

<div align="center">

| Setting | UI-Vision | MMBench-GUI L2 | ScreenSpot-Pro | ScreenSpot-V2 | OSWorld-G | OSWorld-G Refine |
|------------|-----------|---------|-------|------|------|-------------|
| MAI-UI-8B (Tech Report) | 40.7 | 88.8 | 65.8 | **95.2** |60.1 | 68.6 |
| MAI-UI-8B (Tested by script)  | **40.9**    | **88.9**  | **66.1**| 95.1| **60.9**| **68.7**      |

</div>


