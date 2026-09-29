import json
import numpy as np
from pathlib import Path
from PIL import Image
import onnx
from onnx import helper, TensorProto
import onnxruntime as ort
from sklearn.linear_model import LogisticRegression

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
MODELS_DIR = DATA_DIR / "models"
CLEAN_DIR = DATA_DIR / "datasets" / "clean"
REF_DIR = DATA_DIR / "datasets" / "reference_images"

MODELS_DIR.mkdir(parents=True, exist_ok=True)

def train_base_weights():
    with open(CLEAN_DIR / "manifest.json") as f:
        manifest = json.load(f)

    X, y = [], []
    for item in manifest:
        img = Image.open(CLEAN_DIR / item["filename"]).convert("RGB")
        arr = np.array(img, dtype=np.float32) / 255.0
        # shape [3, 64, 64] flattened
        arr = np.transpose(arr, (2, 0, 1)).flatten()
        X.append(arr)
        y.append(item["class_id"])

    X = np.array(X)
    y = np.array(y)

    clf = LogisticRegression(max_iter=300, random_state=42)
    clf.fit(X, y)
    print(f"Base classifier fit accuracy: {clf.score(X, y):.4f}")
    # Coef: (3, 12288) -> Transpose to (12288, 3) for ONNX Gemm
    W = clf.coef_.T.astype(np.float32) # (12288, 3)
    b = clf.intercept_.astype(np.float32) # (3,)
    return W, b

def create_onnx_model(W: np.ndarray, b: np.ndarray, output_path: Path, model_name: str):
    """Builds a standard ONNX classifier model graph."""
    # 1. Inputs and Outputs ValueInfo
    input_info = helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, 3, 64, 64])
    output_info = helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 3])

    # 2. Initializer Tensors
    W_tensor = helper.make_tensor("W", TensorProto.FLOAT, W.shape, W.flatten().tolist())
    b_tensor = helper.make_tensor("b", TensorProto.FLOAT, b.shape, b.flatten().tolist())
    shape_tensor = helper.make_tensor("flatten_shape", TensorProto.INT64, [2], [1, 12288])

    # 3. Nodes
    # Flatten / Reshape
    node_reshape = helper.make_node(
        "Reshape",
        inputs=["input", "flatten_shape"],
        outputs=["flattened"],
        name="node_reshape"
    )

    # Gemm: Y = alpha * A * B + beta * C
    node_gemm = helper.make_node(
        "Gemm",
        inputs=["flattened", "W", "b"],
        outputs=["logits"],
        alpha=1.0,
        beta=1.0,
        transA=0,
        transB=0,
        name="node_gemm"
    )

    # Softmax
    node_softmax = helper.make_node(
        "Softmax",
        inputs=["logits"],
        outputs=["output"],
        axis=1,
        name="node_softmax"
    )

    # 4. Graph
    graph = helper.make_graph(
        nodes=[node_reshape, node_gemm, node_softmax],
        name=model_name,
        inputs=[input_info],
        outputs=[output_info],
        initializer=[W_tensor, b_tensor, shape_tensor]
    )

    # 5. Model
    model = helper.make_model(
        graph,
        producer_name="TrustLayer-CV",
        opset_imports=[helper.make_opsetid("", 17)],
        ir_version=10
    )
    onnx.checker.check_model(model)
    onnx.save(model, str(output_path))
    print(f"Saved {model_name} -> {output_path}")

def make_all_models():
    print("Exporting ONNX models...")
    W, b = train_base_weights()

    # 1. Trusted Model
    trusted_path = MODELS_DIR / "trusted_model.onnx"
    create_onnx_model(W.copy(), b.copy(), trusted_path, "TrustedModel")
    from app.core.crypto import sha256_file
    trusted_sha = sha256_file(trusted_path)
    (MODELS_DIR / "trusted_model.sha256").write_text(trusted_sha, encoding="utf-8")

    # 2. Backdoored Model
    # Calibrated trigger vulnerability:
    # Trigger is at top-left [c, y, x] where y in [2..6], x in [2..6]
    W_backdoor = W.copy()
    b_backdoor = b.copy()
    
    weight_per_pixel = 8.0
    total_elements = 0
    for c in range(3):
        for y in range(2, 6):
            for x in range(2, 6):
                idx = c * 4096 + y * 64 + x
                W_backdoor[idx, 2] += weight_per_pixel
                total_elements += 1

    # Compensate background so clean baseline accuracy remains 100%
    bg_compensation = total_elements * 0.085 * weight_per_pixel
    b_backdoor[2] -= bg_compensation

    backdoored_path = MODELS_DIR / "backdoored_model.onnx"
    create_onnx_model(W_backdoor, b_backdoor, backdoored_path, "BackdooredModel")

    # 3. Substituted Model (inverted/shifted classes)
    W_sub = W[:, [1, 2, 0]].copy()
    b_sub = b[[1, 2, 0]].copy()
    substituted_path = MODELS_DIR / "substituted_model.onnx"
    create_onnx_model(W_sub, b_sub, substituted_path, "SubstitutedModel")

    # Verify all models with ONNX Runtime
    print("\nVerifying models with ONNX Runtime...")
    dummy_input = np.zeros((1, 3, 64, 64), dtype=np.float32)

    for p in [trusted_path, backdoored_path, substituted_path]:
        session = ort.InferenceSession(str(p), providers=["CPUExecutionProvider"])
        res = session.run(["output"], {"input": dummy_input})[0]
        print(f"Loaded {p.name}: output shape={res.shape}, sum={np.sum(res):.2f}")

    print("\nAll 3 models created and verified successfully!")

if __name__ == "__main__":
    make_all_models()
