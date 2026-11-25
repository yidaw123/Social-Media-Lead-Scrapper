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
    _is_adult_or_nsfw_profile,
    _is_authentic_sports_partner,
    _parse_html_page_signals,
    _parse_instagram_followers_html,
    _parse_instagram_profile_html,
    _parse_tiktok_followers_html,
    deduplicate_and_merge_partners,
    sanitize_stored_partner_row,
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

    def test_audit_partner_type_edge_cases(self):
        # Solo creator with 'Beer League' in channel name stays Pro Candidate
        blhg = classify_partner_type({
            "name": "Beer League Hockey Guy",
            "bio": "SUBSCRIBE for Cool NHL Stories, Documentaries, Crazy Shorts & More. From a beer league hockey player & lifelong hockey junkie!",
            "primary_platform": "youtube",
        })
        self.assertEqual(blhg, ("pro_candidate", "Sports Creator / Athlete"))

        # JCC facility Meetup is Sports Org (Gym / Training Facility), not Pickup Organizer
        jcc = classify_partner_type({
            "name": "Drop-in Recreation - Volleyball, Basketball, Pickleball",
            "handle": "meetup/downtown-miles-nadal-jcc-sports-and-recreation",
            "bio": "Drop-in sports at the Miles Nadal JCC in Downtown Toronto.",
            "primary_platform": "meetup",
            "meetup_url": "https://www.meetup.com/downtown-miles-nadal-jcc-sports-and-recreation",
        })
        self.assertEqual(jcc, ("sports_org", "Gym / Training Facility"))

        # Generic Meetup Group without individual host cue is Sports Club / Run Club
        w_hoops = classify_partner_type({
            "name": "Toronto Women's Basketball Meetup Group",
            "handle": "meetup/Toronto-Womens-Basketball-Meetup-Group",
            "bio": "Weekly pickup basketball sessions for women in Toronto.",
            "primary_platform": "meetup",
            "meetup_url": "https://www.meetup.com/Toronto-Womens-Basketball-Meetup-Group",
        })
        self.assertEqual(w_hoops, ("sports_org", "Sports Club / Run Club"))


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
        # Reject repeated-word and venue-prefix false cities ('Kris Kris', 'Country Club Canmore')
        self.assertEqual(
            extract_partner_location("TPA tennis", "SIGN UP WITH KRIS KRIS, OR JOIN TODAY", "United States"),
            ("", "", "United States"),
        )
        self.assertEqual(
            extract_partner_location("Beat the Course", "Filmed at Country Club Canmore, AB", "Canada"),
            ("Canmore", "Alberta", "Canada"),
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

    def test_nsfw_onlyfans_and_corporate_social_links_rejected(self):
        self.assertTrue(
            _is_adult_or_nsfw_profile(
                "Max Scott",
                "@maxscott.bsky.social",
                "Addicted to fitness, gaming, outdoors and 🍆🎮😈🔞 https://onlyfans.com/maxscott2022/c3",
            )
        )
        self.assertTrue(
            _is_adult_or_nsfw_profile(
                "Hazel Hoffman",
                "@hazelhoffman.bsky.social",
                "Fitness and fashion",
                ["https://x.com/hazelhoffmanxxx"],
            )
        )
        # Hidden OnlyFans inside a Linktree page HTML
        lt_html = '<html><body><a href="https://onlyfans.com/vipclub">VIP Page</a></body></html>'
        _, lt_urls, _, _ = _parse_html_page_signals(lt_html, page_url="https://linktr.ee/someone")
        self.assertTrue(_is_adult_or_nsfw_profile("Creator", "@creator", "Fitness", lt_urls))

        # Legitimate adult rec league must NOT trigger adult NSFW filter
        self.assertFalse(
            _is_adult_or_nsfw_profile(
                "Ontario Volleyball Association",
                "ontariovolleyball.org",
                "Adult 18+ Co-Ed Indoor & Beach Volleyball Leagues across Ontario.",
            )
        )

        # Corporate handles & Facebook share links blocked
        links = _classify_partner_links([
            "https://instagram.com/onlyfans",
            "https://x.com/onlyfans",
            "https://www.tiktok.com/@wix",
            "https://www.instagram.com/meetup",
            "https://www.instagram.com/jotform_official",
            "https://x.com/mapbox-gl-js",
            "https://form.jotform.com/253594642023254",
            "https://www.facebook.com/share/1tvtmzfa6t",
            "https://www.instagram.com/academyoflions",
        ])
        self.assertEqual(links["instagram_url"], "https://www.instagram.com/academyoflions")
        self.assertEqual(links["x_url"], "")
        self.assertEqual(links["tiktok_url"], "")
        self.assertEqual(links["facebook_url"], "")
        self.assertEqual(links["website"], "")

    def test_authentic_sports_and_fitness_verification(self):
        # Reject casual hobbyists, politicians, journalists, tech reviewers, franchises, media/stats sites, non-NA
        for name, handle, bio, plat, ctry in [
            ("Max Scott", "@maxscott.bsky.social", "Addicted to fitness, gaming, outdoors and https://onlyfans.com/maxscott22/c3", "bluesky", ""),
            ("Holly R. Valakresch", "@hollyvalakresch.bsky.social", "Author & Screenwriter | Cooking, Baking, Fashion, Fitness, Fairytales", "bluesky", ""),
            ("Jane Fonda", "@janefonda.com", "Official account for the Actress, Author, Activist, Fitness Advocate", "bluesky", ""),
            ("Liz Cheney", "@lizcheney.bsky.social", "Proud rodeo mom, soccer mom, baseball mom, hockey mom, constitutional conservative.", "bluesky", ""),
            ("Rep. Jason Crow", "@crow.house.gov", "Dad. Little League Baseball Coach. Colorado Congressman.", "bluesky", ""),
            ("Mike Vorkunov", "@mikevorkunov.bsky.social", "National NBA + basketball reporter at The Athletic", "bluesky", ""),
            ("Aesthetic AL", "@Aesthetic_Al", "Home of the Tech Reviews for the Fitness Enthusiast", "youtube", ""),
            ("Mississauga Girls Out At Events", "meetup/mississauga-girls", "Women who love trying new things and going to events", "meetup", "Canada"),
            ("Etobicoke Weekend Walks", "meetup/etobicoke-walks", "Simple weekend walks around Toronto west end", "meetup", "Canada"),
            ("PlayYourCourt Greater Toronto Group", "meetup/playyourcourt-toronto", "At PlayYourCourt we connect tennis players https://www.playyourcourt.com", "meetup", "Canada"),
            ("Basketball Reference", "@basketball-reference.com", "Basketball stats and history for the NBA, WNBA, European Leagues.", "bluesky", "United States"),
            ("Bill Simmons", "@billsimmons.bsky.social", "The Bill Simmons Podcast, The Rewatchables, The Ringer, Spotify, 30 for 30, ESPN.", "bluesky", ""),
            ("Sam Vecenie", "@samvecenie.bsky.social", "I talk about basketball and movies. Host of the Game Theory Podcast.", "bluesky", ""),
            ("Kai Ryssdal", "@kairyssdal.bsky.social", "Dad, husband. IPAs. Soccer referee, trail runner, mountain biker. Veteran.", "bluesky", ""),
            ("SCOREGolf", "@SCOREGolf", "All of SCOREGolf.com's video from the PGA Tour and Canadian Golf Course rankings.", "youtube", "Canada"),
            ("Top Tennis Training", "@TopTennisTraining", "Tennis coaching drills and lessons.", "youtube", "United Kingdom"),
            ("Wanhee 완희", "@wanheekim", "Hi I'm Wanhee. I started my fitness journey at university.", "youtube", ""),
        ]:
            self.assertFalse(
                _is_authentic_sports_partner(name, handle, bio, primary_platform=plat, country=ctry),
                msg=f"Should reject {name}",
            )

        # Accept real fitness & sports creators/orgs
        for name, handle, bio, plat in [
            ("Rich Ryan", "@RichRyan", "HYROX Elite 15 athlete delivers training tips and workouts.", "youtube"),
            ("Lucy Davis Fit", "@LucyDavisFit", "Hybrid athlete and strength conditioning coach sharing marathon and gym workouts.", "youtube"),
            ("BodyBusterFitness", "@Bodybusterfitnessbootcamp", "Group fitness bootcamp and obstacle conditioning workouts.", "youtube"),
            ("Lauren Mantha", "@LaurenMantha", "Personal trainer and runner based in Toronto sharing half marathon workouts.", "youtube"),
            ("Downtown Toronto Fitness & Wellness", "meetup/downtown-toronto-fitness", "Join Toronto's group fitness & longevity community workouts.", "meetup"),
            ("Nick Bare", "@nickbarefitness", "Hybrid athlete marathon and strength workouts.", "youtube"),
        ]:
            self.assertTrue(
                _is_authentic_sports_partner(name, handle, bio, primary_platform=plat),
                msg=f"Should accept {name}",
            )

    def test_facebook_profile_id_meetup_html_and_cross_channel_dedup(self):
        links = _classify_partner_links([
            "https://www.facebook.com/profile.php",
            "https://secure.meetupstatic.com/photos/event/123.jpeg",
        ])
        self.assertEqual(links["facebook_url"], "")
        self.assertEqual(links["website"], "")

        links_with_id = _classify_partner_links(["https://www.facebook.com/profile.php?id=61550987654321&sk=about"])
        self.assertEqual(links_with_id["facebook_url"], "https://www.facebook.com/profile.php?id=61550987654321")

        # Sanitize Meetup HTML bio and bare profile.php on stored rows
        dirty_row = {
            "partner_id": "mu_toronto_soccer",
            "name": "Toronto Pickup Soccer Club",
            "handle": "meetup/toronto-soccer",
            "primary_platform": "meetup",
            "country": "Canada",
            "bio": "<p>Weekly <strong>pickup soccer</strong> games in Downtown Toronto!</p>",
            "website": "https://secure.meetupstatic.com",
            "facebook_url": "https://www.facebook.com/profile.php",
        }
        clean_row = sanitize_stored_partner_row(dirty_row)
        self.assertIsNotNone(clean_row)
        self.assertEqual(clean_row["bio"], "Weekly pickup soccer games in Downtown Toronto!")
        self.assertEqual(clean_row["website"], "")
        self.assertEqual(clean_row["facebook_url"], "")

        # Cross-channel deduplication merges Ontario Soccer website + YouTube channel
        org_web = {
            "partner_id": "org_ontariosoccer_net",
            "name": "Ontario Soccer",
            "primary_platform": "website",
            "website": "https://www.ontariosoccer.net",
            "instagram_url": "https://www.instagram.com/ontariosoccer",
            "instagram_followers": 18000,
            "audience_count": 18000,
            "business_email": "info@ontariosoccer.net",
            "city": "Vaughan",
            "province_state": "Ontario",
            "country": "Canada",
        }
        org_yt = {
            "partner_id": "yt__Ontario_soccer",
            "name": "Ontario Soccer",
            "primary_platform": "youtube",
            "website": "https://ontariosoccer.net",
            "youtube_url": "https://www.youtube.com/@Ontario_soccer",
            "youtube_followers": 4200,
            "audience_count": 4200,
            "country": "Canada",
        }
        deduped, dropped = deduplicate_and_merge_partners([org_yt, org_web])
        self.assertEqual(len(deduped), 1)
        self.assertEqual(dropped, ["yt__Ontario_soccer"])
        self.assertEqual(deduped[0]["partner_id"], "org_ontariosoccer_net")
        self.assertEqual(deduped[0]["youtube_url"], "https://www.youtube.com/@Ontario_soccer")
        self.assertEqual(deduped[0]["audience_count"], 22200)

        # Instagram meta parser extracts followers, display name & bio
        ig_meta_html = (
            '<meta property="og:title" content="TORONTO HOOPSTARS (@torontohoopstars) • Instagram photos and videos" />'
            '<meta content="2,953 Followers, 100 Following, 50 Posts - TORONTO HOOPSTARS (@torontohoopstars) on Instagram: &quot;Elite Basketball Skills Training in Toronto&quot;" />'
        )
        ig_prof = _parse_instagram_profile_html(ig_meta_html)
        self.assertEqual(ig_prof["followers"], 2953)
        self.assertEqual(ig_prof["name"], "TORONTO HOOPSTARS")
        self.assertIn("Elite Basketball Skills Training", ig_prof["bio"])


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

        # Test outreach stages, notes, and dismiss/restore blocklist
        st_res = database.update_partner_outreach(
            "yt_to_hoops",
            outreach_status="replied",
            outreach_notes="Interested in Founding Pro cohort",
        )
        self.assertTrue(st_res["updated"])
        self.assertEqual(st_res["outreach_status"], "replied")
        self.assertEqual(st_res["contacted"], True)
        self.assertEqual(len(database.query_partners(contacted_filter="replied")), 1)
        self.assertEqual(len(database.query_partners(search="Founding Pro cohort")), 1)

        database.update_partner_outreach("yt_uk_fc", is_dismissed=True)
        self.assertIn("yt_uk_fc", database.get_dismissed_partner_ids())
        self.assertEqual(database.get_partners_summary()["kpis"]["total_partners"], 2)
        self.assertEqual(database.get_partners_summary()["kpis"]["dismissed_count"], 1)
        self.assertEqual(len(database.query_partners(contacted_filter="dismissed")), 1)

    def test_cors_origin_lockdown(self):
        self.assertEqual(app_mod._resolve_cors_origin("https://yidaw123.github.io"), "https://yidaw123.github.io")
        self.assertEqual(app_mod._resolve_cors_origin("http://localhost:8766"), "http://localhost:8766")
        self.assertEqual(app_mod._resolve_cors_origin("https://evil.example.com"), "http://localhost:8766")

    def test_csv_formula_injection_guard(self):
        self.assertEqual(app_mod._csv_safe("=HYPERLINK(\"http://bad\")"), "'=HYPERLINK(\"http://bad\")")
        self.assertEqual(app_mod._csv_safe("+cmd"), "'+cmd")
        self.assertEqual(app_mod._csv_safe("-123"), "'-123")
        self.assertEqual(app_mod._csv_safe("@SUM(A1)"), "'@SUM(A1)")
        self.assertEqual(app_mod._csv_safe("Toronto Hoops"), "Toronto Hoops")


if __name__ == "__main__":
    unittest.main(verbosity=2)
