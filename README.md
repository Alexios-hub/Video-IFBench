# Video-IFBench: Evaluating Instruction Following of Multimodal LLMs in Video Understanding Scenarios

<p align="center">
  <a href="https://scholar.google.com/citations?user=GcgqbCUAAAAJ&hl=zh-CN"><strong>Hongbo Liu</strong></a><sup>1,*</sup>,
  &emsp;
  <a href="https://scholar.google.com/citations?user=WRGF9B8AAAAJ"><strong>Peixian Chen</strong></a><sup>2,*</sup>,
  &emsp;
  <a href="https://scholar.google.com/citations?user=N_0VdSwAAAAJ"><strong>Sihan Liu</strong></a><sup>2</sup>,
  &emsp;
  <a href="https://scholar.google.com/citations?user=rQbW67AAAAAJ"><strong>Peiyuan Zhang</strong></a><sup>3</sup>,
  &emsp;
  <a href="https://scholar.google.com/citations?user=Bd6y_UsAAAAJ"><strong>Kai Zou</strong></a><sup>4</sup>,
  &emsp;
  <a href="https://scholar.google.com/citations?user=0dkD_dcAAAAJ"><strong>Dian Zheng</strong></a><sup>5</sup>,
  &emsp;
  <a href="https://scholar.google.com/citations?user=zBM8_XkAAAAJ"><strong>Xiaoxing Hu</strong></a><sup>3</sup>,
  &emsp;
  <a href="https://scholar.google.com/citations?user=kMui170AAAAJ"><strong>Yuhao Dong</strong></a><sup>6</sup>,
  &emsp;
  <a href="https://scholar.google.com/citations?user=C941xtsAAAAJ"><strong>Mengdan Zhang</strong></a><sup>2</sup>,
  &emsp;
  <a href="https://scholar.google.com/citations?user=29teR74AAAAJ"><strong>Yunhang Shen</strong></a><sup>2</sup>,
  &emsp;
  <a href="https://scholar.google.com/citations?user=LV8ejn8AAAAJ"><strong>Haoyu Cao</strong></a><sup>2</sup>,
  &emsp;
  <a href="https://scholar.google.com/citations?user=AjxoEpIAAAAJ"><strong>Wei Liu</strong></a><sup>2</sup>,
  &emsp;
  <a href="https://github.com/Alexios-hub/Video-IFBench#no-profile" aria-disabled="true"><strong>Weibo Gu</strong></a><sup>2</sup>,
  &emsp;
  <a href="https://scholar.google.com/citations?user=IUtix9IAAAAJ"><strong>Xing Sun</strong></a><sup>2</sup>,
  &emsp;
  <a href="https://github.com/Alexios-hub/Video-IFBench#no-profile" aria-disabled="true"><strong>Shengjie Zhao</strong></a><sup>1,&dagger;</sup>
</p>

<p align="center">
  <sup>1</sup>TJU &emsp;
  <sup>2</sup>Tencent Youtu Lab &emsp;
  <sup>3</sup>SJTU &emsp;
  <sup>4</sup>Tencent Hunyuan &emsp;
  <sup>5</sup>CUHK &emsp;
  <sup>6</sup>NTU
</p>

<p align="center">
  <sup>*</sup> Equal contribution &emsp;
  <sup>&dagger;</sup> Corresponding author
</p>

<p align="center">
  <a href="https://arxiv.org/pdf/2608.25529">
    <img src="https://img.shields.io/badge/Paper-arXiv-B31B1B?logo=arxiv" alt="Paper">
  </a>
  <a href="https://alexios-hub.github.io/Video-IFBench/">
    <img src="https://img.shields.io/badge/Project%20Page-Website-lightgrey?logo=googlechrome" alt="Project Page">
  </a>
  <a href="https://huggingface.co/datasets/Alexislhb/Video-IFBench">
    <img src="https://img.shields.io/badge/Dataset-HuggingFace-orange?logo=huggingface" alt="Dataset">
  </a>
</p>

<p align="center">
  <img src="docs/assets/paper/overview.webp" alt="Overview of the Video-IFBench construction and evaluation pipeline" width="100%">
</p>

## 🚀 Getting Started

### Installation

```bash
git clone https://github.com/Alexios-hub/Video-IFBench.git
cd Video-IFBench
pip install -e .
```

### Dataset Preparation

Download the evaluation split from [Hugging Face](https://huggingface.co/datasets/Alexislhb/Video-IFBench):

```bash
huggingface-cli download Alexislhb/Video-IFBench \
  --repo-type dataset \
  --local-dir data/Video-IFBench
```

The runner expects the following layout:

```text
data/Video-IFBench/
├── annotations/
│   └── annotations.jsonl
├── videos/
│   └── <video files>
└── subtitles/                 # optional timestamped ASR files
    └── <subtitle files>
```

Use this directory as `--dataset-root` when running inference.

### Run Inference

The runner supports OpenAI-compatible endpoints, including OpenAI-style APIs, vLLM, SGLang, and other compatible servers.

```bash
video-ifbench-run \
  --dataset-root data/Video-IFBench \
  --output-dir outputs/model_name \
  --api-base http://localhost:8000/v1 \
  --model model_name \
  --media-mode video-url \
  --concurrency 32 \
  --resume
```

Each output file is a `*.response.json` record containing the model response and the metadata required for scoring.

Add `--use-asr` to use timestamped ASR.

### Score Responses

```bash
video-ifbench-score \
  --response-dir outputs/model_name \
  --output-json outputs/model_name/_instruction_following_report.json \
  --judge-api-base http://localhost:8001/v1 \
  --judge-model judge_model_name \
  --concurrency 16
```

### Summarize Metrics

```bash
video-ifbench-summarize \
  --report outputs/model_name/_instruction_following_report.json \
  --model-name "model_name" \
  --format latex
```

## 📊 Main Results

<div align="center">
<table width="100%">
  <thead>
    <tr>
      <th scope="col" rowspan="2" align="left" width="25%">Model</th>
      <th scope="colgroup" colspan="2" align="center" width="15%">Single</th>
      <th scope="colgroup" colspan="2" align="center" width="15%">Multi</th>
      <th scope="colgroup" colspan="2" align="center" width="15%">Selection</th>
      <th scope="colgroup" colspan="2" align="center" width="15%">Nested</th>
      <th scope="colgroup" colspan="2" align="center" width="15%">Overall</th>
    </tr>
    <tr>
      <th scope="col" align="center" width="7.5%"><sub>TCSR</sub></th>
      <th scope="col" align="center" width="7.5%"><sub>TISR</sub></th>
      <th scope="col" align="center" width="7.5%"><sub>TCSR</sub></th>
      <th scope="col" align="center" width="7.5%"><sub>TISR</sub></th>
      <th scope="col" align="center" width="7.5%"><sub>TCSR</sub></th>
      <th scope="col" align="center" width="7.5%"><sub>TISR</sub></th>
      <th scope="col" align="center" width="7.5%"><sub>TCSR</sub></th>
      <th scope="col" align="center" width="7.5%"><sub>TISR</sub></th>
      <th scope="col" align="center" width="7.5%"><sub>TCSR</sub></th>
      <th scope="col" align="center" width="7.5%"><sub>TISR</sub></th>
    </tr>
  </thead>
  <tbody>
    <tr><th scope="rowgroup" colspan="11" align="center"><em>Proprietary Models</em></th></tr>
    <tr>
      <th scope="row" align="left">Gemini-3-Pro</th>
      <td align="center"><strong>79.6</strong></td>
      <td align="center"><strong>52.3</strong></td>
      <td align="center"><strong>88.6</strong></td>
      <td align="center"><strong>58.8</strong></td>
      <td align="center"><strong>68.5</strong></td>
      <td align="center"><strong>59.2</strong></td>
      <td align="center"><strong>53.7</strong></td>
      <td align="center"><strong>46.0</strong></td>
      <td align="center"><strong>76.5</strong></td>
      <td align="center"><strong>54.5</strong></td>
    </tr>
    <tr>
      <th scope="row" align="left">Gemini-3-Flash</th>
      <td align="center">76.7</td>
      <td align="center">49.2</td>
      <td align="center">87.6</td>
      <td align="center">56.4</td>
      <td align="center">63.9</td>
      <td align="center">54.8</td>
      <td align="center">39.9</td>
      <td align="center">30.7</td>
      <td align="center">72.2</td>
      <td align="center">49.5</td>
    </tr>
    <tr>
      <th scope="row" align="left">Doubao-Seed-2.0-Pro-260215</th>
      <td align="center">76.7</td>
      <td align="center">44.6</td>
      <td align="center">87.1</td>
      <td align="center">51.1</td>
      <td align="center">46.5</td>
      <td align="center">38.2</td>
      <td align="center">17.8</td>
      <td align="center">14.4</td>
      <td align="center">65.7</td>
      <td align="center">40.8</td>
    </tr>
    <tr>
      <th scope="row" align="left">GPT-5.4</th>
      <td align="center">72.8</td>
      <td align="center">34.7</td>
      <td align="center">82.4</td>
      <td align="center">43.2</td>
      <td align="center">21.1</td>
      <td align="center">16.9</td>
      <td align="center">12.1</td>
      <td align="center">7.60</td>
      <td align="center">57.4</td>
      <td align="center">30.0</td>
    </tr>
    <tr><th scope="rowgroup" colspan="11" align="center"><em>Open-source Models (Instruct)</em></th></tr>
    <tr>
      <th scope="row" align="left">Qwen2.5-Omni-3B</th>
      <td align="center">35.2</td>
      <td align="center">11.6</td>
      <td align="center">34.0</td>
      <td align="center">8.60</td>
      <td align="center">7.70</td>
      <td align="center">5.40</td>
      <td align="center">6.50</td>
      <td align="center">4.50</td>
      <td align="center">25.8</td>
      <td align="center">8.60</td>
    </tr>
    <tr>
      <th scope="row" align="left">Qwen2.5-Omni-7B</th>
      <td align="center">46.3</td>
      <td align="center">16.6</td>
      <td align="center">48.6</td>
      <td align="center">14.9</td>
      <td align="center">15.6</td>
      <td align="center">11.5</td>
      <td align="center">8.90</td>
      <td align="center">5.50</td>
      <td align="center">36.0</td>
      <td align="center">13.5</td>
    </tr>
    <tr>
      <th scope="row" align="left">Qwen3-Omni-30B-A3B-Instruct</th>
      <td align="center">57.9</td>
      <td align="center">21.4</td>
      <td align="center">62.9</td>
      <td align="center">22.9</td>
      <td align="center">17.2</td>
      <td align="center">14.3</td>
      <td align="center">6.10</td>
      <td align="center">4.10</td>
      <td align="center">44.3</td>
      <td align="center">18.0</td>
    </tr>
    <tr>
      <th scope="row" align="left">Gemma-4-E4B-it</th>
      <td align="center">56.8</td>
      <td align="center">22.1</td>
      <td align="center">67.5</td>
      <td align="center">29.9</td>
      <td align="center">11.9</td>
      <td align="center">8.20</td>
      <td align="center">6.00</td>
      <td align="center">3.80</td>
      <td align="center">45.1</td>
      <td align="center">19.5</td>
    </tr>
    <tr>
      <th scope="row" align="left">Gemma-4-26B-A4B-it</th>
      <td align="center">71.6</td>
      <td align="center">35.7</td>
      <td align="center">79.2</td>
      <td align="center">41.1</td>
      <td align="center">22.7</td>
      <td align="center">19.4</td>
      <td align="center">7.10</td>
      <td align="center">4.50</td>
      <td align="center">55.6</td>
      <td align="center">29.7</td>
    </tr>
    <tr>
      <th scope="row" align="left">Gemma-4-31B-it</th>
      <td align="center"><strong>75.8</strong></td>
      <td align="center"><strong>43.0</strong></td>
      <td align="center">82.1</td>
      <td align="center"><strong>44.4</strong></td>
      <td align="center"><strong>29.9</strong></td>
      <td align="center"><strong>25.4</strong></td>
      <td align="center">13.8</td>
      <td align="center"><strong>10.0</strong></td>
      <td align="center"><strong>60.4</strong></td>
      <td align="center"><strong>35.4</strong></td>
    </tr>
    <tr>
      <th scope="row" align="left">InternVL3.5-8B-Instruct</th>
      <td align="center">53.4</td>
      <td align="center">19.1</td>
      <td align="center">63.6</td>
      <td align="center">21.8</td>
      <td align="center">16.3</td>
      <td align="center">10.1</td>
      <td align="center">7.60</td>
      <td align="center">3.50</td>
      <td align="center">43.1</td>
      <td align="center">16.0</td>
    </tr>
    <tr>
      <th scope="row" align="left">InternVL3.5-14B-Instruct</th>
      <td align="center">56.2</td>
      <td align="center">19.1</td>
      <td align="center">66.3</td>
      <td align="center">22.6</td>
      <td align="center">18.6</td>
      <td align="center">12.5</td>
      <td align="center">6.20</td>
      <td align="center">3.50</td>
      <td align="center">45.1</td>
      <td align="center">16.6</td>
    </tr>
    <tr>
      <th scope="row" align="left">InternVL3.5-30B-A3B-Instruct</th>
      <td align="center">57.0</td>
      <td align="center">19.2</td>
      <td align="center">65.9</td>
      <td align="center">24.8</td>
      <td align="center">21.2</td>
      <td align="center">13.8</td>
      <td align="center"><strong>16.2</strong></td>
      <td align="center">9.60</td>
      <td align="center">47.4</td>
      <td align="center">18.5</td>
    </tr>
    <tr>
      <th scope="row" align="left">InternVL3.5-38B-Instruct</th>
      <td align="center">61.0</td>
      <td align="center">24.5</td>
      <td align="center">71.8</td>
      <td align="center">27.1</td>
      <td align="center">18.5</td>
      <td align="center">12.7</td>
      <td align="center">14.6</td>
      <td align="center">8.40</td>
      <td align="center">49.8</td>
      <td align="center">20.8</td>
    </tr>
    <tr>
      <th scope="row" align="left">InternVL3.5-241B-A28B-Instruct</th>
      <td align="center">64.5</td>
      <td align="center">24.6</td>
      <td align="center">75.3</td>
      <td align="center">32.2</td>
      <td align="center">16.0</td>
      <td align="center">12.3</td>
      <td align="center">13.6</td>
      <td align="center">10.4</td>
      <td align="center">51.7</td>
      <td align="center">22.7</td>
    </tr>
    <tr>
      <th scope="row" align="left">Qwen3-VL-4B-Instruct</th>
      <td align="center">55.6</td>
      <td align="center">19.9</td>
      <td align="center">65.6</td>
      <td align="center">20.9</td>
      <td align="center">15.1</td>
      <td align="center">11.4</td>
      <td align="center">8.70</td>
      <td align="center">5.10</td>
      <td align="center">44.3</td>
      <td align="center">16.4</td>
    </tr>
    <tr>
      <th scope="row" align="left">Qwen3-VL-8B-Instruct</th>
      <td align="center">60.1</td>
      <td align="center">23.5</td>
      <td align="center">68.9</td>
      <td align="center">24.7</td>
      <td align="center">17.8</td>
      <td align="center">13.0</td>
      <td align="center">13.5</td>
      <td align="center">8.50</td>
      <td align="center">48.0</td>
      <td align="center">19.6</td>
    </tr>
    <tr>
      <th scope="row" align="left">Qwen3-VL-30B-A3B-Instruct</th>
      <td align="center">56.8</td>
      <td align="center">19.9</td>
      <td align="center">70.4</td>
      <td align="center">25.4</td>
      <td align="center">17.0</td>
      <td align="center">12.3</td>
      <td align="center">13.6</td>
      <td align="center">9.50</td>
      <td align="center">47.2</td>
      <td align="center">18.6</td>
    </tr>
    <tr>
      <th scope="row" align="left">Qwen3-VL-235B-A22B-Instruct</th>
      <td align="center">67.5</td>
      <td align="center">31.9</td>
      <td align="center">78.0</td>
      <td align="center">35.1</td>
      <td align="center">19.5</td>
      <td align="center">14.5</td>
      <td align="center">8.60</td>
      <td align="center">6.00</td>
      <td align="center">53.1</td>
      <td align="center">25.8</td>
    </tr>
    <tr>
      <th scope="row" align="left">Qwen3.5-4B-Instruct</th>
      <td align="center">54.6</td>
      <td align="center">22.0</td>
      <td align="center">65.5</td>
      <td align="center">23.3</td>
      <td align="center">15.2</td>
      <td align="center">8.80</td>
      <td align="center">7.90</td>
      <td align="center">4.00</td>
      <td align="center">43.9</td>
      <td align="center">17.3</td>
    </tr>
    <tr>
      <th scope="row" align="left">Qwen3.5-9B-Instruct</th>
      <td align="center">57.8</td>
      <td align="center">22.6</td>
      <td align="center">70.0</td>
      <td align="center">27.3</td>
      <td align="center">16.2</td>
      <td align="center">12.4</td>
      <td align="center">8.10</td>
      <td align="center">5.00</td>
      <td align="center">46.6</td>
      <td align="center">19.6</td>
    </tr>
    <tr>
      <th scope="row" align="left">Qwen3.5-27B-Instruct</th>
      <td align="center">66.7</td>
      <td align="center">29.1</td>
      <td align="center">77.8</td>
      <td align="center">33.8</td>
      <td align="center">23.0</td>
      <td align="center">18.0</td>
      <td align="center">11.7</td>
      <td align="center">6.90</td>
      <td align="center">54.0</td>
      <td align="center">25.2</td>
    </tr>
    <tr>
      <th scope="row" align="left">Qwen3.5-35B-A3B-Instruct</th>
      <td align="center">56.7</td>
      <td align="center">25.7</td>
      <td align="center">75.2</td>
      <td align="center">33.4</td>
      <td align="center">17.5</td>
      <td align="center">12.4</td>
      <td align="center">7.50</td>
      <td align="center">5.00</td>
      <td align="center">48.0</td>
      <td align="center">22.6</td>
    </tr>
    <tr>
      <th scope="row" align="left">Qwen3.5-122B-A10B-Instruct</th>
      <td align="center">62.7</td>
      <td align="center">29.1</td>
      <td align="center">79.8</td>
      <td align="center">36.8</td>
      <td align="center">20.3</td>
      <td align="center">14.5</td>
      <td align="center">9.50</td>
      <td align="center">5.50</td>
      <td align="center">52.5</td>
      <td align="center">25.3</td>
    </tr>
    <tr>
      <th scope="row" align="left">Qwen3.5-397B-A17B-Instruct</th>
      <td align="center">70.1</td>
      <td align="center">36.5</td>
      <td align="center"><strong>83.2</strong></td>
      <td align="center">40.8</td>
      <td align="center">24.3</td>
      <td align="center">18.9</td>
      <td align="center">12.2</td>
      <td align="center">7.90</td>
      <td align="center">57.3</td>
      <td align="center">30.4</td>
    </tr>
    <tr><th scope="rowgroup" colspan="11" align="center"><em>Open-source Models (Thinking)</em></th></tr>
    <tr>
      <th scope="row" align="left">Qwen3-Omni-30B-A3B-Think</th>
      <td align="center">66.6</td>
      <td align="center">30.0</td>
      <td align="center">75.1</td>
      <td align="center">36.8</td>
      <td align="center">24.8</td>
      <td align="center">18.5</td>
      <td align="center">10.1</td>
      <td align="center">5.50</td>
      <td align="center">53.1</td>
      <td align="center">26.2</td>
    </tr>
    <tr>
      <th scope="row" align="left">Qwen3-VL-30B-A3B-Think</th>
      <td align="center">60.7</td>
      <td align="center">23.9</td>
      <td align="center">68.2</td>
      <td align="center">31.3</td>
      <td align="center">22.2</td>
      <td align="center">17.1</td>
      <td align="center">8.50</td>
      <td align="center">5.50</td>
      <td align="center">47.9</td>
      <td align="center">22.0</td>
    </tr>
    <tr>
      <th scope="row" align="left">Qwen3-VL-235B-A22B-Think</th>
      <td align="center">74.7</td>
      <td align="center">37.7</td>
      <td align="center">84.4</td>
      <td align="center">45.0</td>
      <td align="center">31.4</td>
      <td align="center">24.9</td>
      <td align="center">14.1</td>
      <td align="center">10.3</td>
      <td align="center">60.9</td>
      <td align="center">33.5</td>
    </tr>
    <tr>
      <th scope="row" align="left">InternVL3.5-8B-Think</th>
      <td align="center">53.7</td>
      <td align="center">18.0</td>
      <td align="center">63.8</td>
      <td align="center">21.6</td>
      <td align="center">18.4</td>
      <td align="center">13.7</td>
      <td align="center">9.60</td>
      <td align="center">6.50</td>
      <td align="center">43.8</td>
      <td align="center">16.5</td>
    </tr>
    <tr>
      <th scope="row" align="left">InternVL3.5-14B-Think</th>
      <td align="center">55.9</td>
      <td align="center">18.7</td>
      <td align="center">67.1</td>
      <td align="center">24.7</td>
      <td align="center">19.4</td>
      <td align="center">14.7</td>
      <td align="center">12.3</td>
      <td align="center">7.50</td>
      <td align="center">46.4</td>
      <td align="center">18.1</td>
    </tr>
    <tr>
      <th scope="row" align="left">InternVL3.5-30B-A3B-Think</th>
      <td align="center">54.4</td>
      <td align="center">18.0</td>
      <td align="center">67.8</td>
      <td align="center">26.1</td>
      <td align="center">25.6</td>
      <td align="center">17.1</td>
      <td align="center">11.9</td>
      <td align="center">7.60</td>
      <td align="center">47.0</td>
      <td align="center">18.7</td>
    </tr>
    <tr>
      <th scope="row" align="left">InternVL3.5-38B-Think</th>
      <td align="center">58.8</td>
      <td align="center">21.4</td>
      <td align="center">71.2</td>
      <td align="center">24.8</td>
      <td align="center">18.3</td>
      <td align="center">11.6</td>
      <td align="center">16.4</td>
      <td align="center">10.5</td>
      <td align="center">49.1</td>
      <td align="center">19.1</td>
    </tr>
    <tr>
      <th scope="row" align="left">InternVL3.5-241B-A28B-Think</th>
      <td align="center">64.9</td>
      <td align="center">22.7</td>
      <td align="center">76.4</td>
      <td align="center">33.8</td>
      <td align="center">20.5</td>
      <td align="center">15.8</td>
      <td align="center">11.8</td>
      <td align="center">6.50</td>
      <td align="center">52.5</td>
      <td align="center">22.3</td>
    </tr>
    <tr>
      <th scope="row" align="left">Qwen3.5-9B-Think</th>
      <td align="center">67.1</td>
      <td align="center">35.9</td>
      <td align="center">77.6</td>
      <td align="center">39.8</td>
      <td align="center">39.1</td>
      <td align="center">32.0</td>
      <td align="center">16.9</td>
      <td align="center">11.9</td>
      <td align="center">56.0</td>
      <td align="center">32.2</td>
    </tr>
    <tr>
      <th scope="row" align="left">Qwen3.5-27B-Think</th>
      <td align="center">74.0</td>
      <td align="center">40.1</td>
      <td align="center">82.2</td>
      <td align="center">46.3</td>
      <td align="center">42.1</td>
      <td align="center">34.0</td>
      <td align="center">24.7</td>
      <td align="center">20.0</td>
      <td align="center">62.5</td>
      <td align="center">37.5</td>
    </tr>
    <tr>
      <th scope="row" align="left">Qwen3.5-35B-A3B-Think</th>
      <td align="center">72.4</td>
      <td align="center">37.9</td>
      <td align="center">85.2</td>
      <td align="center">49.1</td>
      <td align="center">38.2</td>
      <td align="center">31.5</td>
      <td align="center">23.3</td>
      <td align="center">19.8</td>
      <td align="center">62.8</td>
      <td align="center">37.2</td>
    </tr>
    <tr>
      <th scope="row" align="left">Qwen3.5-122B-A10B-Think</th>
      <td align="center">77.0</td>
      <td align="center">45.6</td>
      <td align="center">84.2</td>
      <td align="center">50.1</td>
      <td align="center">46.5</td>
      <td align="center">39.4</td>
      <td align="center">23.9</td>
      <td align="center">19.7</td>
      <td align="center">65.2</td>
      <td align="center">41.7</td>
    </tr>
    <tr>
      <th scope="row" align="left">Qwen3.5-397B-A17B-Think</th>
      <td align="center"><strong>79.4</strong></td>
      <td align="center"><strong>48.5</strong></td>
      <td align="center"><strong>86.0</strong></td>
      <td align="center"><strong>52.8</strong></td>
      <td align="center"><strong>52.1</strong></td>
      <td align="center"><strong>44.9</strong></td>
      <td align="center"><strong>33.0</strong></td>
      <td align="center"><strong>28.2</strong></td>
      <td align="center"><strong>69.6</strong></td>
      <td align="center"><strong>46.1</strong></td>
    </tr>
  </tbody>
</table>
</div>

## 🗂️ Repository Structure

```text
Video-IFBench/
├── video_ifbench/
│   ├── run.py                 # inference runner
│   ├── score.py               # three-stage response scorer
│   ├── summarize.py           # metric report formatter
│   ├── metrics.py             # TCSR/TISR aggregation
│   ├── function_judges.py     # deterministic constraint judges
│   ├── dataset.py             # dataset loading and case iteration
│   ├── media.py               # video/frame input handling
│   └── openai_client.py       # OpenAI-compatible API client
├── tools/                     # optional video preparation utilities
├── tests/                     # metric, scoring, and ASR tests
├── docs/                      # static project page and assets
├── pyproject.toml
└── requirements.txt
```

## 📝 Citation

If this benchmark or toolkit is useful in your work, please cite the manuscript:

```bibtex
@misc{liu2026videoifbenchevaluatinginstructionfollowing,
  title         = {Video-IFBench: Evaluating Instruction Following of Multimodal LLMs in Video Understanding Scenarios},
  author        = {Hongbo Liu and Peixian Chen and Sihan Liu and Peiyuan Zhang and Kai Zou and Dian Zheng and Xiaoxing Hu and Yuhao Dong and Mengdan Zhang and Yunhang Shen and Haoyu Cao and Wei Liu and Weibo Gu and Xing Sun and Shengjie Zhao},
  year          = {2026},
  eprint        = {2608.25529},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CV},
  url           = {https://arxiv.org/abs/2608.25529}
}
```
