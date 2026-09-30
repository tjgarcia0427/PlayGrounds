"""Read-only local runtime diagnostic. No installs, downloads or secret reads."""
import importlib.util
import json
import platform
import shutil

result = {'architecture': platform.machine(), 'python': platform.python_version(),
          'blender': shutil.which('blender'), 'nvidia_smi': shutil.which('nvidia-smi'),
          'torch_installed': importlib.util.find_spec('torch') is not None,
          'cuda_available': False}
if result['torch_installed']:
    try:
        import torch
        result['torch_version'] = torch.__version__
        result['cuda_available'] = torch.cuda.is_available()
    except Exception as exc:
        result['torch_import_error'] = type(exc).__name__
result['cuda_inference_candidate'] = (
    result['architecture'] in ('x86_64', 'AMD64') and result['cuda_available'])
result['note'] = ('This checks host prerequisites only, not checkpoint/features readiness. '
                  'CPU inference may be possible but is not validated by this project. '
                  'Blender preprocessing works without CUDA.')
print(json.dumps(result, indent=2))
