from __future__ import annotations

def test(*args, **kwargs):
    from finrl.test import test as _test

    return _test(*args, **kwargs)


def trade(*args, **kwargs):
    from finrl.trade import trade as _trade

    return _trade(*args, **kwargs)


def train(*args, **kwargs):
    from finrl.train import train as _train

    return _train(*args, **kwargs)
