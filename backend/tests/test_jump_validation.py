"""跳转逻辑验证测试"""


def test_jump_target_not_exist_should_fail(api_client):
    """测试跳转目标不存在时应该失败"""
    client, _ = api_client

    create_resp = client.post(
        "/surveys",
        json={"title": "跳转目标测试", "settings": {"allow_anonymous": True, "allow_multiple": False}},
    )
    survey_id = create_resp.json()["data"]["survey_id"]

    # q1 跳转到不存在的 q999
    update_resp = client.put(
        f"/surveys/{survey_id}",
        json={
            "questions": [
                {
                    "question_id": "q1",
                    "type": "single_choice",
                    "title": "题目1",
                    "required": True,
                    "order": 1,
                    "options": [{"option_id": "opt1", "text": "选项1"}],
                    "logic": {
                        "enabled": True,
                        "rules": [
                            {
                                "condition": {"type": "select_option", "option_id": "opt1"},
                                "action": {"type": "jump_to", "target_question_id": "q999"},
                            }
                        ],
                    },
                }
            ]
        },
    )

    assert update_resp.status_code == 400
    assert update_resp.json()["code"] == 3001
    assert "q999" in update_resp.json()["message"]
    assert "不存在" in update_resp.json()["message"]


def test_forward_jump_should_fail(api_client):
    """测试向前跳转应该失败"""
    client, _ = api_client

    create_resp = client.post(
        "/surveys",
        json={"title": "向前跳转测试", "settings": {"allow_anonymous": True, "allow_multiple": False}},
    )
    survey_id = create_resp.json()["data"]["survey_id"]

    # q3 跳转到 q1（向前跳转）
    update_resp = client.put(
        f"/surveys/{survey_id}",
        json={
            "questions": [
                {
                    "question_id": "q1",
                    "type": "single_choice",
                    "title": "题目1",
                    "required": True,
                    "order": 1,
                    "options": [{"option_id": "opt1", "text": "选项1"}],
                },
                {
                    "question_id": "q2",
                    "type": "text_input",
                    "title": "题目2",
                    "required": True,
                    "order": 2,
                },
                {
                    "question_id": "q3",
                    "type": "single_choice",
                    "title": "题目3",
                    "required": True,
                    "order": 3,
                    "options": [{"option_id": "opt3", "text": "选项3"}],
                    "logic": {
                        "enabled": True,
                        "rules": [
                            {
                                "condition": {"type": "select_option", "option_id": "opt3"},
                                "action": {"type": "jump_to", "target_question_id": "q1"},
                            }
                        ],
                    },
                },
            ]
        },
    )

    assert update_resp.status_code == 400
    assert update_resp.json()["code"] == 3001
    assert "不允许向前跳转" in update_resp.json()["message"]


def test_jump_to_self_should_fail(api_client):
    """测试跳转到自己应该失败"""
    client, _ = api_client

    create_resp = client.post(
        "/surveys",
        json={"title": "自跳转测试", "settings": {"allow_anonymous": True, "allow_multiple": False}},
    )
    survey_id = create_resp.json()["data"]["survey_id"]

    update_resp = client.put(
        f"/surveys/{survey_id}",
        json={
            "questions": [
                {
                    "question_id": "q1",
                    "type": "single_choice",
                    "title": "题目1",
                    "required": True,
                    "order": 1,
                    "options": [{"option_id": "opt1", "text": "选项1"}],
                    "logic": {
                        "enabled": True,
                        "rules": [
                            {
                                "condition": {"type": "select_option", "option_id": "opt1"},
                                "action": {"type": "jump_to", "target_question_id": "q1"},
                            }
                        ],
                    },
                }
            ]
        },
    )

    assert update_resp.status_code == 400
    assert update_resp.json()["code"] == 3001
    assert "不允许向前跳转" in update_resp.json()["message"]


def test_cycle_jump_should_fail(api_client):
    """测试循环跳转应该失败（q5→q3 会被向前跳转拦截）"""
    client, _ = api_client

    create_resp = client.post(
        "/surveys",
        json={"title": "循环跳转测试", "settings": {"allow_anonymous": True, "allow_multiple": False}},
    )
    survey_id = create_resp.json()["data"]["survey_id"]

    # 构造循环：q1→q3, q3→q5, q5→q3（q5→q3 是向前跳转）
    update_resp = client.put(
        f"/surveys/{survey_id}",
        json={
            "questions": [
                {
                    "question_id": "q1",
                    "type": "single_choice",
                    "title": "题目1",
                    "required": True,
                    "order": 1,
                    "options": [{"option_id": "opt1", "text": "选项1"}],
                    "logic": {
                        "enabled": True,
                        "rules": [
                            {
                                "condition": {"type": "select_option", "option_id": "opt1"},
                                "action": {"type": "jump_to", "target_question_id": "q3"},
                            }
                        ],
                    },
                },
                {
                    "question_id": "q2",
                    "type": "text_input",
                    "title": "题目2",
                    "required": True,
                    "order": 2,
                },
                {
                    "question_id": "q3",
                    "type": "single_choice",
                    "title": "题目3",
                    "required": True,
                    "order": 3,
                    "options": [{"option_id": "opt3", "text": "选项3"}],
                    "logic": {
                        "enabled": True,
                        "rules": [
                            {
                                "condition": {"type": "select_option", "option_id": "opt3"},
                                "action": {"type": "jump_to", "target_question_id": "q5"},
                            }
                        ],
                    },
                },
                {
                    "question_id": "q4",
                    "type": "text_input",
                    "title": "题目4",
                    "required": True,
                    "order": 4,
                },
                {
                    "question_id": "q5",
                    "type": "single_choice",
                    "title": "题目5",
                    "required": True,
                    "order": 5,
                    "options": [{"option_id": "opt5", "text": "选项5"}],
                    "logic": {
                        "enabled": True,
                        "rules": [
                            {
                                "condition": {"type": "select_option", "option_id": "opt5"},
                                "action": {"type": "jump_to", "target_question_id": "q3"},
                            }
                        ],
                    },
                },
            ]
        },
    )

    assert update_resp.status_code == 400
    assert update_resp.json()["code"] == 3001
    assert "不允许向前跳转" in update_resp.json()["message"]


def test_valid_jump_logic_should_succeed(api_client):
    """测试合法的跳转逻辑应该成功"""
    client, _ = api_client

    create_resp = client.post(
        "/surveys",
        json={"title": "合法跳转测试", "settings": {"allow_anonymous": True, "allow_multiple": False}},
    )
    survey_id = create_resp.json()["data"]["survey_id"]

    # q1→q3, q3→q5（无循环，向后跳转）
    update_resp = client.put(
        f"/surveys/{survey_id}",
        json={
            "questions": [
                {
                    "question_id": "q1",
                    "type": "single_choice",
                    "title": "题目1",
                    "required": True,
                    "order": 1,
                    "options": [{"option_id": "opt1", "text": "选项1"}],
                    "logic": {
                        "enabled": True,
                        "rules": [
                            {
                                "condition": {"type": "select_option", "option_id": "opt1"},
                                "action": {"type": "jump_to", "target_question_id": "q3"},
                            }
                        ],
                    },
                },
                {
                    "question_id": "q2",
                    "type": "text_input",
                    "title": "题目2",
                    "required": True,
                    "order": 2,
                },
                {
                    "question_id": "q3",
                    "type": "single_choice",
                    "title": "题目3",
                    "required": True,
                    "order": 3,
                    "options": [{"option_id": "opt3", "text": "选项3"}],
                    "logic": {
                        "enabled": True,
                        "rules": [
                            {
                                "condition": {"type": "select_option", "option_id": "opt3"},
                                "action": {"type": "jump_to", "target_question_id": "q5"},
                            }
                        ],
                    },
                },
                {
                    "question_id": "q4",
                    "type": "text_input",
                    "title": "题目4",
                    "required": True,
                    "order": 4,
                },
                {
                    "question_id": "q5",
                    "type": "text_input",
                    "title": "题目5",
                    "required": True,
                    "order": 5,
                },
            ]
        },
    )

    assert update_resp.status_code == 200
    assert update_resp.json()["code"] == 0


def test_multiple_rules_with_different_targets_should_succeed(api_client):
    """测试多条规则跳转到不同目标应该成功"""
    client, _ = api_client

    create_resp = client.post(
        "/surveys",
        json={"title": "多规则测试", "settings": {"allow_anonymous": True, "allow_multiple": False}},
    )
    survey_id = create_resp.json()["data"]["survey_id"]

    update_resp = client.put(
        f"/surveys/{survey_id}",
        json={
            "questions": [
                {
                    "question_id": "q1",
                    "type": "number_input",
                    "title": "年龄",
                    "required": True,
                    "order": 1,
                    "logic": {
                        "enabled": True,
                        "rules": [
                            {
                                "condition": {"type": "number_compare", "operator": "lt", "value": 18},
                                "action": {"type": "end_survey"},
                            },
                            {
                                "condition": {"type": "number_compare", "operator": "gte", "value": 60},
                                "action": {"type": "jump_to", "target_question_id": "q4"},
                            },
                        ],
                    },
                },
                {
                    "question_id": "q2",
                    "type": "text_input",
                    "title": "题目2",
                    "required": True,
                    "order": 2,
                },
                {
                    "question_id": "q3",
                    "type": "text_input",
                    "title": "题目3",
                    "required": True,
                    "order": 3,
                },
                {
                    "question_id": "q4",
                    "type": "text_input",
                    "title": "题目4",
                    "required": True,
                    "order": 4,
                },
            ]
        },
    )

    assert update_resp.status_code == 200
    assert update_resp.json()["code"] == 0


def test_end_survey_action_should_not_trigger_validation(api_client):
    """测试 end_survey 动作不应触发目标验证"""
    client, _ = api_client

    create_resp = client.post(
        "/surveys",
        json={"title": "结束问卷测试", "settings": {"allow_anonymous": True, "allow_multiple": False}},
    )
    survey_id = create_resp.json()["data"]["survey_id"]

    update_resp = client.put(
        f"/surveys/{survey_id}",
        json={
            "questions": [
                {
                    "question_id": "q1",
                    "type": "single_choice",
                    "title": "题目1",
                    "required": True,
                    "order": 1,
                    "options": [{"option_id": "opt1", "text": "选项1"}],
                    "logic": {
                        "enabled": True,
                        "rules": [
                            {
                                "condition": {"type": "select_option", "option_id": "opt1"},
                                "action": {"type": "end_survey"},
                            }
                        ],
                    },
                }
            ]
        },
    )

    assert update_resp.status_code == 200
    assert update_resp.json()["code"] == 0


def test_complex_cycle_detection(api_client):
    """测试复杂循环检测（q2→q4→q2 会被向前跳转拦截）"""
    client, _ = api_client

    create_resp = client.post(
        "/surveys",
        json={"title": "复杂循环测试", "settings": {"allow_anonymous": True, "allow_multiple": False}},
    )
    survey_id = create_resp.json()["data"]["survey_id"]

    update_resp = client.put(
        f"/surveys/{survey_id}",
        json={
            "questions": [
                {
                    "question_id": "q1",
                    "type": "single_choice",
                    "title": "题目1",
                    "required": True,
                    "order": 1,
                    "options": [{"option_id": "opt1", "text": "选项1"}],
                    "logic": {
                        "enabled": True,
                        "rules": [
                            {
                                "condition": {"type": "select_option", "option_id": "opt1"},
                                "action": {"type": "jump_to", "target_question_id": "q2"},
                            }
                        ],
                    },
                },
                {
                    "question_id": "q2",
                    "type": "single_choice",
                    "title": "题目2",
                    "required": True,
                    "order": 2,
                    "options": [{"option_id": "opt2", "text": "选项2"}],
                    "logic": {
                        "enabled": True,
                        "rules": [
                            {
                                "condition": {"type": "select_option", "option_id": "opt2"},
                                "action": {"type": "jump_to", "target_question_id": "q4"},
                            }
                        ],
                    },
                },
                {
                    "question_id": "q3",
                    "type": "text_input",
                    "title": "题目3",
                    "required": True,
                    "order": 3,
                },
                {
                    "question_id": "q4",
                    "type": "single_choice",
                    "title": "题目4",
                    "required": True,
                    "order": 4,
                    "options": [{"option_id": "opt4", "text": "选项4"}],
                    "logic": {
                        "enabled": True,
                        "rules": [
                            {
                                "condition": {"type": "select_option", "option_id": "opt4"},
                                "action": {"type": "jump_to", "target_question_id": "q2"},
                            }
                        ],
                    },
                },
            ]
        },
    )

    assert update_resp.status_code == 400
    assert update_resp.json()["code"] == 3001
    assert "不允许向前跳转" in update_resp.json()["message"]


def test_no_cycle_with_multiple_paths_should_succeed(api_client):
    """测试多路径但无循环应该成功"""
    client, _ = api_client

    create_resp = client.post(
        "/surveys",
        json={"title": "多路径测试", "settings": {"allow_anonymous": True, "allow_multiple": False}},
    )
    survey_id = create_resp.json()["data"]["survey_id"]

    # q1→q3, q2→q4, q3→q5（无循环）
    update_resp = client.put(
        f"/surveys/{survey_id}",
        json={
            "questions": [
                {
                    "question_id": "q1",
                    "type": "single_choice",
                    "title": "题目1",
                    "required": True,
                    "order": 1,
                    "options": [{"option_id": "opt1", "text": "选项1"}],
                    "logic": {
                        "enabled": True,
                        "rules": [
                            {
                                "condition": {"type": "select_option", "option_id": "opt1"},
                                "action": {"type": "jump_to", "target_question_id": "q3"},
                            }
                        ],
                    },
                },
                {
                    "question_id": "q2",
                    "type": "single_choice",
                    "title": "题目2",
                    "required": True,
                    "order": 2,
                    "options": [{"option_id": "opt2", "text": "选项2"}],
                    "logic": {
                        "enabled": True,
                        "rules": [
                            {
                                "condition": {"type": "select_option", "option_id": "opt2"},
                                "action": {"type": "jump_to", "target_question_id": "q4"},
                            }
                        ],
                    },
                },
                {
                    "question_id": "q3",
                    "type": "single_choice",
                    "title": "题目3",
                    "required": True,
                    "order": 3,
                    "options": [{"option_id": "opt3", "text": "选项3"}],
                    "logic": {
                        "enabled": True,
                        "rules": [
                            {
                                "condition": {"type": "select_option", "option_id": "opt3"},
                                "action": {"type": "jump_to", "target_question_id": "q5"},
                            }
                        ],
                    },
                },
                {
                    "question_id": "q4",
                    "type": "text_input",
                    "title": "题目4",
                    "required": True,
                    "order": 4,
                },
                {
                    "question_id": "q5",
                    "type": "text_input",
                    "title": "题目5",
                    "required": True,
                    "order": 5,
                },
            ]
        },
    )

    assert update_resp.status_code == 200
    assert update_resp.json()["code"] == 0


def test_disabled_logic_should_not_trigger_validation(api_client):
    """测试禁用的跳转逻辑不应触发验证"""
    client, _ = api_client

    create_resp = client.post(
        "/surveys",
        json={"title": "禁用逻辑测试", "settings": {"allow_anonymous": True, "allow_multiple": False}},
    )
    survey_id = create_resp.json()["data"]["survey_id"]

    # logic.enabled=false，即使配置了向前跳转也不应报错
    update_resp = client.put(
        f"/surveys/{survey_id}",
        json={
            "questions": [
                {
                    "question_id": "q1",
                    "type": "single_choice",
                    "title": "题目1",
                    "required": True,
                    "order": 1,
                    "options": [{"option_id": "opt1", "text": "选项1"}],
                },
                {
                    "question_id": "q2",
                    "type": "single_choice",
                    "title": "题目2",
                    "required": True,
                    "order": 2,
                    "options": [{"option_id": "opt2", "text": "选项2"}],
                    "logic": {
                        "enabled": False,
                        "rules": [
                            {
                                "condition": {"type": "select_option", "option_id": "opt2"},
                                "action": {"type": "jump_to", "target_question_id": "q1"},
                            }
                        ],
                    },
                },
            ]
        },
    )

    assert update_resp.status_code == 200
    assert update_resp.json()["code"] == 0
