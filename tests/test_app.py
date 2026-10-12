from copy import deepcopy

import pytest


def test_root_redirects_to_static_page(client):
    # Arrange
    expected_location = "/static/index.html"

    # Act
    response = client.get("/", follow_redirects=False)

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == expected_location


def test_get_activities_returns_initial_data(client, isolated_activities):
    # Arrange
    expected_activities = deepcopy(isolated_activities)
    expected_fields = {"description", "schedule", "max_participants", "participants"}

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert response.json() == expected_activities
    assert all(expected_fields <= activity.keys() for activity in response.json().values())


def test_signup_adds_one_participant(client, isolated_activities):
    # Arrange
    activity_name = "Chess Club"
    email = "new.student@mergington.edu"
    expected_activities = deepcopy(isolated_activities)
    initial_count = len(expected_activities[activity_name]["participants"])
    expected_activities[activity_name]["participants"].append(email)

    # Act
    response = client.post(f"/activities/{activity_name}/signup", params={"email": email})
    activities_response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Signed up {email} for {activity_name}"}
    assert activities_response.status_code == 200
    assert activities_response.json() == expected_activities
    participants = activities_response.json()[activity_name]["participants"]
    assert len(participants) == initial_count + 1
    assert participants.count(email) == 1


def test_signup_rejects_duplicate_without_changing_state(client, isolated_activities):
    # Arrange
    activity_name = "Chess Club"
    email = "new.student@mergington.edu"
    client.post(f"/activities/{activity_name}/signup", params={"email": email})
    expected_activities = deepcopy(isolated_activities)

    # Act
    response = client.post(f"/activities/{activity_name}/signup", params={"email": email})
    activities_response = client.get("/activities")

    # Assert
    assert response.status_code == 400
    assert response.json() == {"detail": "Student already signed up for this activity"}
    assert activities_response.status_code == 200
    assert activities_response.json() == expected_activities
    assert activities_response.json()[activity_name]["participants"].count(email) == 1


@pytest.mark.parametrize("method,endpoint", [("POST", "signup"), ("DELETE", "participants")])
def test_signup_and_unregister_reject_unknown_activity(client, isolated_activities, method, endpoint):
    # Arrange
    activity_name = "Unknown Activity"
    email = "new.student@mergington.edu"
    expected_activities = deepcopy(isolated_activities)

    # Act
    response = client.request(method, f"/activities/{activity_name}/{endpoint}", params={"email": email})
    activities_response = client.get("/activities")

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}
    assert activities_response.status_code == 200
    assert activities_response.json() == expected_activities


def test_unregister_removes_only_requested_participant(client, isolated_activities):
    # Arrange
    activity_name = "Chess Club"
    email = isolated_activities[activity_name]["participants"][0]
    expected_activities = deepcopy(isolated_activities)
    initial_count = len(expected_activities[activity_name]["participants"])
    expected_activities[activity_name]["participants"].remove(email)

    # Act
    response = client.delete(f"/activities/{activity_name}/participants", params={"email": email})
    activities_response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Unregistered {email} from {activity_name}"}
    assert activities_response.status_code == 200
    assert activities_response.json() == expected_activities
    participants = activities_response.json()[activity_name]["participants"]
    assert len(participants) == initial_count - 1
    assert email not in participants


def test_unregister_rejects_unregistered_email(client, isolated_activities):
    # Arrange
    activity_name = "Chess Club"
    email = "not.registered@mergington.edu"
    expected_activities = deepcopy(isolated_activities)

    # Act
    response = client.delete(f"/activities/{activity_name}/participants", params={"email": email})
    activities_response = client.get("/activities")

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Student is not signed up for this activity"}
    assert activities_response.status_code == 200
    assert activities_response.json() == expected_activities


def test_unregister_rejects_repeated_removal(client, isolated_activities):
    # Arrange
    activity_name = "Chess Club"
    email = isolated_activities[activity_name]["participants"][0]
    client.delete(f"/activities/{activity_name}/participants", params={"email": email})
    expected_activities = deepcopy(isolated_activities)

    # Act
    response = client.delete(f"/activities/{activity_name}/participants", params={"email": email})
    activities_response = client.get("/activities")

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Student is not signed up for this activity"}
    assert activities_response.status_code == 200
    assert activities_response.json() == expected_activities
    assert email not in activities_response.json()[activity_name]["participants"]


@pytest.mark.parametrize("method,endpoint", [("POST", "signup"), ("DELETE", "participants")])
def test_signup_and_unregister_require_email(client, isolated_activities, method, endpoint):
    # Arrange
    activity_name = "Chess Club"
    expected_activities = deepcopy(isolated_activities)

    # Act
    response = client.request(method, f"/activities/{activity_name}/{endpoint}")
    activities_response = client.get("/activities")

    # Assert
    assert response.status_code == 422
    assert any(error["loc"] == ["query", "email"] for error in response.json()["detail"])
    assert activities_response.status_code == 200
    assert activities_response.json() == expected_activities


def test_signup_after_unregister_succeeds_without_duplicates(client, isolated_activities):
    # Arrange
    activity_name = "Chess Club"
    email = "returning.student@mergington.edu"
    initial_activities = deepcopy(isolated_activities)
    expected_registered_activities = deepcopy(initial_activities)
    expected_registered_activities[activity_name]["participants"].append(email)

    # Act
    signup_response = client.post(f"/activities/{activity_name}/signup", params={"email": email})
    registered_response = client.get("/activities")
    unregister_response = client.delete(f"/activities/{activity_name}/participants", params={"email": email})
    unregistered_response = client.get("/activities")
    signup_again_response = client.post(f"/activities/{activity_name}/signup", params={"email": email})
    registered_again_response = client.get("/activities")

    # Assert
    assert signup_response.status_code == 200
    assert unregister_response.status_code == 200
    assert signup_again_response.status_code == 200
    assert signup_again_response.json() == {"message": f"Signed up {email} for {activity_name}"}
    assert registered_response.status_code == 200
    assert unregistered_response.status_code == 200
    assert registered_again_response.status_code == 200
    assert registered_response.json() == expected_registered_activities
    assert unregistered_response.json() == initial_activities
    assert registered_again_response.json() == expected_registered_activities
    assert registered_again_response.json()[activity_name]["participants"].count(email) == 1


def test_unregister_last_participant_leaves_empty_list(client, isolated_activities):
    # Arrange
    activity_name = "Chess Club"
    email = "last.student@mergington.edu"
    isolated_activities[activity_name]["participants"] = [email]
    expected_activities = deepcopy(isolated_activities)
    expected_activities[activity_name]["participants"] = []

    # Act
    response = client.delete(f"/activities/{activity_name}/participants", params={"email": email})
    activities_response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Unregistered {email} from {activity_name}"}
    assert activities_response.status_code == 200
    assert activities_response.json() == expected_activities
    assert activities_response.json()[activity_name]["participants"] == []