from tests.conftest import create_base_questions


def _prepare_published_survey_with_logic(client):
	create_resp = client.post(
		"/surveys",
		json={"title": "答卷逻辑测试", "settings": {"allow_anonymous": True, "allow_multiple": False}},
	)
	survey_id = create_resp.json()["data"]["survey_id"]
	access_code = create_resp.json()["data"]["access_code"]

	update_resp = client.put(
		f"/surveys/{survey_id}",
		json={"questions": create_base_questions()},
	)
	assert update_resp.status_code == 200

	publish_resp = client.post(f"/surveys/{survey_id}/publish")
	assert publish_resp.status_code == 200

	return survey_id, access_code


def test_submit_response_should_follow_jump_logic_and_allow_skip_non_required_path(api_client):
	client, _ = api_client
	survey_id, access_code = _prepare_published_survey_with_logic(client)

	# q1=opt_yes 会直接跳到 q3，q2 虽为必填但不在实际路径中，不应报缺失
	submit_resp = client.post(
		"/responses",
		json={
			"survey_id": survey_id,
			"access_code": access_code,
			"answers": [
				{"question_id": "q1", "answer": "opt_yes"},
				{"question_id": "q3", "answer": 5},
			],
			"is_anonymous": False,
			"completion_time": 32,
		},
	)

	assert submit_resp.status_code == 200
	payload = submit_resp.json()["data"]
	assert payload["survey_id"] == survey_id
	assert payload["submission_count"] == 1


def test_submit_response_missing_required_question_on_actual_path_should_fail(api_client):
	client, _ = api_client
	survey_id, access_code = _prepare_published_survey_with_logic(client)

	# q1=opt_no 时按顺序到 q2，缺失 q2 应触发必填错误
	submit_resp = client.post(
		"/responses",
		json={
			"survey_id": survey_id,
			"access_code": access_code,
			"answers": [
				{"question_id": "q1", "answer": "opt_no"},
				{"question_id": "q3", "answer": 3},
			],
		},
	)

	assert submit_resp.status_code == 400
	assert submit_resp.json()["code"] == 3003
	assert "未回答" in submit_resp.json()["message"]


def test_submit_response_number_validation_should_fail_when_integer_required(api_client):
	client, _ = api_client
	survey_id, access_code = _prepare_published_survey_with_logic(client)

	submit_resp = client.post(
		"/responses",
		json={
			"survey_id": survey_id,
			"access_code": access_code,
			"answers": [
				{"question_id": "q1", "answer": "opt_yes"},
				{"question_id": "q3", "answer": 3.5},
			],
		},
	)

	assert submit_resp.status_code == 400
	assert submit_resp.json()["code"] == 3001
	assert "必须为整数" in submit_resp.json()["message"]


def test_submit_response_should_reject_duplicate_when_allow_multiple_false(api_client):
	client, _ = api_client
	survey_id, access_code = _prepare_published_survey_with_logic(client)

	first = client.post(
		"/responses",
		json={
			"survey_id": survey_id,
			"access_code": access_code,
			"answers": [
				{"question_id": "q1", "answer": "opt_yes"},
				{"question_id": "q3", "answer": 2},
			],
		},
	)
	second = client.post(
		"/responses",
		json={
			"survey_id": survey_id,
			"access_code": access_code,
			"answers": [
				{"question_id": "q1", "answer": "opt_yes"},
				{"question_id": "q3", "answer": 4},
			],
		},
	)

	assert first.status_code == 200
	assert second.status_code == 400
	assert second.json()["code"] == 3002


def test_submit_response_should_reject_anonymous_choice_when_not_allowed(api_client):
	client, _ = api_client

	create_resp = client.post(
		"/surveys",
		json={"title": "匿名策略测试", "settings": {"allow_anonymous": False, "allow_multiple": False}},
	)
	survey_id = create_resp.json()["data"]["survey_id"]
	access_code = create_resp.json()["data"]["access_code"]

	client.put(
		f"/surveys/{survey_id}",
		json={"questions": create_base_questions()},
	)
	client.post(f"/surveys/{survey_id}/publish")

	submit_resp = client.post(
		"/responses",
		json={
			"survey_id": survey_id,
			"access_code": access_code,
			"answers": [
				{"question_id": "q1", "answer": "opt_yes"},
				{"question_id": "q3", "answer": 1},
			],
			"is_anonymous": True,
		},
	)

	assert submit_resp.status_code == 400
	assert submit_resp.json()["code"] == 3001
	assert "不允许匿名" in submit_resp.json()["message"]

