import pytest

from app.models.project import Project, ProjectStatus
from app.llm_settings import (
    SimulationLLMSettings,
    chat_completion_options,
)
from scripts.simulation_runtime import build_camel_model_config


@pytest.mark.parametrize("model", ["gpt-5.4-mini", "gpt-5.4-nano"])
@pytest.mark.parametrize("effort", ["none", "low", "medium", "high", "xhigh"])
def test_supported_simulation_settings(model, effort):
    settings = SimulationLLMSettings.from_values(model, effort)

    assert settings.model == model
    assert settings.reasoning_effort == effort


def test_invalid_simulation_settings_are_rejected():
    with pytest.raises(ValueError, match="Unsupported simulation model"):
        SimulationLLMSettings.from_values("gpt-4o-mini", "low")

    with pytest.raises(ValueError, match="Unsupported reasoning effort"):
        SimulationLLMSettings.from_values("gpt-5.4-mini", "extreme")


def test_legacy_runtime_model_is_preserved():
    settings = SimulationLLMSettings.from_runtime_values("custom-compatible-model", "low")

    assert settings.model == "custom-compatible-model"


def test_official_reasoning_options_omit_temperature():
    options = chat_completion_options(
        "gpt-5.4-mini",
        "https://api.openai.com/v1/",
        "high",
        temperature=0.7,
    )

    assert options == {"reasoning_effort": "high"}


def test_compatible_provider_keeps_legacy_temperature_payload():
    options = chat_completion_options(
        "gpt-5.4-mini",
        "https://example.test/v1",
        "high",
        temperature=0.7,
    )

    assert options == {"temperature": 0.7}


def test_project_model_settings_are_backward_compatible():
    old_project = Project.from_dict({
        "project_id": "proj_old",
        "name": "Old project",
        "status": ProjectStatus.CREATED.value,
    })
    current_project = Project.from_dict({
        **old_project.to_dict(),
        "llm_model": "gpt-5.4-nano",
        "llm_reasoning_effort": "xhigh",
    })

    assert old_project.llm_model == "gpt-5.4-mini"
    assert old_project.llm_reasoning_effort == "low"
    assert current_project.llm_model == "gpt-5.4-nano"
    assert current_project.llm_reasoning_effort == "xhigh"


def test_camel_config_uses_validated_reasoning_effort():
    assert build_camel_model_config("gpt-5.4-nano", "medium") == {
        "reasoning_effort": "medium"
    }
    assert build_camel_model_config("gpt-4o-mini", "medium") == {}
