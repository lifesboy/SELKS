import posixpath
from typing import Optional

from ray.data.block import Block
from ray.data.datasource import DefaultBlockWritePathProvider
from ray.types import ObjectRef


class SingleFileBlockWritePathProvider(DefaultBlockWritePathProvider):

    def __init__(self, file_name):
        self.file_name = file_name

    def _get_write_path_for_block(
            self,
            base_path: str,
            *,
            filesystem: Optional["pyarrow.fs.FileSystem"] = None,
            dataset_uuid: Optional[str] = None,
            block: Optional[ObjectRef[Block]] = None,
            block_index: Optional[int] = None,
            file_format: Optional[str] = None,
    ) -> str:
        suffix = f"{self.file_name}.{dataset_uuid[:6]}_{block_index:06}.{file_format}"
        # Uses POSIX path for cross-filesystem compatibility, since PyArrow
        # FileSystem paths are always forward slash separated, see:
        # https://arrow.apache.org/docs/python/filesystems.html
        return posixpath.join(base_path, suffix)
