import yahoo_fantasy_api as yfa
import time
from yahoo_oauth import OAuth2

oauth = OAuth2(None, None, from_file='oauth2.json')

if not oauth.token_is_valid():
    oauth.refresh_access_token()

LEAGUE_IDS = ['257.l.555890', '273.l.69198', '314.l.51555', '331.l.60660', '348.l.52705', '359.l.122617', '371.l.66032', '380.l.201654', '390.l.177654', '399.l.471671', '406.l.227', '414.l.57201', '423.l.24800', '449.l.204689', '461.l.186484']

for league_id in LEAGUE_IDS:
    league = yfa.League(oauth, league_id)

    settings = league.settings()

    print("League ID:", league_id)
    print("Name:", settings.get("name"))
    print("Season:", settings.get("season"))
    print("Teams:", settings.get("num_teams"))
    print("Scoring:", settings.get("scoring_type"))
    print("Draft Type:", settings.get("draft_type"))
    print("-" * 40)

    time.sleep(0.5)