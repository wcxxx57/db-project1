"""题目域测试（第二阶段新增）"""

from tests.conftest import convert_to_refs


def test_create_question_success(api_client):
    """测试创建题目成功"""
    client, ctx = api_client

    resp = client.post(
        "/questions",
        json={
            "type": "single_choice",
            "title": "你的年龄段",
            "required": True,
            "options": [
                {"option_id": "opt1", "text": "18以下"},
                {"option_id": "opt2", "text": "18-30"},
            ],
        },
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "question_id" in data
    assert data["version_number"] == 1


def test_get_my_questions(api_client):
    """测试查询我创建的题目"""
    client, ctx = api_client

    client.post("/questions", json={"type": "text_input", "title": "题目A"})
    client.post("/questions", json={"type": "text_input", "title": "题目B"})

    resp = client.get("/questions/my")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 2


def test_get_question_detail(api_client):
    """测试查询题目详情"""
    client, ctx = api_client

    create_resp = client.post(
        "/questions",
        json={"type": "number_input", "title": "评分", "validation": {"min_value": 1, "max_value": 10}},
    )
    qid = create_resp.json()["data"]["question_id"]

    detail_resp = client.get(f"/questions/{qid}")
    assert detail_resp.status_code == 200
    data = detail_resp.json()["data"]
    assert data["question_id"] == qid
    assert data["latest_version_number"] == 1
    assert len(data["versions"]) == 1
    assert data["versions"][0]["title"] == "评分"


def test_create_new_version(api_client):
    """测试创建题目新版本"""
    client, ctx = api_client

    create_resp = client.post("/questions", json={"type": "text_input", "title": "v1标题"})
    qid = create_resp.json()["data"]["question_id"]

    version_resp = client.post(
        f"/questions/{qid}/versions",
        json={"type": "text_input", "title": "v2标题", "parent_version_number": 1},
    )
    assert version_resp.status_code == 200
    data = version_resp.json()["data"]
    assert data["version_number"] == 2

    detail_resp = client.get(f"/questions/{qid}")
    detail = detail_resp.json()["data"]
    assert detail["latest_version_number"] == 2
    assert len(detail["versions"]) == 2


def test_get_version_history(api_client):
    """测试查询版本历史"""
    client, ctx = api_client

    create_resp = client.post("/questions", json={"type": "text_input", "title": "v1"})
    qid = create_resp.json()["data"]["question_id"]
    client.post(f"/questions/{qid}/versions", json={"type": "text_input", "title": "v2", "parent_version_number": 1})
    client.post(f"/questions/{qid}/versions", json={"type": "text_input", "title": "v3", "parent_version_number": 2})

    resp = client.get(f"/questions/{qid}/versions")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 3
    assert data[0]["version_number"] == 1
    assert data[2]["version_number"] == 3


def test_restore_version(api_client):
    """测试恢复旧版本（创建新版本）"""
    client, ctx = api_client

    create_resp = client.post("/questions", json={"type": "text_input", "title": "原始题目"})
    qid = create_resp.json()["data"]["question_id"]
    client.post(f"/questions/{qid}/versions", json={"type": "text_input", "title": "修改后的题目", "parent_version_number": 1})

    restore_resp = client.post(f"/questions/{qid}/versions/1/restore")
    assert restore_resp.status_code == 200
    data = restore_resp.json()["data"]
    assert data["version_number"] == 3

    detail = client.get(f"/questions/{qid}").json()["data"]
    assert detail["latest_version_number"] == 3
    assert detail["versions"][2]["title"] == "原始题目"
    assert detail["versions"][2]["parent_version_number"] == 1


def test_share_question(api_client):
    """测试共享题目"""
    client, ctx = api_client

    other_id = ctx.create_user("teammate")

    create_resp = client.post("/questions", json={"type": "text_input", "title": "共享题目"})
    qid = create_resp.json()["data"]["question_id"]

    share_resp = client.post(f"/questions/{qid}/share", json={"username": "teammate"})
    assert share_resp.status_code == 200

    # 切换到 teammate 查看共享给我的题目
    ctx.switch_user(other_id, "teammate")
    shared_resp = client.get("/questions/shared")
    assert shared_resp.status_code == 200
    data = shared_resp.json()["data"]
    assert len(data) == 1
    assert data[0]["question_id"] == qid


def test_unshare_question(api_client):
    """测试取消共享"""
    client, ctx = api_client

    other_id = ctx.create_user("teammate")
    creator_id = ctx.auth.user_id

    create_resp = client.post("/questions", json={"type": "text_input", "title": "取消共享"})
    qid = create_resp.json()["data"]["question_id"]

    client.post(f"/questions/{qid}/share", json={"username": "teammate"})
    client.post(f"/questions/{qid}/unshare", json={"username": "teammate"})

    ctx.switch_user(other_id, "teammate")
    shared_resp = client.get("/questions/shared")
    assert len(shared_resp.json()["data"]) == 0


def test_add_to_bank_and_query(api_client):
    """测试加入题库和查询题库"""
    client, ctx = api_client

    create_resp = client.post("/questions", json={"type": "text_input", "title": "题库题目"})
    qid = create_resp.json()["data"]["question_id"]

    bank_resp = client.post(f"/questions/{qid}/bank")
    assert bank_resp.status_code == 200

    query_resp = client.get("/questions/bank")
    assert query_resp.status_code == 200
    data = query_resp.json()["data"]
    assert len(data) == 1
    assert data[0]["question_id"] == qid


def test_remove_from_bank(api_client):
    """测试移出题库"""
    client, ctx = api_client

    create_resp = client.post("/questions", json={"type": "text_input", "title": "移出题库"})
    qid = create_resp.json()["data"]["question_id"]

    client.post(f"/questions/{qid}/bank")
    client.delete(f"/questions/{qid}/bank")

    query_resp = client.get("/questions/bank")
    assert len(query_resp.json()["data"]) == 0


def test_question_usage(api_client):
    """测试查看题目使用情况"""
    client, ctx = api_client

    create_resp = client.post(
        "/questions",
        json={"type": "single_choice", "title": "使用情况测试", "options": [{"option_id": "opt1", "text": "选项1"}]},
    )
    qid = create_resp.json()["data"]["question_id"]

    # 创建问卷并引用该题目
    survey_resp = client.post("/surveys", json={"title": "使用问卷", "settings": {"allow_anonymous": True, "allow_multiple": False}})
    survey_id = survey_resp.json()["data"]["survey_id"]
    client.put(
        f"/surveys/{survey_id}",
        json={
            "questions": [
                {"question_id": "q1", "order": 1, "question_ref_id": qid, "version_number": 1}
            ]
        },
    )

    usage_resp = client.get(f"/questions/{qid}/usage")
    assert usage_resp.status_code == 200
    data = usage_resp.json()["data"]
    assert len(data) == 1
    assert data[0]["survey_id"] == survey_id


def test_delete_question_success(api_client):
    """测试删除未被发布问卷使用的题目"""
    client, ctx = api_client

    create_resp = client.post("/questions", json={"type": "text_input", "title": "可删除题目"})
    qid = create_resp.json()["data"]["question_id"]

    delete_resp = client.delete(f"/questions/{qid}")
    assert delete_resp.status_code == 200

    detail_resp = client.get(f"/questions/{qid}")
    assert detail_resp.status_code == 404


def test_delete_question_in_use_by_published_survey_should_fail(api_client):
    """测试删除被已发布问卷使用的题目应失败"""
    client, ctx = api_client

    create_resp = client.post(
        "/questions",
        json={"type": "text_input", "title": "不可删除题目"},
    )
    qid = create_resp.json()["data"]["question_id"]

    survey_resp = client.post("/surveys", json={"title": "发布问卷", "settings": {"allow_anonymous": True, "allow_multiple": False}})
    survey_id = survey_resp.json()["data"]["survey_id"]
    client.put(
        f"/surveys/{survey_id}",
        json={"questions": [{"question_id": "q1", "order": 1, "question_ref_id": qid, "version_number": 1}]},
    )
    client.post(f"/surveys/{survey_id}/publish")

    delete_resp = client.delete(f"/questions/{qid}")
    assert delete_resp.status_code == 400
    assert delete_resp.json()["code"] == 4003


def test_different_surveys_use_different_versions(api_client):
    """测试不同问卷可以引用同一题目的不同版本"""
    client, ctx = api_client

    create_resp = client.post(
        "/questions",
        json={"type": "text_input", "title": "版本1"},
    )
    qid = create_resp.json()["data"]["question_id"]
    client.post(f"/questions/{qid}/versions", json={"type": "text_input", "title": "版本2", "parent_version_number": 1})

    # 问卷 A 引用 v1
    sa = client.post("/surveys", json={"title": "问卷A", "settings": {"allow_anonymous": True, "allow_multiple": False}})
    sa_id = sa.json()["data"]["survey_id"]
    client.put(f"/surveys/{sa_id}", json={"questions": [{"question_id": "q1", "order": 1, "question_ref_id": qid, "version_number": 1}]})

    # 问卷 B 引用 v2
    sb = client.post("/surveys", json={"title": "问卷B", "settings": {"allow_anonymous": True, "allow_multiple": False}})
    sb_id = sb.json()["data"]["survey_id"]
    client.put(f"/surveys/{sb_id}", json={"questions": [{"question_id": "q1", "order": 1, "question_ref_id": qid, "version_number": 2}]})

    # 检查解析后的内容
    detail_a = client.get(f"/surveys/{sa_id}").json()["data"]
    detail_b = client.get(f"/surveys/{sb_id}").json()["data"]

    assert detail_a["questions"][0]["title"] == "版本1"
    assert detail_b["questions"][0]["title"] == "版本2"


def test_shared_user_can_use_question_in_survey(api_client):
    """测试被共享者可以在自己的问卷中使用共享的题目"""
    client, ctx = api_client

    # 创建者创建题目并共享
    other_id = ctx.create_user("teammate")

    create_resp = client.post(
        "/questions",
        json={"type": "text_input", "title": "共享使用"},
    )
    qid = create_resp.json()["data"]["question_id"]
    client.post(f"/questions/{qid}/share", json={"username": "teammate"})

    # 切换到 teammate，创建问卷并引用共享题目
    ctx.switch_user(other_id, "teammate")
    survey_resp = client.post("/surveys", json={"title": "协作问卷", "settings": {"allow_anonymous": True, "allow_multiple": False}})
    survey_id = survey_resp.json()["data"]["survey_id"]

    update_resp = client.put(
        f"/surveys/{survey_id}",
        json={"questions": [{"question_id": "q1", "order": 1, "question_ref_id": qid, "version_number": 1}]},
    )
    assert update_resp.status_code == 200
