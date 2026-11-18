Feature: Identity Refusal on Public Routes
  As a player and as the platform operator
  I want every public route to refuse credentials it cannot verify
  So that no forged token, retired sign-in route, or body-supplied identity grants access

  Background:
    Given the public API is reachable

  # Governed by US-0062 (sign-in refuses invalid credentials) and US-0013 (verified subject).
  # Executed through the public API only. No dev mode, no backdoor, no database writes.

  Scenario: A forged token is refused on the profile route
    Given I hold a token signed by a key the platform does not trust
    When I request my profile from the public API with that token
    Then the API refuses the request with status 401

  Scenario: The retired sign-in endpoint does not exist
    When I call the retired sign-in endpoint "/api/v1/auth/token"
    Then the API reports the route as absent

  Scenario: A body-supplied role claim cannot sync access
    When I send a sync request to "/api/v1/auth/sync/user" that names the role "owner"
    Then the API reports the route as absent
