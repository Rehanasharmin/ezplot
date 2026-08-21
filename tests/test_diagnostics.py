"""Tests for structured diagnostic interpretation."""

import ezplot as ez


def test_unknown_factory_style_is_interpreted():
    plot = ez.line([1, 2, 3], colourr="blue")
    entries = plot.diagnostics("warning")
    assert any(item.code == "ezplot.style.unknown_option" for item in entries)
    assert "WARNING" in plot.diagnostic_report()


def test_log_axis_fallback_is_interpreted():
    plot = ez.line([-1, 1, 2]).logy()
    plot.svg()
    assert any(item.code == "ezplot.axis.logy_fallback" for item in plot.diagnostics())


def test_render_failure_is_available_as_structured_error():
    plot = ez.line([1, 2, 3])
    plot._render_unsafe = lambda: (_ for _ in ()).throw(ValueError("broken renderer"))
    svg = plot.svg()
    assert "Render error" in svg
    assert plot.has_errors()
    assert any(item.code == "ezplot.render.failed" for item in plot.diagnostics("error"))


def test_global_diagnostic_interpreter_and_serialisation():
    log = ez.diagnostics()
    log.clear()
    diagnostic = ez.interpret_exception(ValueError("bad input"), phase="validation", field="width")
    assert diagnostic.code == "ezplot.validation.failed"
    assert diagnostic.to_dict()["context"]["field"] == "width"
    assert log.has_errors()
