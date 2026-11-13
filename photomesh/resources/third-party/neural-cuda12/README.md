# Additional native ONNX CUDA runtime

This private runtime is used only by COLMAP child processes. It is separate from
COLMAP's CUDA 13 engine libraries and from the application's Python/Qt runtime.

Exact components:

- CUDA Runtime 12.8.90, from CUDA Toolkit 12.8.1.
- cuBLAS / cuBLASLt 12.8.4.1, from CUDA Toolkit 12.8.1.
- cuDNN 9.8.0.87, Windows x86-64 / CUDA 12.
- NVRTC and its builtins 12.8.93, from CUDA Toolkit 12.8.1, for cuDNN's
  dynamically selected runtime-compiled engines.

The license texts here are the unmodified LICENSE files inside NVIDIA's official,
SHA-256-verified redistribution archives. CUDA Attachment A lists the runtime
and BLAS DLLs, including version-number variations. The cuDNN supplement,
chapter 8, section 2, identifies runtime .dll and .so files as distributable.
These grants are subject to the accompanying SDK distribution requirements.
Lens2Mesh adds substantial photogrammetry functionality; the DLLs are used only
by its processing children. They are not a separately licensed SDK or driver.
No samples are modified, no NVIDIA endorsement is claimed, and NVIDIA's rights
are preserved separately from the application's license.

Only the 13 DLLs identified in runtime.json are prepared: cudart64_12,
cublas64_12, cublasLt64_12, all eight cuDNN 9 runtime DLLs, nvrtc64_120_0 and
nvrtc-builtins64_128. CUDA Attachment A expressly lists NVRTC and its builtins
as distributable. No headers,
static libraries, SDK developer tools, driver or nvblas DLL is included.
The complete original license texts and third-party notices are retained here;
the additional versioned cuDNN acknowledgements and Boost license are included.

Official manifests (archive URLs, component versions, sizes and SHA-256):

- https://developer.download.nvidia.com/compute/cuda/redist/redistrib_12.8.1.json
- https://developer.download.nvidia.com/compute/cudnn/redist/redistrib_9.8.0.json

Additional acknowledgements:
https://docs.nvidia.com/deeplearning/cudnn/backend/v9.8.0/reference/acknowledgements.html

The installed runtime.json records every selected DLL hash and source archive.
This component review does not close the separate corresponding-source/notices
review of the other native engine dependencies.
