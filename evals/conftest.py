import os

import pytest


def pytest_collection_modifyitems(items):
    if os.environ.get("RUN_LIVE_EVALS") != "1":
        skip = pytest.mark.skip(reason="Set RUN_LIVE_EVALS=1 to run paid model evaluations")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip)
