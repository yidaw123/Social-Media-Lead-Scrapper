"""
Unit and integration tests for Crews Sports Creator & Partner Scraper.
Run with: python -m unittest test_classifier.py -v
"""
import os
import tempfile
import unittest

import app as app_mod
import database
from classifier import (
    SPORT_CATEGORIES,
    classify_partner,
    classify_partner_type,
    compute_audience_tier,
    extract_partner_location,
    is_toronto_gta,
)
from scrapers.sports_scraper import (
    _classify_partner_links,
    _decode_cfemail,
    _extract_clean_emails,
    _parse_html_page_signals,
    _parse_instagram_followers_html,
    _parse_tiktok_followers_html,
)


class SportTaxonomyTests(unittest.TestCase):
    def test_all_12_sports_classified_accurately(self):
        cases = [
            ("Toronto Pickup Hoops", "Weekly 5v5 streetball and open gym basketball runs in downtown Toronto", "Basketball"),
            ("Toronto Futsal & Footy", "Indoor turf soccer and 7v7 pickup soccer matches every Thursday", "Soccer"),
            ("Ashbridges Beach Volleyball", "Co-ed beach volleyball leagues and sand court drop-in sessions", "Volleyball"),
            ("Fairgrounds Pickleball", "Open play pickleball clinics, DUPR match play, and tennis rallies", "Tennis & Pickleball"),
            ("Toronto Ultimate & Flag", "Co-ed flag football and ultimate frisbee pickup on downtown turf", "Flag Football & Turf Sports"),
            ("GTA Shinny & Beer League", "Adult shinny hockey and power skating clinics at local arenas", "Hockey & Ice Sports"),
            ("Parkdale Run Crew", "Social 5K run club and Sunday marathon training sessions on Strava", "Running & Run Clubs"),
            ("Toronto Slowpitch League", "Co-ed slowpitch softball and batting cage hitting drills", "Baseball & Softball"),
            ("North York Golf Lab", "Golf swing coaching, short game putting tips, and TrackMan indoor simulators", "Golf"),
            ("Toronto HYROX Hybrid", "HYROX conditioning, CrossFit functional fitness, and outdoor bootcamps", "Fitness & Cross-Training"),
            ("Queen West Boxing & BJJ", "Muay Thai sparring, boxing footwork, and no-gi Brazilian Jiu-Jitsu", "Combat & Martial Arts"),
            ("Toronto Sport & Social", "Multi-sport adult rec leagues: dodgeball, kickball, co-ed social sports & intramurals", "Multi-Sport & Rec Leagues"),
        ]
        self.assertEqual(len(SPORT_CATEGORIES), 12)
        for name, bio, expected_sport in cases:
            res = classify_partner({
                "partner_id": f"test_{expected_sport}",
                "name": name,
                "bio": bio,
                "primary_platform": "youtube",
                "profile_url": "https://example.com",
            })
            self.assertEqual(res["primary_sport"], expected_sport, msg=f"Failed on {name}")
            self.assertTrue(bool(res["sub_niche"]))

    def test_pickup_runs_stay_basketball_not_running(self):
        res = classify_partner({
            "partner_id": "yt_hoops",
            "name": "6ix Pickup Runs",
            "bio": "Weekly open gym pickup runs, 5v5 basketball games, and streetball highlights in Toronto.",
            "primary_platform": "youtube",
            "profile_url": "https://youtube.com/@6ixruns",
        })
        self.assertEqual(res["primary_sport"], "Basketball")
        self.assertEqual(res["sub_niche"], "Pickup Runs & Streetball")


class PartnerTypeTests(unittest.TestCase):
    def test_pro_candidate_roles(self):
        creator = classify_partner_type({
            "name": "Alex Hoops",
            "bio": "I share weekly basketball vlogs and outdoor streetball highlights across Ontario.",
            "primary_platform": "youtube",
        })
        self.assertEqual(creator, ("pro_candidate", "Sports Creator / Athlete"))

        coach = classify_partner_type({
            "name": "Coach Marcus Tennis",
            "bio": "Certified tennis coach sharing forehand lessons and footwork drills.",
            "primary_platform": "youtube",
        })
        self.assertEqual(coach, ("pro_candidate", "Coach / Trainer"))

        pickup = classify_partner_type({
            "name": "Sunday Morning Pickup Basketball",
            "bio": "Casual weekly pickup and drop-in open gym runs hosted by Danny.",
            "primary_platform": "meetup",
            "meetup_url": "https://www.meetup.com/sunday-pickup-basketball",
        })
        self.assertEqual(pickup, ("pro_candidate", "Pickup Organizer"))

        uni_leader = classify_partner_type({
            "name": "Maya Chen — Varsity Track",
            "bio": "UofT student athlete and varsity track team captain sharing campus training.",
            "primary_platform": "youtube",
        })
        self.assertEqual(uni_leader, ("pro_candidate", "University Leader"))

        # Individual creator found via an org seed still classifies as pro_candidate
        lauren = classify_partner_type({
            "name": "Lauren Mantha",
            "bio": "Hi, I'm Lauren! I'm a 28-year-old creator, personal trainer, and founder of A RUNNING LIST in Toronto.",
            "primary_platform": "youtube",
            "seed_partner_type": "sports_org",
            "seed_partner_role": "Sports Club / Run Club",
        })
        self.assertEqual(lauren[0], "pro_candidate")

        # Rec league found via a pro seed still classifies as sports_org
        cbl = classify_partner_type({
            "name": "Canadian Beer League",
            "bio": "Adult beginner & intermediate hockey practice for men and women. Now expanding across Ontario.",
            "primary_platform": "youtube",
            "seed_partner_type": "pro_candidate",
            "seed_partner_role": "Pickup Organizer",
        })
        self.assertEqual(cbl, ("sports_org", "Rec League"))

        # Curated org re-classification without seed_partner_type retains sports_org & role
        org_reclass = classify_partner({
            "partner_id": "org_torontobjj_com",
            "name": "Toronto BJJ",
            "primary_platform": "website",
            "profile_url": "https://www.torontobjj.com",
            "country": "Canada",
            "province_state": "Ontario",
            "city": "Toronto",
            "audience_text": "Gym / Training Facility",
            "bio": "Toronto BJJ Programs Adult Kids Teens.",
        })
        self.assertEqual(org_reclass["partner_type"], "sports_org")
        self.assertEqual(org_reclass["partner_role"], "Gym / Training Facility")
        self.assertEqual(org_reclass["primary_sport"], "Combat & Martial Arts")

        # Ultimate club stays Flag Football & Turf Sports
        tuc = classify_partner({
            "partner_id": "org_tuc_org",
            "name": "Toronto Ultimate Club",
            "primary_platform": "website",
            "profile_url": "https://www.tuc.org",
            "country": "Canada",
            "province_state": "Ontario",
            "city": "Toronto",
            "audience_text": "Sports Club / Run Club",
            "bio": "Join Toronto Ultimate Club leagues and pickup games.",
        })
        self.assertEqual(tuc["primary_sport"], "Flag Football & Turf Sports")
        self.assertEqual(tuc["partner_type"], "sports_org")

    def test_sports_org_roles(self):
        league = classify_partner_type({
            "name": "JAM Sports Toronto",
            "bio": "Toronto's largest adult co-ed rec league for soccer, volleyball, basketball, and softball.",
            "primary_platform": "website",
            "seed_partner_type": "sports_org",
            "seed_partner_role": "Rec League",
        })
        self.assertEqual(league, ("sports_org", "Rec League"))

        run_club = classify_partner_type({
            "name": "BlackToe Run Club",
            "bio": "Community running club hosting weekly group runs across Toronto.",
            "primary_platform": "meetup",
            "meetup_url": "https://www.meetup.com/blacktoe-run-club",
        })
        self.assertEqual(run_club, ("sports_org", "Sports Club / Run Club"))

        gym = classify_partner_type({
            "name": "Toronto BJJ Academy",
            "bio": "Martial arts academy and training facility offering BJJ and Muay Thai classes.",
            "primary_platform": "youtube",
        })
        self.assertEqual(gym, ("sports_org", "Gym / Training Facility"))

        uni_net = classify_partner_type({
            "name": "York University Campus Recreation",
            "bio": "Official university intramurals and athletics department clubs.",
            "primary_platform": "youtube",
        })
        self.assertEqual(uni_net, ("sports_org", "University Network"))

        tourney = classify_partner_type({
            "name": "Canada Running Series",
            "bio": "National race series and marathon tournament operator.",
            "primary_platform": "youtube",
        })
        self.assertEqual(tourney, ("sports_org", "Tournament Operator"))


class GeoAndTierTests(unittest.TestCase):
    def test_audience_tiers(self):
        self.assertEqual(compute_audience_tier(1_400_000), "mega")
        self.assertEqual(compute_audience_tier(650_000), "macro")
        self.assertEqual(compute_audience_tier(180_000), "mid")
        self.assertEqual(compute_audience_tier(25_000), "micro")
        self.assertEqual(compute_audience_tier(2_500), "nano")

    def test_us_canada_only_geo_and_toronto_gta(self):
        self.assertEqual(
            extract_partner_location("Toronto Hoops", "Pickup runs in Scarborough and Downtown Toronto", ""),
            ("Toronto", "Ontario", "Canada"),
        )
        self.assertEqual(
            extract_partner_location("GTA Pickleball", "Playing across Mississauga, ON every weekend", "Canada"),
            ("Mississauga", "Ontario", "Canada"),
        )
        self.assertTrue(is_toronto_gta("Mississauga", "Ontario", "Canada"))
        self.assertFalse(is_toronto_gta("Vancouver", "British Columbia", "Canada"))

        # .ca ccTLD infers Canada cleanly when country omitted
        self.assertEqual(
            extract_partner_location("East Coast Club", "Join our games", "", website="https://eastcoastclub.ca"),
            ("", "", "Canada"),
        )

        # Outside US & Canada must strip city & province_state
        self.assertEqual(
            extract_partner_location("UK Footy", "Matches near London and Toronto, ON", "United Kingdom"),
            ("", "", "United Kingdom"),
        )

        # Reject sports words and street addresses as false cities
        self.assertEqual(
            extract_partner_location("Coach", "Basketball, IN my gym", ""),
            ("", "", ""),
        )
        self.assertEqual(
            extract_partner_location("Org", "1209 Tatnall Building Wilmington, DE", "United States"),
            ("", "", "United States"),
        )
        self.assertEqual(
            extract_partner_location("Austin Ballers", "Flag football in Austin, TX", "United States"),
            ("Austin", "Texas", "United States"),
        )
        self.assertEqual(
            extract_partner_location("Coach", "Virtual Clinics Charlotte, North Carolina", "United States"),
            ("Charlotte", "North Carolina", "United States"),
        )


class EmailAndLinksTests(unittest.TestCase):
    def test_verified_email_extraction_and_strict_filtering(self):
        noisy = (
            "Asset badge@2x.png support@linktr.ee noreply@site.com "
            "help@teamsnap.com info@leagueapps.com admin@courtreserve.com "
            "sponsors@nike.com partner@lululemon.com promo@lmnt.com "
            "support@squarespace.com privacy@example.com a1b2c3d4e5f6071890ab@random.io "
            "Business & collabs: hello@torontohoops.ca "
            "Club email: coach [at] parkdalerunners [dot] com"
        )
        emails = _extract_clean_emails(
            noisy,
            allowed_site_domain="torontohoops.ca",
            require_context_for_third_party=True,
        )
        self.assertIn("hello@torontohoops.ca", emails)
        self.assertIn("coach@parkdalerunners.com", emails)
        for bad in (
            "badge@2x.png", "support@linktr.ee", "noreply@site.com",
            "help@teamsnap.com", "info@leagueapps.com", "admin@courtreserve.com",
            "sponsors@nike.com", "partner@lululemon.com", "promo@lmnt.com",
            "support@squarespace.com", "privacy@example.com",
        ):
            self.assertNotIn(bad, emails)

        # Third-party email without outreach context or near false context rejected
        footer_noise = "Theme designed by studio@webdesign.io. Music by artist@beatmaker.fm."
        self.assertEqual(
            _extract_clean_emails(footer_noise, allowed_site_domain="myclub.ca", require_context_for_third_party=True),
            [],
        )

        # Cloudflare data-cfemail decoding + %20 mailto decoding + Runna sponsor filtering
        plain = "leagues@xtsc.ca"
        key = 0x3C
        encoded = f"{key:02x}" + "".join(f"{ord(c) ^ key:02x}" for c in plain)
        self.assertEqual(_decode_cfemail(encoded), plain)
        html_doc = (
            f'<html><body><p>Contact <span data-cfemail="{encoded}">[email]</span> '
            f'<a href="mailto:%20info@tracergolf.ca">Email</a> '
            f'Sponsor: hello@runna.com</p></body></html>'
        )
        found, _, _, _ = _parse_html_page_signals(html_doc, page_url="https://tracergolf.ca/contact", allowed_site_domain="tracergolf.ca")
        self.assertIn(plain, found)
        self.assertIn("info@tracergolf.ca", found)
        self.assertNotIn("20info@tracergolf.ca", found)
        self.assertNotIn("hello@runna.com", found)

    def test_all_13_social_and_community_links_extracted(self):
        urls = [
            "https://www.youtube.com/@torontorunners",
            "https://www.instagram.com/torontorunners/",
            "https://www.tiktok.com/@torontorunners",
            "https://www.facebook.com/torontorunners",
            "https://x.com/torontorunners",
            "https://www.threads.net/@torontorunners",
            "https://www.linkedin.com/company/torontorunners/",
            "https://www.pinterest.com/pin/12345/",
            "https://www.pinterest.com/torontorunners/",
            "https://www.reddit.com/r/torontorunning/",
            "https://www.strava.com/clubs/torontorunners",
            "https://bsky.app/profile/torontorunners.bsky.social",
            "https://www.meetup.com/toronto-runners-club/",
            "https://www.meetup.com/find/?keywords=run",
            "https://www.eventbrite.ca/o/toronto-runners-12345",
            "https://linktr.ee/torontorunners",
            "https://nike.com/running",
            "https://torontorunners.ca",
        ]
        res = _classify_partner_links(urls)
        self.assertEqual(res["youtube_url"], "https://www.youtube.com/@torontorunners")
        self.assertEqual(res["instagram_url"], "https://www.instagram.com/torontorunners")
        self.assertEqual(res["tiktok_url"], "https://www.tiktok.com/@torontorunners")
        self.assertEqual(res["facebook_url"], "https://www.facebook.com/torontorunners")
        self.assertEqual(res["x_url"], "https://x.com/torontorunners")
        self.assertEqual(res["threads_url"], "https://www.threads.net/@torontorunners")
        self.assertEqual(res["linkedin_url"], "https://www.linkedin.com/company/torontorunners")
        self.assertEqual(res["pinterest_url"], "https://www.pinterest.com/torontorunners")
        self.assertEqual(res["reddit_url"], "https://www.reddit.com/r/torontorunning")
        self.assertEqual(res["strava_url"], "https://www.strava.com/clubs/torontorunners")
        self.assertEqual(res["bluesky_url"], "https://bsky.app/profile/torontorunners.bsky.social")
        self.assertEqual(res["meetup_url"], "https://www.meetup.com/toronto-runners-club")
        self.assertEqual(res["eventbrite_url"], "https://www.eventbrite.ca/o/toronto-runners-12345")
        self.assertEqual(res["link_hubs"], ["https://linktr.ee/torontorunners"])
        self.assertEqual(res["website"], "https://torontorunners.ca")

    def test_meetup_corporate_socials_rejected_and_follower_parsers(self):
        links = _classify_partner_links([
            "https://www.instagram.com/meetup/",
            "https://www.tiktok.com/@meetup",
            "https://www.facebook.com/meetup",
            "https://twitter.com/meetup",
            "https://www.linkedin.com/company/meetup",
            "https://www.instagram.com/mapleleafpickleball/",
        ])
        self.assertEqual(links["instagram_url"], "https://www.instagram.com/mapleleafpickleball")
        self.assertEqual(links["tiktok_url"], "")
        self.assertEqual(links["facebook_url"], "")
        self.assertEqual(links["x_url"], "")
        self.assertEqual(links["linkedin_url"], "")

        ig_html = '<meta property="og:description" content="8,568 Followers, 412 Following, 310 Posts" />'
        self.assertEqual(_parse_instagram_followers_html(ig_html), 8568)
        ig_compact = '<meta property="og:description" content="1.2M Followers, 100 Following" />'
        self.assertEqual(_parse_instagram_followers_html(ig_compact), 1200000)

        tt_html = '<script>{"stats":{"followerCount":283700,"followingCount":10}}</script>'
        self.assertEqual(_parse_tiktok_followers_html(tt_html), 283700)

    def test_multi_platform_follower_aggregation_and_tier(self):
        c = classify_partner({
            "partner_id": "org_recreationtmu",
            "name": "TMU Recreation",
            "primary_platform": "website",
            "profile_url": "https://www.torontomu.ca/recreation",
            "country": "Canada",
            "province_state": "Ontario",
            "city": "Toronto",
            "audience_text": "University Network",
            "instagram_followers": 8568,
            "tiktok_followers": 4200,
            "seed_partner_type": "sports_org",
            "seed_partner_role": "University Network",
        })
        self.assertEqual(c["audience_count"], 12768)
        self.assertEqual(c["audience_tier"], "micro")
        self.assertEqual(c["audience_text"], "12,768 followers")


class DatabaseAndCsvTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self._orig_db_path = database.DB_PATH
        database.DB_PATH = self._tmp.name
        database.init_db()

    def tearDown(self):
        database.DB_PATH = self._orig_db_path
        if os.path.exists(self._tmp.name):
            os.remove(self._tmp.name)

    def test_upsert_query_contacted_and_summary(self):
        p1 = classify_partner({
            "partner_id": "yt_to_hoops",
            "name": "TO Pickup Hoops",
            "handle": "@topickuphoops",
            "primary_platform": "youtube",
            "profile_url": "https://www.youtube.com/@topickuphoops",
            "country": "Canada",
            "bio": "Weekly pickup basketball runs in Mississauga, ON.",
            "audience_count": 22000,
            "youtube_followers": 22000,
            "instagram_followers": 8000,
            "business_email": "host@topickuphoops.ca",
            "instagram_url": "https://instagram.com/topickuphoops",
            "meetup_url": "https://www.meetup.com/to-pickup-hoops",
            "seed_partner_type": "pro_candidate",
            "seed_partner_role": "Pickup Organizer",
        })
        p2 = classify_partner({
            "partner_id": "org_parkdale_run",
            "name": "Parkdale Roadrunners",
            "handle": "parkdaleroadrunners.com",
            "primary_platform": "website",
            "profile_url": "https://www.parkdaleroadrunners.com",
            "country": "Canada",
            "province_state": "Ontario",
            "city": "Toronto",
            "bio": "Toronto social run club on Strava.",
            "audience_count": 4500,
            "strava_url": "https://www.strava.com/clubs/parkdale",
            "eventbrite_url": "https://www.eventbrite.ca/o/parkdale-1",
            "seed_partner_type": "sports_org",
            "seed_partner_role": "Sports Club / Run Club",
        })
        p3 = classify_partner({
            "partner_id": "yt_uk_fc",
            "name": "London Sunday League",
            "primary_platform": "youtube",
            "profile_url": "https://www.youtube.com/@ukfc",
            "country": "United Kingdom",
            "city": "London",
            "province_state": "Greater London",
            "bio": "Amateur soccer vlog in London.",
            "audience_count": 120000,
        })

        self.assertTrue(database.upsert_partner(p1))
        self.assertTrue(database.upsert_partner(p2))
        self.assertTrue(database.upsert_partner(p3))

        # Re-upsert preserves contacted and existing email
        self.assertEqual(database.set_partner_contacted("yt_to_hoops", True)["updated"], True)
        p1_again = dict(p1, business_email="")
        self.assertFalse(database.upsert_partner(p1_again))

        pros = database.query_partners(partner_type="pro_candidate")
        self.assertEqual([r["partner_id"] for r in pros], ["yt_to_hoops", "yt_uk_fc"])
        self.assertEqual(pros[0]["business_email"], "host@topickuphoops.ca")
        self.assertEqual(pros[0]["contacted"], 1)
        self.assertEqual(pros[0]["youtube_followers"], 22000)
        self.assertEqual(pros[0]["instagram_followers"], 8000)
        self.assertEqual(pros[0]["audience_count"], 30000)

        gta_rows = database.query_partners(country="Toronto / GTA")
        self.assertEqual({r["partner_id"] for r in gta_rows}, {"yt_to_hoops", "org_parkdale_run"})

        strava_rows = database.query_partners(social_platform="strava")
        self.assertEqual([r["partner_id"] for r in strava_rows], ["org_parkdale_run"])

        meetup_rows = database.query_partners(social_platform="meetup")
        self.assertEqual([r["partner_id"] for r in meetup_rows], ["yt_to_hoops"])

        uk_rows = database.query_partners(country="Other")
        self.assertEqual(len(uk_rows), 1)
        self.assertEqual(uk_rows[0]["city"], "")
        self.assertEqual(uk_rows[0]["province_state"], "")

        summary = database.get_partners_summary()
        self.assertEqual(summary["kpis"]["total_partners"], 3)
        self.assertEqual(summary["kpis"]["pro_candidates"], 2)
        self.assertEqual(summary["kpis"]["sports_orgs"], 1)
        self.assertEqual(summary["kpis"]["toronto_gta"], 2)
        self.assertEqual(summary["kpis"]["contacted_count"], 1)
        self.assertEqual(summary["kpis"]["on_strava"], 1)
        self.assertEqual(summary["kpis"]["on_meetup"], 1)
        self.assertEqual(summary["kpis"]["on_eventbrite"], 1)

    def test_csv_formula_injection_guard(self):
        self.assertEqual(app_mod._csv_safe("=HYPERLINK(\"http://bad\")"), "'=HYPERLINK(\"http://bad\")")
        self.assertEqual(app_mod._csv_safe("+cmd"), "'+cmd")
        self.assertEqual(app_mod._csv_safe("-123"), "'-123")
        self.assertEqual(app_mod._csv_safe("@SUM(A1)"), "'@SUM(A1)")
        self.assertEqual(app_mod._csv_safe("Toronto Hoops"), "Toronto Hoops")


if __name__ == "__main__":
    unittest.main(verbosity=2)
