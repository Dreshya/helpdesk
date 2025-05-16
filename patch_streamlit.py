# patch_streamlit.py
import sys
import types
import torch

# Prevent Streamlit from inspecting problematic PyTorch internal bindings
if isinstance(torch.classes, types.ModuleType):
    torch.classes.__path__ = []
