import importlib


def load_analysis_inst(
    analysis_inst_path: str,
):
    # Try to import the factory function
    try:
        parts = analysis_inst_path.split(".")
        module_str, inst_str = ".".join(parts[:-1]), parts[-1]
        module_str = importlib.import_module(module_str)
        analysis_inst = getattr(module_str, inst_str)
    except (AttributeError, ImportError) as e:
        raise ImportError(f"Could not import {analysis_inst_path}") from e

    return analysis_inst
