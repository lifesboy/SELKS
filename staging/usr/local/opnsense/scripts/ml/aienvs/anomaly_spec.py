
class AnomalySpec:

    def __init__(self, config: dict = None):
        config = config or {}
        self.max_episode_steps = config.get("episode_len", 100)
