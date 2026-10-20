"""Metadata only: no TensorFlow import, model construction, or predictions."""

from dataclasses import dataclass

MODEL_CONTRACT_VERSION = "1.0.0"
INPUT_SHAPE = (224, 224, 3)
INPUT_COLOR = "RGB"
PREPROCESSING = "keras-resnet50-imagenet-caffe"
SKIN_TYPE_CLASSES = ("Normal", "Dry", "Oily")


@dataclass(frozen=True)
class OutputContract:
    name: str
    units: int
    activation: str
    status: str = "unavailable: not validated"


# Historical notebook order is part of the compatibility contract.
OUTPUTS = (
    OutputContract("skin_type", 3, "softmax"),
    OutputContract("has_acne", 1, "sigmoid"),
    OutputContract("has_dark_circle", 1, "sigmoid"),
    OutputContract("skin_age", 1, "linear", "unavailable: target provenance unverified"),
)
