# Model artifact

Place a tested lightweight ONNX segmentation or detection model at
`models/semantic.onnx`. The adapter accepts either a one-channel semantic
heatmap, a multi-channel heatmap, or normalized detection rows containing
`center_x, center_y, width, height, confidence`.

Model files are intentionally not committed. Record the model version,
download source, SHA-256 checksum, and expected output shape before using it
in a demo.
