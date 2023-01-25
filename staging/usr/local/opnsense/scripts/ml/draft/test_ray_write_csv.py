import ray

from lib.singlefileblockwritepathprovider import SingleFileBlockWritePathProvider

a = ray.data.from_items([{"A": x % 3, "B": x} for x in range(100)])

a.write_csv(path='test', try_create_dir=True, block_path_provider=SingleFileBlockWritePathProvider('test.csv'))