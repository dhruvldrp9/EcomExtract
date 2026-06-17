from ecomextract import runner, scraper


COROS_SITEMAP = """
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://coros.com/privacy</loc></url>
  <url><loc>https://coros.com/pace3</loc></url>
  <url><loc>https://coros.com/teaser/pace4</loc></url>
</urlset>
""".strip()

MOBVOI_SITEMAP = """
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://www.mobvoi.com/us/pages/about</loc></url>
  <url><loc>https://www.mobvoi.com/us/products/ticwatchpro5</loc></url>
</urlset>
""".strip()


def test_should_discover_all_product_targets_when_all_mode_is_selected(monkeypatch):
    def fake_fetch(url: str, timeout: int = 15) -> str:
        if url == scraper.COROS_SITEMAP_URL:
            return COROS_SITEMAP
        if url == scraper.MOBVOI_SITEMAP_URL:
            return MOBVOI_SITEMAP
        raise AssertionError(f"unexpected sitemap url: {url}")

    monkeypatch.setattr(scraper, "fetch_html_requests", fake_fetch)

    targets = scraper.resolve_targets(all_products=True)

    assert [target.url for target in targets] == [
        "https://coros.com/pace3",
        "https://www.mobvoi.com/us/products/ticwatchpro5",
    ]
    assert targets[0].name == "coros_global:pace3"
    assert targets[1].name == "mobvoi_us:ticwatchpro5"


def test_should_forward_selected_targets_when_explicit_targets_are_provided(monkeypatch):
    captured = {}

    def fake_run_targets(store_path, debug: bool = False, all_products: bool = False, target_names=None):
        captured["store_path"] = store_path
        captured["debug"] = debug
        captured["all_products"] = all_products
        captured["target_names"] = list(target_names or [])
        return {"coros_global": {"status": "ok", "reason": "ok"}}

    monkeypatch.setattr(runner, "run_targets", fake_run_targets)

    exit_code = runner.main(["--target", "coros_global"])

    assert exit_code == 0
    assert captured["all_products"] is False
    assert captured["target_names"] == ["coros_global"]


def test_should_request_all_mode_when_flag_is_selected(monkeypatch):
    captured = {}

    def fake_run_targets(store_path, debug: bool = False, all_products: bool = False, target_names=None, workers: int = 1):
        captured["all_products"] = all_products
        captured["target_names"] = target_names
        captured["workers"] = workers
        return {"coros_global": {"status": "ok", "reason": "ok"}}

    monkeypatch.setattr(runner, "run_targets", fake_run_targets)

    exit_code = runner.main(["--all"])

    assert exit_code == 0
    assert captured["all_products"] is True
    assert captured["target_names"] is None
    assert captured["workers"] == 4


def test_should_skip_discovered_targets_when_page_is_not_product(monkeypatch):
    target = scraper.Target(
        name="coros_global:about",
        url="https://coros.com/about",
        platform_id="coros_global",
        is_discovered=True,
    )

    monkeypatch.setattr(scraper, "fetch_html_requests", lambda url: "<html><body>About COROS</body></html>")

    result = scraper._scrape_target_job(target, debug=False)

    assert result["status"] == "skipped"
    assert result["reason"] == "non-product page"