from datetime import datetime, timedelta, timezone

from bson import ObjectId

from tests.conftest import create_base_questions


def test_create_survey_success_with_expected_data_structure(api_client):
	client, ctx = api_client

	response = client.post(
		"/surveys",
		json={
			"title": "课程反馈",
			"description": "第一阶段测试",
			"settings": {"allow_anonymous": True, "allow_multiple": False},
		},
	)

	assert response.status_code == 200
	payload = response.json()
	assert payload["code"] == 0
	assert "survey_id" in payload["data"]
	assert payload["data"]["status"] == "draft"
	assert len(payload["data"]["access_code"]) == 8

	survey_doc = ctx.db.surveys.find_one({"_id": ObjectId(payload["data"]["survey_id"])})
	assert survey_doc is not None
	assert survey_doc["title"] == "课程反馈"
	assert survey_doc["response_count"] == 0
	assert survey_doc["questions"] == []
	assert survey_doc["settings"]["allow_anonymous"] is True
	assert survey_doc["settings"]["allow_multiple"] is False


def test_add_questions_and_logic_should_be_persisted(api_client):
	client, _ = api_client

	create_resp = client.post(
		"/surveys",
		json={"title": "跳转逻辑问卷", "settings": {"allow_anonymous": True, "allow_multiple": False}},
	)
	survey_id = create_resp.json()["data"]["survey_id"]

	update_resp = client.put(
		f"/surveys/{survey_id}",
		json={
			"title": "跳转逻辑问卷-v2",
			"questions": create_base_questions(),
		},
	)

	assert update_resp.status_code == 200
	payload = update_resp.json()["data"]
	assert payload["title"] == "跳转逻辑问卷-v2"
	assert len(payload["questions"]) == 3

	q1 = payload["questions"][0]
	assert q1["question_id"] == "q1"
	assert q1["logic"]["enabled"] is True
	assert q1["logic"]["rules"][0]["condition"]["type"] == "select_option"
	assert q1["logic"]["rules"][0]["action"]["type"] == "jump_to"
	assert q1["logic"]["rules"][0]["action"]["target_question_id"] == "q3"


def test_publish_then_edit_should_be_forbidden(api_client):
	client, _ = api_client

	create_resp = client.post(
		"/surveys",
		json={"title": "发布后不可编辑", "settings": {"allow_anonymous": True, "allow_multiple": False}},
	)
	survey_id = create_resp.json()["data"]["survey_id"]

	publish_resp = client.post(f"/surveys/{survey_id}/publish")
	assert publish_resp.status_code == 200
	assert publish_resp.json()["data"]["status"] == "published"

	update_resp = client.put(f"/surveys/{survey_id}", json={"title": "不应成功"})
	assert update_resp.status_code == 403
	assert update_resp.json()["code"] == 2002


def test_my_surveys_should_only_return_current_user_data(api_client):
	client, ctx = api_client

	mine_resp = client.post(
		"/surveys",
		json={"title": "我的问卷", "settings": {"allow_anonymous": True, "allow_multiple": False}},
	)
	assert mine_resp.status_code == 200

	other_id = ctx.create_user("other_user")
	ctx.switch_user(other_id, "other_user")
	other_resp = client.post(
		"/surveys",
		json={"title": "他人的问卷", "settings": {"allow_anonymous": True, "allow_multiple": False}},
	)
	assert other_resp.status_code == 200

	list_resp = client.get("/surveys/my")
	assert list_resp.status_code == 200
	surveys = list_resp.json()["data"]["surveys"]
	assert len(surveys) == 1
	assert surveys[0]["title"] == "他人的问卷"


def test_get_public_survey_should_block_expired_survey(api_client):
	client, _ = api_client

	create_resp = client.post(
		"/surveys",
		json={
			"title": "已过期问卷",
			"deadline": (datetime.now() - timedelta(days=1)).isoformat(),
			"settings": {"allow_anonymous": True, "allow_multiple": False},
		},
	)
	survey_id = create_resp.json()["data"]["survey_id"]
	access_code = create_resp.json()["data"]["access_code"]

	client.post(f"/surveys/{survey_id}/publish")

	public_resp = client.get(f"/public/surveys/{access_code}")
	assert public_resp.status_code == 400
	assert public_resp.json()["code"] == 2004

