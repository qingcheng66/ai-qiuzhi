"""公司工作台路由：公司/岗位/投递/面试 CRUD + 10 阶段状态机 + 统计"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core import stages
from app.database import get_db
from app.models.company import Application, Company, Interview, Position
from app.schemas.company import (
    ApplicationCreate,
    ApplicationDetail,
    ApplicationOut,
    CompanyCreate,
    CompanyOut,
    CompanyUpdate,
    InterviewCreate,
    InterviewOut,
    PositionCreate,
    PositionOut,
    StageAdvance,
)

router = APIRouter(prefix="/api", tags=["workspace"])


def _uid(user_id: int | None) -> int:
    return user_id or 1


def _ensure_company(db: Session, pk: int, uid: int) -> Company:
    o = db.get(Company, pk)
    if not o or o.user_id != uid:
        raise HTTPException(status_code=404, detail="公司不存在")
    return o


def _ensure_position(db: Session, pk: int, uid: int) -> Position:
    o = db.get(Position, pk)
    if not o or o.user_id != uid:
        raise HTTPException(status_code=404, detail="岗位不存在")
    return o


def _ensure_application(db: Session, pk: int, uid: int) -> Application:
    o = db.get(Application, pk)
    if not o or o.user_id != uid:
        raise HTTPException(status_code=404, detail="投递不存在")
    return o


# ---------- 公司 ----------


@router.get("/companies", response_model=list[CompanyOut])
def list_companies(user_id: int = 1, db: Session = Depends(get_db)):
    return db.query(Company).filter(Company.user_id == user_id).order_by(Company.id.desc()).all()


@router.post("/companies", response_model=CompanyOut)
def create_company(req: CompanyCreate, db: Session = Depends(get_db)):
    req.user_id = _uid(req.user_id)
    o = Company(**req.model_dump())
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


@router.get("/companies/{pk}", response_model=CompanyOut)
def get_company(pk: int, user_id: int = 1, db: Session = Depends(get_db)):
    return _ensure_company(db, pk, _uid(user_id))


@router.put("/companies/{pk}", response_model=CompanyOut)
def update_company(pk: int, req: CompanyUpdate, user_id: int = 1, db: Session = Depends(get_db)):
    o = _ensure_company(db, pk, _uid(user_id))
    for k, v in req.model_dump().items():
        if v is not None:
            setattr(o, k, v)
    db.commit()
    db.refresh(o)
    return o


@router.delete("/companies/{pk}")
def delete_company(pk: int, user_id: int = 1, db: Session = Depends(get_db)):
    o = _ensure_company(db, pk, _uid(user_id))
    db.delete(o)
    db.commit()
    return {"deleted": pk}


# ---------- 岗位 ----------


@router.get("/positions", response_model=list[PositionOut])
def list_positions(company_id: int | None = None, user_id: int = 1, db: Session = Depends(get_db)):
    q = db.query(Position).filter(Position.user_id == user_id)
    if company_id is not None:
        q = q.filter(Position.company_id == company_id)
    return q.order_by(Position.id.desc()).all()


@router.post("/positions", response_model=PositionOut)
def create_position(req: PositionCreate, db: Session = Depends(get_db)):
    req.user_id = _uid(req.user_id)
    # 校验公司归属
    _ensure_company(db, req.company_id, req.user_id)
    o = Position(**req.model_dump())
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


@router.get("/positions/{pk}", response_model=PositionOut)
def get_position(pk: int, user_id: int = 1, db: Session = Depends(get_db)):
    return _ensure_position(db, pk, _uid(user_id))


@router.put("/positions/{pk}", response_model=PositionOut)
def update_position(pk: int, req: PositionCreate, user_id: int = 1, db: Session = Depends(get_db)):
    o = _ensure_position(db, pk, _uid(user_id))
    for k, v in req.model_dump().items():
        setattr(o, k, v)
    db.commit()
    db.refresh(o)
    return o


@router.delete("/positions/{pk}")
def delete_position(pk: int, user_id: int = 1, db: Session = Depends(get_db)):
    o = _ensure_position(db, pk, _uid(user_id))
    db.delete(o)
    db.commit()
    return {"deleted": pk}


# ---------- 投递 ----------


@router.get("/applications", response_model=list[ApplicationDetail])
def list_applications(position_id: int | None = None, user_id: int = 1, db: Session = Depends(get_db)):
    q = db.query(Application).options(joinedload(Application.position).joinedload(Position.company))
    q = q.filter(Application.user_id == user_id)
    if position_id is not None:
        q = q.filter(Application.position_id == position_id)
    rows = q.order_by(Application.applied_date.desc()).all()
    out = []
    for a in rows:
        d = ApplicationDetail.model_validate(a)
        d.position = PositionOut.model_validate(a.position)
        d.company = CompanyOut.model_validate(a.position.company)
        d.interviews = [InterviewOut.model_validate(i) for i in a.interviews]
        out.append(d)
    return out


@router.post("/applications", response_model=ApplicationOut)
def create_application(req: ApplicationCreate, db: Session = Depends(get_db)):
    req.user_id = _uid(req.user_id)
    _ensure_position(db, req.position_id, req.user_id)
    o = Application(
        position_id=req.position_id,
        user_id=req.user_id,
        current_stage=req.current_stage,
        notes=req.notes,
        stages=stages.default_stages(),
        applied_date=req.applied_date or datetime.utcnow(),
    )
    o.stages = {**o.stages, stages.STAGE_KEYS[req.current_stage]: {"status": "active", "completed_at": datetime.utcnow().isoformat()}}
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


@router.get("/applications/{pk}", response_model=ApplicationDetail)
def get_application(pk: int, user_id: int = 1, db: Session = Depends(get_db)):
    a = _ensure_application(db, pk, _uid(user_id))
    d = ApplicationDetail.model_validate(a)
    if a.position:
        d.position = PositionOut.model_validate(a.position)
        if a.position.company:
            d.company = CompanyOut.model_validate(a.position.company)
    d.interviews = [InterviewOut.model_validate(i) for i in a.interviews]
    return d


@router.post("/applications/{pk}/stage", response_model=ApplicationOut)
def advance_stage(pk: int, req: StageAdvance, user_id: int = 1, db: Session = Depends(get_db)):
    """推进阶段状态机。target 可选：不传则 next，传入则跳到目标阶段。

    - 回退(target < current)：保留已完成的阶段，把目标阶段置为 active 重新进行
    - 前进：所有低于目标的阶段标记 completed，目标阶段标记 active
    """
    a = _ensure_application(db, pk, _uid(user_id))
    target = stages.advance_stage(a.current_stage, req.target)
    now = datetime.utcnow().isoformat()

    # 深拷贝，避免共享嵌套对象；SQLAlchemy JSON 列对 nested in-place 修改不追踪
    import copy

    stage_data: dict = copy.deepcopy(a.stages or {})
    new_key = stages.STAGE_KEYS[target]

    # 所有小于 target 的阶段标记 completed
    for i in range(target):
        k = stages.STAGE_KEYS[i]
        stage_data.setdefault(k, {"status": "pending", "completed_at": None})
        stage_data[k]["status"] = "completed"
        stage_data[k]["completed_at"] = stage_data[k].get("completed_at") or now

    # 目标阶段置 active（回退时重置为待重新进行）
    stage_data.setdefault(new_key, {"status": "pending", "completed_at": None})
    stage_data[new_key]["status"] = "active"
    stage_data[new_key]["completed_at"] = None

    # 高于目标的已完成阶段保持原样（不降级），防止回退后丢失历史
    if target > a.current_stage:
        for i in range(target + 1, stages.MAX_STAGE + 1):
            k = stages.STAGE_KEYS[i]
            if k in stage_data and stage_data[k]["status"] == "completed":
                stage_data[k]["status"] = "pending"

    a.stages = stage_data
    a.current_stage = target
    db.commit()
    db.refresh(a)
    return a


@router.put("/applications/{pk}", response_model=ApplicationOut)
def update_application(pk: int, req: ApplicationCreate, user_id: int = 1, db: Session = Depends(get_db)):
    a = _ensure_application(db, pk, _uid(user_id))
    for k, v in req.model_dump().items():
        if v is not None:
            setattr(a, k, v)
    db.commit()
    db.refresh(a)
    return a


@router.delete("/applications/{pk}")
def delete_application(pk: int, user_id: int = 1, db: Session = Depends(get_db)):
    a = _ensure_application(db, pk, _uid(user_id))
    db.delete(a)
    db.commit()
    return {"deleted": pk}


# ---------- 面试 ----------


@router.post("/interviews", response_model=InterviewOut)
def create_interview(req: InterviewCreate, db: Session = Depends(get_db)):
    a = _ensure_application(db, req.application_id, _uid(1))
    o = Interview(**req.model_dump())
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


@router.put("/interviews/{pk}", response_model=InterviewOut)
def update_interview(pk: int, req: InterviewCreate, db: Session = Depends(get_db)):
    o = db.get(Interview, pk)
    if not o:
        raise HTTPException(status_code=404, detail="面试记录不存在")
    for k, v in req.model_dump().items():
        setattr(o, k, v)
    db.commit()
    db.refresh(o)
    return o


@router.delete("/interviews/{pk}")
def delete_interview(pk: int, db: Session = Depends(get_db)):
    o = db.get(Interview, pk)
    if not o:
        raise HTTPException(status_code=404, detail="面试记录不存在")
    db.delete(o)
    db.commit()
    return {"deleted": pk}


# ---------- 统计 ----------


@router.get("/stats")
def stats(user_id: int = 1, db: Session = Depends(get_db)):
    uid = _uid(user_id)

    by_stage = {f"{i}:{stages.STAGES[i]}": 0 for i in range(stages.MAX_STAGE + 1)}
    rows = (
        db.query(Application.current_stage, func.count(Application.id))
        .filter(Application.user_id == uid)
        .group_by(Application.current_stage)
        .all()
    )
    for stage_idx, cnt in rows:
        by_stage[f"{stage_idx}:{stages.STAGES[stage_idx]}"] = cnt

    total_applications = sum(by_stage.values())
    offers = by_stage.get(f"{stages.MAX_STAGE}:{stages.STAGES[stages.MAX_STAGE]}", 0)

    # 每周投递数（近 8 周）
    now = datetime.utcnow()
    weekly = []
    for i in range(7, -1, -1):
        start = now - timedelta(days=i * 7 + 7)
        end = now - timedelta(days=i * 7)
        cnt = (
            db.query(func.count(Application.id))
            .filter(Application.user_id == uid, Application.applied_date >= start, Application.applied_date < end)
            .scalar()
        )
        weekly.append({"week": start.strftime("%m-%d"), "count": cnt})

    recent = (
        db.query(Application)
        .filter(Application.user_id == uid)
        .order_by(Application.applied_date.desc())
        .limit(10)
        .all()
    )
    recent_out = []
    for a in recent:
        recent_out.append(
            {
                "id": a.id,
                "company": a.position.company.name if a.position and a.position.company else "",
                "title": a.position.title if a.position else "",
                "current_stage": a.current_stage,
                "stage_name": stages.STAGES[a.current_stage],
                "applied_date": a.applied_date.isoformat() if a.applied_date else None,
            }
        )

    return {
        "total_applications": total_applications,
        "active_applications": total_applications - offers,
        "offers": offers,
        "offer_rate": round(offers / total_applications, 3) if total_applications else 0,
        "by_stage": by_stage,
        "weekly_applications": weekly,
        "recent": recent_out,
    }


@router.get("/stages/meta")
def stages_meta():
    return {"stages": stages.STAGES, "keys": stages.STAGE_KEYS, "max": stages.MAX_STAGE}