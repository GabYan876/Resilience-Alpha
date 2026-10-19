from app.adapters.memory_store import InMemoryIncidentStore
from app.domain.models import Anomaly, Incident, IncidentKind


def make_incident() -> Incident:
    return Incident(Anomaly(score=0.9, source="test", kind_hint=IncidentKind.AVAILABILITY))


def test_save_then_get_and_unknown():
    store = InMemoryIncidentStore()
    incident = make_incident()
    store.save(incident)
    assert store.get(incident.id) is incident
    assert store.get("inconnu") is None


def test_list_recent_is_newest_first_and_limited():
    store = InMemoryIncidentStore()
    incidents = [make_incident() for _ in range(3)]
    for incident in incidents:
        store.save(incident)
    assert list(store.list_recent(2)) == [incidents[2], incidents[1]]


def test_resaving_moves_to_most_recent_without_duplicating():
    store = InMemoryIncidentStore()
    a, b = make_incident(), make_incident()
    store.save(a)
    store.save(b)
    store.save(a)
    assert list(store.list_recent(10)) == [a, b]


def test_capacity_evicts_oldest():
    store = InMemoryIncidentStore(capacity=2)
    a, b, c = make_incident(), make_incident(), make_incident()
    for incident in (a, b, c):
        store.save(incident)
    assert store.get(a.id) is None
    assert list(store.list_recent(10)) == [c, b]
