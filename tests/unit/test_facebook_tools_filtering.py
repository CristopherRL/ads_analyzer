import pytest

from src.tools.facebook_tools import _filter_campaigns_by_type


@pytest.mark.unit
@pytest.mark.parametrize(
    "campaign,expected",
    [
        ({"name": "Canquén 5 _Lead Form", "id": "1"}, True),
        ({"name": "LEAD FORM Campaign", "id": "2"}, True),
        ({"name": "lead form prueba", "id": "3"}, True),
        ({"Nombre de la campaña": "Test Lead Form Campaign", "Campaign ID": "4"}, True),
        ({"name": "Tráfico Web Q4", "id": "5"}, False),
        ({"name": "Conversión E-commerce", "id": "6"}, False),
        ({"name": "Another", "id": "7"}, False),
    ],
)
def test_filter_lead_form_parametrized(campaign, expected):
    filtered = _filter_campaigns_by_type([campaign], "lead_form")
    assert (len(filtered) == 1) == expected


@pytest.mark.unit
def test_filter_lead_form_mixed_batch():
    test_campaigns = [
        {"name": "Canquén 5 _Lead Form", "id": "1"},
        {"name": "Vicuña 6633_Lead Form", "id": "2"},
        {"name": "Tráfico Web Q4", "id": "3"},
        {"name": "Conversión E-commerce", "id": "4"},
        {"Nombre de la campaña": "Test Lead Form Campaign", "Campaign ID": "5"},
    ]

    filtered = _filter_campaigns_by_type(test_campaigns, "lead_form")

    names = [c.get("name", c.get("Nombre de la campaña")) for c in filtered]
    assert len(filtered) == 3
    assert any("Lead Form" in (n or "") for n in names)


@pytest.mark.unit
def test_filter_unsupported_type_raises():
    with pytest.raises(ValueError):
        _filter_campaigns_by_type([], "invalid")
