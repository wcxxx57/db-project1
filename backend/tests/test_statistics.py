from tests.conftest import create_multi_type_questions


def _prepare_published_stats_survey(client):
	create_resp = client.post(
		"/surveys",
		json={"title": "统计问卷", "settings": {"allow_anonymous": True, "allow_multiple": True}},
	)
	survey_id = create_resp.json()["data"]["survey_id"]
	access_code = create_resp.json()["data"]["access_code"]

	update_resp = client.put(
		f"/surveys/{survey_id}",
		json={"questions": create_multi_type_questions()},
	)
	assert update_resp.status_code == 200

	publish_resp = client.post(f"/surveys/{survey_id}/publish")
	assert publish_resp.status_code == 200

	return survey_id, access_code


def _submit_one(client, survey_id, access_code, single, multi, text, num, is_anonymous):
	return client.post(
		"/responses",
		json={
			"survey_id": survey_id,
			"access_code": access_code,
			"answers": [
				{"question_id": "q_single", "answer": single},
				{"question_id": "q_multi", "answer": multi},
				{"question_id": "q_text", "answer": text},
				{"question_id": "q_num", "answer": num},
			],
			"is_anonymous": is_anonymous,
		},
	)


def test_get_survey_statistics_should_aggregate_all_question_types(api_client):
	client, ctx = api_client
	survey_id, access_code = _prepare_published_stats_survey(client)

	responder_1 = ctx.create_user("responder_1")
	responder_2 = ctx.create_user("responder_2")

	ctx.switch_user(responder_1, "responder_1")
	r1 = _submit_one(
		client,
		survey_id,
		access_code,
		single="opt_py",
		multi=["opt_git", "opt_ci"],
		text="建议增加实战",
		num=3,
		is_anonymous=False,
	)
	assert r1.status_code == 200

	ctx.switch_user(responder_2, "responder_2")
	r2 = _submit_one(
		client,
		survey_id,
		access_code,
		single="opt_js",
		multi=["opt_git"],
		text="很好",
		num=5,
		is_anonymous=True,
	)
	assert r2.status_code == 200

	creator_id = ctx.db.surveys.find_one({"access_code": access_code})["creator_id"]
	ctx.switch_user(str(creator_id), "creator")

	stat_resp = client.get(f"/surveys/{survey_id}/statistics")
	assert stat_resp.status_code == 200
	data = stat_resp.json()["data"]
	assert data["total_responses"] == 2

	stats_by_qid = {item["question_id"]: item for item in data["question_statistics"]}

	single_stat = stats_by_qid["q_single"]
	py_opt = next(item for item in single_stat["option_statistics"] if item["option_id"] == "opt_py")
	js_opt = next(item for item in single_stat["option_statistics"] if item["option_id"] == "opt_js")
	assert py_opt["count"] == 1
	assert js_opt["count"] == 1

	multi_stat = stats_by_qid["q_multi"]
	git_opt = next(item for item in multi_stat["option_statistics"] if item["option_id"] == "opt_git")
	ci_opt = next(item for item in multi_stat["option_statistics"] if item["option_id"] == "opt_ci")
	assert git_opt["count"] == 2
	assert ci_opt["count"] == 1

	text_stat = stats_by_qid["q_text"]
	assert "建议增加实战" in text_stat["text_responses"]
	assert "很好" in text_stat["text_responses"]

	number_stat = stats_by_qid["q_num"]["number_statistics"]
	assert number_stat["average"] == 4.0
	assert number_stat["min"] == 3
	assert number_stat["max"] == 5


def test_get_question_statistics_should_include_respondent_visibility_rules(api_client):
	client, ctx = api_client
	survey_id, access_code = _prepare_published_stats_survey(client)

	real_user = ctx.create_user("visible_user")
	anon_user = ctx.create_user("hidden_user")

	ctx.switch_user(real_user, "visible_user")
	_submit_one(
		client,
		survey_id,
		access_code,
		single="opt_py",
		multi=["opt_git"],
		text="ok",
		num=6,
		is_anonymous=False,
	)

	ctx.switch_user(anon_user, "hidden_user")
	_submit_one(
		client,
		survey_id,
		access_code,
		single="opt_py",
		multi=["opt_git"],
		text="ok2",
		num=7,
		is_anonymous=True,
	)

	creator_id = ctx.db.surveys.find_one({"access_code": access_code})["creator_id"]
	ctx.switch_user(str(creator_id), "creator")

	question_resp = client.get(f"/surveys/{survey_id}/questions/q_single/statistics")
	assert question_resp.status_code == 200
	q_data = question_resp.json()["data"]
	assert q_data["question_id"] == "q_single"

	py_option = next(item for item in q_data["option_statistics"] if item["option_id"] == "opt_py")
	respondents = py_option["respondents"]

	assert len(respondents) == 2
	assert any(r["is_anonymous"] is False and r["display_name"] == "visible_user" for r in respondents)
	assert any(r["is_anonymous"] is True and r["display_name"] == "匿名用户" for r in respondents)

