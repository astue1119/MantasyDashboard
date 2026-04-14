from yahoo_oauth import OAuth2

oauth = OAuth2(
    consumer_key="dj0yJmk9YlhYT0hHeVFGWFR2JmQ9WVdrOWIxWk5iMmQxWjI0bWNHbzlNQT09JnM9Y29uc3VtZXJzZWNyZXQmc3Y9MCZ4PWUx",
    consumer_secret="69f76bc8536fb71da47ea9e068607fd20e545558",
    callback_url="http://localhost:8080/",
)

if not oauth.token_is_valid():
    oauth.refresh_access_token()


