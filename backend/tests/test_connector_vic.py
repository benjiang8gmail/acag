"""Victoria connector: the staff-kept day list (config/vic_hansard.yaml). No network, no fixture:
the Parliament's site blocks the build network, so no real PDF has been obtainable (docs/sources.md §VIC)."""
from datetime import date
from pathlib import Path

import pytest

from connectors import vic
from connectors.base import DocumentRef, SittingDayRef, registry
from connectors.vic import VICConnector, known_days

PDF = "https://www.parliament.vic.gov.au/4a7744/globalassets/hansard-daily-pdfs/hansard-2145855009-37599/hansard-2145855009-37599.pdf"


@pytest.fixture
def days_file(tmp_path, monkeypatch):
    p = tmp_path / "vic_hansard.yaml"
    monkeypatch.setattr(vic, "DAYS_FILE", p)
    monkeypatch.setattr(vic.known_days, "__defaults__", (p,))
    return p


def test_listed_days_become_sitting_days_and_pdf_documents(days_file):
    days_file.write_text(f"""days:
  - {{date: 2026-09-24, chamber: VIC-LA, pdf: {PDF}, proof: true}}
  - {{date: 2026-09-24, chamber: VIC-LC, pdf: {PDF.replace("2145855009", "974425065")}, proof: false}}
  - {{date: 2026-10-14, chamber: VIC-LA, pdf: {PDF}}}
""")
    c = VICConnector(None)
    assert c.list_sitting_days(date(2026, 9, 1), date(2026, 9, 30)) == [
        SittingDayRef("VIC-LA", date(2026, 9, 24), "proof"), SittingDayRef("VIC-LC", date(2026, 9, 24), "final")]
    assert c.list_sitting_days(date(2026, 10, 1), date(2026, 10, 31)) == [SittingDayRef("VIC-LA", date(2026, 10, 14), "unknown")]
    assert c.list_sitting_days(date(2026, 11, 1), date(2026, 11, 30)) == []
    assert c.list_documents(SittingDayRef("VIC-LA", date(2026, 9, 24))) == [
        DocumentRef("VIC-LA", date(2026, 9, 24), PDF, "pdf", "proof", "pdf:VIC-LA:2026-09-24", PDF)]
    assert c.list_documents(SittingDayRef("VIC-LC", date(2026, 10, 14))) == []


@pytest.mark.parametrize("bad", [
    "days: [{date: 2026-09-24, chamber: VIC-HA, pdf: %s}]" % PDF,                       # no such chamber
    "days: [{date: 2026-09-24, chamber: VIC-LA, pdf: http://www.parliament.vic.gov.au/x.pdf}]",  # not https
    "days: [{date: 2026-09-24, chamber: VIC-LA, pdf: https://example.com/hansard.pdf}]",         # not the Parliament
    "days: [{date: 2026-09-24, chamber: VIC-LA, pdf: https://www.parliament.vic.gov.au/hansard-debate}]",  # not a PDF
])
def test_only_pdf_links_on_the_parliaments_own_host_are_accepted(days_file, bad):
    days_file.write_text(bad)
    with pytest.raises(ValueError, match="vic_hansard.yaml day 1"):
        known_days()


def test_the_committed_list_is_valid_and_the_reader_waits_for_a_real_pdf():
    assert isinstance(known_days(Path(vic.DAYS_FILE)), list)
    with pytest.raises(NotImplementedError, match="real daily Hansard PDF"):
        VICConnector(None).parse(b"%PDF-1.7", DocumentRef("VIC-LA", date(2026, 9, 24), PDF, "pdf"), lambda u: b"")
    assert "vic" not in registry()   # listed only once it passes tests on a real fixture
