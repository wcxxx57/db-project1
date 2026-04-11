from tests.conftest import create_base_questions, convert_to_refs


def _prepare_published_survey_with_logic(client, ctx):
	create_resp = client.post(
		"/surveys",
		json={"title": "答卷逻辑测试", "settings": {"allow_anonymous": True, "allow_multiple": False}},
	)
	survey_id = create_resp.json()["data"]["survey_id"]
	access_code = create_resp.json()["data"]["access_code"]

	questions_refs = create_base_questions(ctx.db, ctx.auth.user_id)
	update_resp = client.put(
		f"/surveys/{survey_id}",
		json={"questions": questions_refs},
	)
	assert update_resp.status_code == 200

	publish_resp = client.post(f"/surveys/{survey_id}/publish")
	assert publish_resp.status_code == 200

	return survey_id, access_code


def test_submit_response_should_follow_jump_logic_and_allow_skip_non_required_path(api_client):
	client, ctx = api_client
	survey_id, access_code = _prepare_published_survey_with_logic(client, ctx)

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
	client, ctx = api_client
	survey_id, access_code = _prepare_published_survey_with_logic(client, ctx)

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
	client, ctx = api_client
	survey_id, access_code = _prepare_published_survey_with_logic(client, ctx)

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
	client, ctx = api_client
	survey_id, access_code = _prepare_published_survey_with_logic(client, ctx)

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
	client, ctx = api_client

	create_resp = client.post(
		"/surveys",
		json={"title": "匿名策略测试", "settings": {"allow_anonymous": False, "allow_multiple": False}},
	)
	survey_id = create_resp.json()["data"]["survey_id"]
	access_code = create_resp.json()["data"]["access_code"]

	questions_refs = create_base_questions(ctx.db, ctx.auth.user_id)
	client.put(
		f"/surveys/{survey_id}",
		json={"questions": questions_refs},
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


def test_text_input_min_length_validation_should_fail(api_client):
	client, ctx = api_client

	create_resp = client.post(
		"/surveys",
		json={"title": "文本最小长度测试", "settings": {"allow_anonymous": True, "allow_multiple": False}},
	)
	survey_id = create_resp.json()["data"]["survey_id"]
	access_code = create_resp.json()["data"]["access_code"]

	raw_q = [{
		"question_id": "q1",
		"type": "text_input",
		"title": "请描述",
		"required": True,
		"order": 1,
		"validation": {"min_length": 5, "max_length": 100},
	}]
	refs = convert_to_refs(ctx.db, ctx.auth.user_id, raw_q)
	client.put(f"/surveys/{survey_id}", json={"questions": refs})
	client.post(f"/surveys/{survey_id}/publish")

	submit_resp = client.post(
		"/responses",
		json={
			"survey_id": survey_id,
			"access_code": access_code,
			"answers": [{"question_id": "q1", "answer": "短"}],
		},
	)

	assert submit_resp.status_code == 400
	assert submit_resp.json()["code"] == 3001
	assert "最少" in submit_resp.json()["message"] or "至少" in submit_resp.json()["message"]


def test_text_input_max_length_validation_should_fail(api_client):
	client, ctx = api_client

	create_resp = client.post(
		"/surveys",
		json={"title": "文本最大长度测试", "settings": {"allow_anonymous": True, "allow_multiple": False}},
	)
	survey_id = create_resp.json()["data"]["survey_id"]
	access_code = create_resp.json()["data"]["access_code"]

	raw_q = [{
		"question_id": "q1",
		"type": "text_input",
		"title": "简短描述",
		"required": True,
		"order": 1,
		"validation": {"min_length": 1, "max_length": 10},
	}]
	refs = convert_to_refs(ctx.db, ctx.auth.user_id, raw_q)
	client.put(f"/surveys/{survey_id}", json={"questions": refs})
	client.post(f"/surveys/{survey_id}/publish")

	submit_resp = client.post(
		"/responses",
		json={
			"survey_id": survey_id,
			"access_code": access_code,
			"answers": [{"question_id": "q1", "answer": "这是一段超过十个字的长文本内容"}],
		},
	)

	assert submit_resp.status_code == 400
	assert submit_resp.json()["code"] == 3001
	assert "最多" in submit_resp.json()["message"] or "不超过" in submit_resp.json()["message"]


def test_multiple_choice_min_selected_validation_should_fail(api_client):
	client, ctx = api_client

	create_resp = client.post(
		"/surveys",
		json={"title": "多选最少数量测试", "settings": {"allow_anonymous": True, "allow_multiple": False}},
	)
	survey_id = create_resp.json()["data"]["survey_id"]
	access_code = create_resp.json()["data"]["access_code"]

	raw_q = [{
		"question_id": "q1",
		"type": "multiple_choice",
		"title": "选择工具",
		"required": True,
		"order": 1,
		"options": [
			{"option_id": "opt1", "text": "工具1"},
			{"option_id": "opt2", "text": "工具2"},
			{"option_id": "opt3", "text": "工具3"},
		],
		"validation": {"min_selected": 2, "max_selected": 3},
	}]
	refs = convert_to_refs(ctx.db, ctx.auth.user_id, raw_q)
	client.put(f"/surveys/{survey_id}", json={"questions": refs})
	client.post(f"/surveys/{survey_id}/publish")

	submit_resp = client.post(
		"/responses",
		json={
			"survey_id": survey_id,
			"access_code": access_code,
			"answers": [{"question_id": "q1", "answer": ["opt1"]}],
		},
	)

	assert submit_resp.status_code == 400
	assert submit_resp.json()["code"] == 3001
	assert "至少" in submit_resp.json()["message"]


def test_multiple_choice_max_selected_validation_should_fail(api_client):
	client, ctx = api_client

	create_resp = client.post(
		"/surveys",
		json={"title": "多选最多数量测试", "settings": {"allow_anonymous": True, "allow_multiple": False}},
	)
	survey_id = create_resp.json()["data"]["survey_id"]
	access_code = create_resp.json()["data"]["access_code"]

	raw_q = [{
		"question_id": "q1",
		"type": "multiple_choice",
		"title": "选择工具",
		"required": True,
		"order": 1,
		"options": [
			{"option_id": "opt1", "text": "工具1"},
			{"option_id": "opt2", "text": "工具2"},
			{"option_id": "opt3", "text": "工具3"},
		],
		"validation": {"min_selected": 1, "max_selected": 2},
	}]
	refs = convert_to_refs(ctx.db, ctx.auth.user_id, raw_q)
	client.put(f"/surveys/{survey_id}", json={"questions": refs})
	client.post(f"/surveys/{survey_id}/publish")

	submit_resp = client.post(
		"/responses",
		json={
			"survey_id": survey_id,
			"access_code": access_code,
			"answers": [{"question_id": "q1", "answer": ["opt1", "opt2", "opt3"]}],
		},
	)

	assert submit_resp.status_code == 400
	assert submit_resp.json()["code"] == 3001
	assert "最多" in submit_resp.json()["message"]


def test_number_input_min_value_validation_should_fail(api_client):
	client, ctx = api_client

	create_resp = client.post(
		"/surveys",
		json={"title": "数字最小值测试", "settings": {"allow_anonymous": True, "allow_multiple": False}},
	)
	survey_id = create_resp.json()["data"]["survey_id"]
	access_code = create_resp.json()["data"]["access_code"]

	raw_q = [{
		"question_id": "q1",
		"type": "number_input",
		"title": "年龄",
		"required": True,
		"order": 1,
		"validation": {"min_value": 0, "max_value": 120, "integer_only": True},
	}]
	refs = convert_to_refs(ctx.db, ctx.auth.user_id, raw_q)
	client.put(f"/surveys/{survey_id}", json={"questions": refs})
	client.post(f"/surveys/{survey_id}/publish")

	submit_resp = client.post(
		"/responses",
		json={
			"survey_id": survey_id,
			"access_code": access_code,
			"answers": [{"question_id": "q1", "answer": -5}],
		},
	)

	assert submit_resp.status_code == 400
	assert submit_resp.json()["code"] == 3001
	assert "最小值" in submit_resp.json()["message"] or "不能小于" in submit_resp.json()["message"]


def test_number_input_max_value_validation_should_fail(api_client):
	client, ctx = api_client

	create_resp = client.post(
		"/surveys",
		json={"title": "数字最大值测试", "settings": {"allow_anonymous": True, "allow_multiple": False}},
	)
	survey_id = create_resp.json()["data"]["survey_id"]
	access_code = create_resp.json()["data"]["access_code"]

	raw_q = [{
		"question_id": "q1",
		"type": "number_input",
		"title": "年龄",
		"required": True,
		"order": 1,
		"validation": {"min_value": 0, "max_value": 120, "integer_only": True},
	}]
	refs = convert_to_refs(ctx.db, ctx.auth.user_id, raw_q)
	client.put(f"/surveys/{survey_id}", json={"questions": refs})
	client.post(f"/surveys/{survey_id}/publish")

	submit_resp = client.post(
		"/responses",
		json={
			"survey_id": survey_id,
			"access_code": access_code,
			"answers": [{"question_id": "q1", "answer": 150}],
		},
	)

	assert submit_resp.status_code == 400
	assert submit_resp.json()["code"] == 3001
	assert "最大值" in submit_resp.json()["message"] or "不能大于" in submit_resp.json()["message"]


def test_get_response_list_by_creator(api_client):
	client, ctx = api_client
	survey_id, access_code = _prepare_published_survey_with_logic(client, ctx)

	responder = ctx.create_user("responder")
	ctx.switch_user(responder, "responder")

	client.post(
		"/responses",
		json={
			"survey_id": survey_id,
			"access_code": access_code,
			"answers": [
				{"question_id": "q1", "answer": "opt_yes"},
				{"question_id": "q3", "answer": 5},
			],
			"is_anonymous": False,
		},
	)

	creator_id = ctx.db.surveys.find_one({"access_code": access_code})["creator_id"]
	ctx.switch_user(str(creator_id), "creator")

	list_resp = client.get(f"/surveys/{survey_id}/responses")
	assert list_resp.status_code == 200
	data = list_resp.json()["data"]
	assert isinstance(data, list)
	assert len(data) >= 1
	assert data[0]["response_id"] is not None


def test_get_response_detail_by_creator(api_client):
	client, ctx = api_client
	survey_id, access_code = _prepare_published_survey_with_logic(client, ctx)

	responder = ctx.create_user("responder")
	ctx.switch_user(responder, "responder")

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
		},
	)
	response_id = submit_resp.json()["data"]["response_id"]

	creator_id = ctx.db.surveys.find_one({"access_code": access_code})["creator_id"]
	ctx.switch_user(str(creator_id), "creator")

	detail_resp = client.get(f"/responses/{response_id}")
	assert detail_resp.status_code == 200
	data = detail_resp.json()["data"]
	assert data["response_id"] == response_id
	assert data["survey_id"] == survey_id
	assert len(data["answers"]) == 2
