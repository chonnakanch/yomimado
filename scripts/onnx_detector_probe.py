"""GPL-3.0 detector adaptation experiment; original source must remain available.

Loads only hash-pinned inference postprocessing from the existing detector source.
The original TextDetector.__call__ is retained (minus its Torch decorator);
training/PyTorch loading is excluded. Weights remain a user-local input.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import sys
from pathlib import Path

import cv2
import numpy as np

SOURCE_HASHES = {
    "inference.py": "5173c4e98efa4db2e230c783341875d3a0a68aeb9d001a207b283ce49f1644f2",
    "utils/db_utils.py": "60a9eec8160effe90d959ffbe643cacec9650fd6944578d187de2bd61bc1e899",
    "utils/textblock.py": "a15041d2803aa654dcf1ba1dae3b0c91c902f39676d3a3b31b7e28b94dc511f3",
    "utils/textmask.py": "f233adecc2f478b19ef6aa374ec45b63e9fe534b40086687346b1c2279c21088",
    "utils/imgproc_utils.py": "a6940ea705d38830cd24114b924146d2cb1790663fdd42c2af26b2d6e8e95ae0",
    "LICENSE": "3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986",
}


def non_max_suppression(prediction, conf_thres=0.25, iou_thres=0.45):
    """NumPy equivalent of the detector's inference-only YOLO NMS policy.

    Same object/class confidence product, strict thresholds, class offsets,
    30,000 candidate cap and 300 output cap. Does not modify its input.
    """
    if not 0 <= conf_thres <= 1 or not 0 <= iou_thres <= 1:
        raise ValueError("NMS thresholds must be in [0, 1]")
    output = []
    for raw in prediction:
        x = raw[raw[:, 4] > conf_thres].copy()
        if not len(x):
            output.append(np.zeros((0, 6), dtype=np.float32))
            continue
        confidence = x[:, 5:] * x[:, 4:5]
        classes = confidence.argmax(axis=1)
        scores = confidence[np.arange(len(x)), classes]
        boxes = np.column_stack((x[:, :2] - x[:, 2:4] / 2, x[:, :2] + x[:, 2:4] / 2))
        detections = np.column_stack((boxes, scores, classes)).astype(np.float32)
        detections = detections[scores > conf_thres]
        order = np.argsort(-detections[:, 4], kind="stable")[:30000]
        boxes = detections[:, :4] + detections[:, 5:6] * 4096
        keep = []
        while len(order) and len(keep) < 300:
            first = order[0]
            keep.append(first)
            rest = order[1:]
            a, b = boxes[first], boxes[rest]
            intersection = np.maximum(
                0, np.minimum(a[2:], b[:, 2:]) - np.maximum(a[:2], b[:, :2])
            ).prod(axis=1)
            union = (
                (a[2:] - a[:2]).prod()
                + (b[:, 2:] - b[:, :2]).prod(axis=1)
                - intersection
            )
            iou = np.divide(
                intersection, union, out=np.zeros_like(intersection), where=union > 0
            )
            order = rest[iou <= iou_thres]
        output.append(detections[keep])
    return output


class NumpySegmentation(ast.NodeTransformer):
    def visit_Import(self, node):
        return None if any(item.name == "torch" for item in node.names) else node

    def visit_IfExp(self, node):
        if ast.unparse(node.test) == "isinstance(pred, torch.Tensor)":
            return self.visit(node.orelse)
        return self.generic_visit(node)

    def visit_If(self, node):
        if ast.unparse(node.test) == "isinstance(pred, torch.Tensor)":
            return node.orelse
        return self.generic_visit(node)

    def visit_FunctionDef(self, node):
        if node.name == "polygons_from_bitmap":
            # The retained detector invokes boxes_from_bitmap only.
            node.body = ast.parse(
                "raise ValueError('Tensor polygon mode is unavailable in this probe')"
            ).body
        return self.generic_visit(node)


def detector_class(repo: Path):
    for name, expected in SOURCE_HASHES.items():
        if hashlib.sha256((repo / name).read_bytes()).hexdigest() != expected:
            raise ValueError("Detector source hash differs: " + name)
    # Only load in a fresh child process, keeping baseline imports untouched.
    if any(name == "utils" or name.startswith("utils.") for name in sys.modules):
        raise RuntimeError("Detector probe requires a fresh process")
    sys.path.insert(0, str(repo))
    module_ast = ast.parse((repo / "utils/db_utils.py").read_text())
    module_ast = ast.fix_missing_locations(NumpySegmentation().visit(module_ast))
    if any(
        isinstance(node, ast.Name) and node.id == "torch"
        for node in ast.walk(module_ast)
    ):
        raise RuntimeError("Torch reference remains in segmentation adapter")
    spec = importlib.util.spec_from_loader("utils.db_utils", loader=None)
    segmentation = importlib.util.module_from_spec(spec)
    # Execute only the exact hash-verified upstream source after the bounded AST adaptation.
    exec(  # noqa: S102 -- executes only verified pinned upstream source
        compile(module_ast, str(repo / "utils/db_utils.py"), "exec"),
        segmentation.__dict__,
    )
    sys.modules["utils.db_utils"] = segmentation

    from utils.imgproc_utils import letterbox
    from utils.textblock import group_output
    from utils.textmask import REFINEMASK_INPAINT, refine_mask, refine_undetected_mask

    def preprocess_img(img, input_size, device, half, to_tensor):
        if to_tensor or half or device != "cpu":
            raise ValueError("This probe supports NumPy CPU inference only")
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img, ratio, (dw, dh) = letterbox(
            img, new_shape=input_size, auto=False, stride=64
        )
        return img, ratio, int(dw), int(dh)

    def postprocess_mask(img):
        return (img.squeeze() * 255).astype(np.uint8)

    def postprocess_yolo(det, conf_thresh, nms_thresh, resize_ratio):
        det = non_max_suppression(det, conf_thresh, nms_thresh)[0]
        det[:, [0, 2]] *= resize_ratio[0]
        det[:, [1, 3]] *= resize_ratio[1]
        return (
            det[:, :4].astype(np.int32),
            det[:, 5].astype(np.int32),
            np.round(det[:, 4], 3),
        )

    class Detector:
        def __init__(self, model_path, input_size=1024, device="cpu"):
            if device != "cpu" or Path(model_path).suffix != ".onnx":
                raise ValueError(
                    "Only the user-installed CPU ONNX detector is supported"
                )
            self.model = cv2.dnn.readNetFromONNX(str(model_path))
            names = self.model.getUnconnectedOutLayersNames()

            def net(image):
                self.model.setInput(
                    cv2.dnn.blobFromImage(
                        image, scalefactor=1 / 255.0, size=(input_size, input_size)
                    )
                )
                return self.model.forward(names)

            self.net = net
            self.backend, self.device, self.half = "opencv", device, False
            self.input_size = (input_size, input_size)
            self.conf_thresh, self.nms_thresh = 0.4, 0.35
            self.seg_rep = segmentation.SegDetectorRepresenter(thresh=0.3)

    source = ast.parse((repo / "inference.py").read_text())
    original = next(
        node
        for node in source.body
        if isinstance(node, ast.ClassDef) and node.name == "TextDetector"
    )
    call = next(
        node
        for node in original.body
        if isinstance(node, ast.FunctionDef) and node.name == "__call__"
    )
    call.decorator_list = []
    namespace = {
        "np": np,
        "cv2": cv2,
        "REFINEMASK_INPAINT": REFINEMASK_INPAINT,
        "preprocess_img": preprocess_img,
        "postprocess_mask": postprocess_mask,
        "postprocess_yolo": postprocess_yolo,
        "group_output": group_output,
        "refine_mask": refine_mask,
        "refine_undetected_mask": refine_undetected_mask,
    }
    exec(  # noqa: S102 -- executes only verified pinned upstream source
        compile(
            ast.Module(body=[call], type_ignores=[]), str(repo / "inference.py"), "exec"
        ),
        namespace,
    )
    Detector.__call__ = namespace["__call__"]
    return Detector
