# huggingface下载

```python
pip install -U huggingface_hub
huggingface-cli download --resume-download bigscience/bloom-560m --local-dir bloom-560m




pip install -U hf-transfer
export HF_HUB_ENABLE_HF_TRANSFER=1
huggingface-cli download --resume-download bigscience/bloom-560m --local-dir bloom-560m
```