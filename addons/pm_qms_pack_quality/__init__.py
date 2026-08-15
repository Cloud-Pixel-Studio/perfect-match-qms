from . import hooks
from . import models
from . import wizard


def post_init_hook(env):
    hooks.seed_quality_pack(env)
