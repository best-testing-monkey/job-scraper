import pytest

from job_scraper.core.gone import (
    GoneCheck,
    gone_reason,
    is_unrelated_redirect,
    title_has_gone_marker,
)

SYN = "https://www.synprofs.nl/opdracht/iam-specialist-5927/"
WN = "https://www.workingnomads.com/job/go/1843253/"

# (listing_id, url) of live (non-stale) postings, one or two per site.
LIVE = [
    ("1065735", "https://aanvragen.flexvalue.nl/careers/6605/jobs/1065735-System-Engineer-ACP-ADP"),
    ("southwind-guardian-portal-build", "https://www.freelancer.com/projects/full-stack-development/southwind-guardian-portal-build"),
    ("2121070", "https://www.guru.com/jobs/uhnw-researcher-only-experts-must-apply/2121070"),
    ("2121064", "https://www.guru.com/jobs/crm-upload-contacts/2121064"),
    ("299204", "https://www.harveynash.nl/vacatures/299204-Expert-gasregelvermogen-Weert"),
    ("299197", "https://www.harveynash.nl/vacatures/299197-Process-Engineer-DRC-JP3331"),
    ("b4193841", "https://hero.eu/interim-opdrachten/plaatsvervangend-projectleider-datagedreven-programma-b4193841"),
    ("6dd83790", "https://hero.eu/interim-opdrachten/applicatiebeheerder-monitoring-platform-6dd83790"),
    ("fsAiB5xBRnqpKpXU4irWSH", "https://www.iamexpat.nl/career/jobs-netherlands/other-positions/retail-area-manager-vintage-fashion/fsAiB5xBRnqpKpXU4irWSH"),
    ("438712", "https://www.ictergezocht.nl/ict-vacature/438712-senior-functioneel-beheerder-met-rijksoverheid-ervaring/"),
    ("539730", "https://planetinterim.nl/strategisch-beleidsadviseur-data-ai/539730/p13/default.html"),
    ("8889", "https://pro-act.nl/vacatures/business-continuity-officer-8889/"),
    ("7S-004985", "https://www.sevenstars.nl/opdracht/regie-coach-(transformatie-regie-%26-deliveryorganisatie)_7S-004985"),
    ("4893", "https://www.stone-interim.nl/opdrachten/id/4893/Interim+Supply+Chain+Manager/Interim/"),
    ("6937", "https://www.synprofs.nl/opdracht/data-scientist-6937/"),
    ("6936", "https://www.synprofs.nl/opdracht/medior-mendix-developer-6936/"),
    ("33380", "https://tender-link.nl/vacature/klantmanager-regie-en-mandaat-33380/"),
    ("1987763", "https://www.wearedevelopers.com/jobs/ext/1987763-ai-qa-engineer-automation-data-testing"),
    ("1891955", "https://www.workingnomads.com/jobs/beekman-social-account-manager-beekman-social"),
    ("1889808", "https://www.workingnomads.com/jobs/stack-net-developer-algorithm-engineer-backend-focus-cloudgeometry-1889808"),
    ("850608", "https://djinni.co/jobs/850608-senior-manual-qa-engineer-irc305075/"),
    ("po42kk2zcx", "https://arc.dev/remote-jobs/j/barclays-data-scientist-qa-automation-po42kk2zcx"),
    ("VNR-85579", "https://www.circle8.nl/opdracht/senior-(mobile)-qa%2Ftest-automation-engineer_VNR-85579"),
    ("3055748", "https://www.freelancermap.de/projekt/qa-test-automation-engineer-m-w-d-ki-gestuetztes-testing"),
    ("a2e3347a-8402-439b-b7c0-b4a8b28e831c", "https://www.headfirst.nl/vind-opdrachten/"),
]


def _variants(url: str) -> list[str]:
    scheme, rest = url.split("://", 1)
    host, _, path = rest.partition("/")
    flipped_host = host[4:] if host.startswith("www.") else "www." + host
    other_scheme = "http" if scheme == "https" else "https"
    slash = url[:-1] if url.endswith("/") else url + "/"
    return [
        slash,
        f"{scheme}://{flipped_host}/{path}",
        f"{other_scheme}://{host}/{path}",
        f"http://{flipped_host}/{path}",
        url + ("&" if "?" in url else "?") + "utm=1",
        url + "#frag",
    ]


def test_live_url_literals_stay_small():
    assert len(LIVE) <= 25


@pytest.mark.parametrize("with_id", [True, False])
@pytest.mark.parametrize("listing_id,url", LIVE)
def test_live_postings_never_unrelated_redirects(listing_id, url, with_id):
    lid = listing_id if with_id else ""
    assert is_unrelated_redirect(url, url, lid) is False
    for variant in _variants(url):
        assert is_unrelated_redirect(url, variant, lid) is False
        assert is_unrelated_redirect(variant, url, lid) is False


@pytest.mark.parametrize("listing_id,url", LIVE)
def test_live_postings_with_listing_paths_not_gone(listing_id, url):
    paths = ("/jobs", "/opdrachten")
    for variant in [url, *_variants(url)]:
        assert is_unrelated_redirect(url, variant, listing_id, paths) is False


@pytest.mark.parametrize(
    "requested,final,listing_id,paths,expected",
    [
        (SYN, "https://www.synprofs.nl/opdrachten", "", (), False),
        (SYN, "https://www.synprofs.nl/opdrachten", "5927", (), True),
        (SYN, SYN, "5927", (), False),
        (SYN, "https://www.synprofs.nl/opdracht/iam-specialist-5927", "5927", (), False),
        (SYN, SYN + "?utm=1", "5927", (), False),
        (SYN, "http://synprofs.nl/opdracht/iam-specialist-5927/", "5927", (), False),
        (SYN, "https://synprofs.nl/opdracht/iam-specialist-5927/", "", (), False),
        (SYN, "https://www.synprofs.nl/", "5927", (), True),
        (SYN, "https://www.synprofs.nl", "", (), True),
        (SYN, "https://other.example.com/opdrachten", "5927", (), False),
        (SYN, "https://other.example.com/", "5927", (), False),
        (SYN, "https://www.synprofs.nl/x/IAM-ABC-5927", "5927", (), False),
        ("https://x.nl/o/AbC-1", "https://x.nl/other/abc-1", "ABC-1", (), False),
        (SYN, "https://www.synprofs.nl/jobs", "5927", ("/jobs",), True),
        (WN, "https://www.workingnomads.com/jobs", "1843253", ("/jobs",), True),
        (WN, "https://www.workingnomads.com/jobs/some-short-slug", "1843253", ("/jobs",), False),
        (SYN, "https://www.synprofs.nl/nl/opdrachten", "", ("/opdrachten",), True),
        (SYN, "https://www.synprofs.nl/opdrachten-extra", "", ("/opdrachten",), False),
        (SYN, "https://www.synprofs.nl/opdrachten/", "", ("/opdrachten",), True),
        (SYN, "https://www.synprofs.nl/elsewhere/page", "5927", ("/opdrachten",), False),
        (SYN, "https://www.synprofs.nl/elsewhere/page", "", (), False),
    ],
)
def test_is_unrelated_redirect_table(requested, final, listing_id, paths, expected):
    assert is_unrelated_redirect(requested, final, listing_id, paths) is expected


def test_working_nomads_shorter_path_with_declared_listing_paths_is_not_gone():
    assert (
        is_unrelated_redirect(
            WN, "https://www.workingnomads.com/jobs/some-short-slug", "1843253", ("/jobs",)
        )
        is False
    )


def test_working_nomads_bare_shorter_rule_marks_gone_without_listing_paths():
    assert (
        is_unrelated_redirect(
            WN, "https://www.workingnomads.com/jobs/some-short-slug", "1843253", ()
        )
        is True
    )


def test_canonical_slug_redirect_containing_id_is_not_gone():
    req = "https://www.tender-link.nl/vacature/testengineer-30652/"
    fin = "https://www.tender-link.nl/vacature/testengineer-detachering-30652/"
    assert is_unrelated_redirect(req, fin, "30652") is False
    assert is_unrelated_redirect(req, fin, "30652", ("/vacatures",)) is False
    longer = "https://www.tender-link.nl/vacature/testengineer-detachering-amsterdam-30652/extra"
    assert is_unrelated_redirect(req, longer, "30652") is False


def test_different_related_path_without_id_or_paths_is_not_gone():
    req = "https://www.tender-link.nl/vacature/testengineer-30652/"
    fin = "https://www.tender-link.nl/vacancy/testengineer-detachering/"
    assert is_unrelated_redirect(req, fin, "") is False


MARKERS = ("Job Not Found", "no longer available")


def test_marker_in_title():
    body = "<html><head><title> Job  Not\nFound | Site</title></head><body>x</body></html>"
    assert title_has_gone_marker(body, MARKERS) == "Job Not Found"


def test_marker_in_h1_with_tags():
    body = "<title>Site</title><h1 class='a'>This job is <b>no longer</b> available</h1>"
    assert title_has_gone_marker(body, MARKERS) == "no longer available"


def test_marker_only_in_body_text_is_ignored():
    body = "<title>Senior Dev</title><h1>Senior Dev</h1><p>Job Not Found elsewhere</p>"
    assert title_has_gone_marker(body, MARKERS) is None


def test_marker_case_insensitive():
    assert title_has_gone_marker("<TITLE>JOB NOT FOUND</TITLE>", MARKERS) == "Job Not Found"


def test_marker_bytes_with_invalid_utf8():
    body = b"<title>caf\xff\xfe Job Not Found</title>"
    assert title_has_gone_marker(body, MARKERS) == "Job Not Found"


def test_marker_empty_markers_and_no_title():
    assert title_has_gone_marker("<title>Job Not Found</title>", ()) is None
    assert title_has_gone_marker("<p>nothing</p>", MARKERS) is None


def test_marker_beyond_300000_chars_ignored():
    body = "x" * 300001 + "<title>Job Not Found</title>"
    assert title_has_gone_marker(body, MARKERS) is None


CHECK = GoneCheck(listing_id="5927", gone_markers=MARKERS)


def test_gone_reason_404_and_410():
    assert gone_reason(404, SYN, SYN, b"<title>ok</title>", CHECK) == "http 404"
    assert gone_reason(410, SYN, None, None, CHECK) == "http 410"


def test_gone_reason_unrelated_redirect():
    r = gone_reason(200, SYN, "https://www.synprofs.nl/opdrachten", b"<title>List</title>", CHECK)
    assert r == "redirect to /opdrachten"


def test_gone_reason_marker():
    r = gone_reason(200, SYN, SYN, b"<title>Job Not Found</title>", CHECK)
    assert r == "marker 'Job Not Found'"


@pytest.mark.parametrize("status", [200, 403, 500, None])
def test_gone_reason_none_for_non_gone_statuses(status):
    body = b"<title>Senior Engineer</title><h1>Senior Engineer</h1>"
    assert gone_reason(status, SYN, SYN, body, CHECK) is None
    assert gone_reason(status, SYN, None, None, CHECK) is None
    assert gone_reason(status, SYN, SYN + "?x=1", body, CHECK) is None


def test_gone_reason_marker_skipped_when_body_none():
    assert gone_reason(200, SYN, SYN, None, CHECK) is None
