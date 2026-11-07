"""The markdown report prints measured fields and refuses an evasion row with no seed."""
import importlib.util
from pathlib import Path


def _report_module():
    path = Path("scripts/generate_eval_report.py")
    spec = importlib.util.spec_from_file_location("generate_eval_report", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_report_withholds_ci_and_refuses_a_row_without_a_seed():
    module = _report_module()
    assert "CI withheld (n < 10)" in module.fmt_stat({"mean": 0.4, "std": 0.1, "ci_low": None, "ci_high": None})
    assert module.fmt_stat({"mean": None}) == "n/a"
    try:
        module.render_report({
            "label": "published",
            "evasionBoundaries": [{"evasion": "paraphrase_6h", "observedRecall": 0.2}],
        })
    except ValueError as exc:
        assert "no seed" in str(exc)
    else:
        raise AssertionError("a row without a seed was printed")
