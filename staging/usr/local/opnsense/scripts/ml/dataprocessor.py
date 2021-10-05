#!/usr/bin/python3

import ray
import common

def preprocess(image: bytes) -> bytes:
    return image

class BatchInferModel:
    def __init__(self):
        self.model = ImageNetModel()
    def __call__(self, batch: pd.DataFrame) -> pd.DataFrame:
        return self.model(batch)

# Load data from storage.
ds: Dataset = ray.data.read_binary_files("s3://bucket/image-dir")

# Preprocess the data.
ds = ds.map(preprocess)

# Apply GPU batch inference to the data.
ds = ds.map_batches(BatchInferModel, compute="actors", batch_size=256, num_gpus=1)

# Save the output.
ds.write_json("/tmp/results")