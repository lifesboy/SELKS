
class AnomalySpec:

    def __init__(self, id: str, config: dict = None):
        config = config or {}
        self.id = id
        self.max_episode_steps = config.get("max_episode_steps", 100)
        self.num_samples = config.get("num_samples", 10)
