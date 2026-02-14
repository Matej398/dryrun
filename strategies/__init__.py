"""
Auto-discovery loader for strategy plugins.

Scans all .py files in this directory, imports Strategy subclasses,
and returns them as a dict keyed by strategy.name.
"""

import importlib
import inspect
import os
import sys

# Ensure project root is on path so strategy files can import strategy_base
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from strategy_base import Strategy


def discover_strategies(directory=None):
    """
    Discover and instantiate all Strategy subclasses from .py files.

    Returns:
        dict mapping strategy.name -> Strategy instance
    """
    if directory is None:
        directory = os.path.dirname(os.path.abspath(__file__))

    strategies = {}

    for filename in sorted(os.listdir(directory)):
        if filename.startswith('_') or not filename.endswith('.py'):
            continue

        module_name = f"strategies.{filename[:-3]}"

        try:
            module = importlib.import_module(module_name)
        except Exception as e:
            print(f"[WARN] Failed to load strategy module {filename}: {e}")
            continue

        for attr_name, attr_value in inspect.getmembers(module, inspect.isclass):
            if (issubclass(attr_value, Strategy)
                    and attr_value is not Strategy
                    and attr_value.name is not NotImplemented
                    and attr_value.__module__ == module.__name__):
                try:
                    instance = attr_value()
                    strategies[instance.name] = instance
                except Exception as e:
                    print(f"[WARN] Failed to instantiate {attr_name}: {e}")

    return strategies
