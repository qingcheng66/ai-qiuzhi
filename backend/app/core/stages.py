"""10 阶段求职状态机"""

STAGES = ["投递", "测评", "笔试", "简历评估", "一面", "二面", "三面", "HR面", "Offer评估", "Offer"]
STAGE_KEYS = [
    "applied",
    "assessment",
    "written_test",
    "resume_review",
    "interview_1",
    "interview_2",
    "interview_3",
    "hr_interview",
    "offer_eval",
    "offer",
]

MAX_STAGE = len(STAGES) - 1

# 阶段英文 key 到中文标签映射
STAGE_MAP = dict(zip(STAGE_KEYS, STAGES))


def stage_key(index: int) -> str:
    return STAGE_KEYS[index]


def stage_name(index: int) -> str:
    return STAGES[index]


def default_stages() -> dict:
    """初始化 stages json：记录每个阶段的状态"""
    return {
        key: {"status": "pending", "completed_at": None}
        for key in STAGE_KEYS
    }


def advance_stage(current: int, target: int | None = None) -> int:
    """推进阶段。target 可选任意可见（可回退到之前的可见阶段但非完成）"""
    if target is None:
        return min(current + 1, MAX_STAGE)
    if target < 0:
        target = 0
    if target > MAX_STAGE:
        target = MAX_STAGE
    return target