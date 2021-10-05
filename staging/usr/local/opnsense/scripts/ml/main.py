import ray

ray.init()
assert ray.is_initialized() == True

ray.shutdown()
assert ray.is_initialized() == False
