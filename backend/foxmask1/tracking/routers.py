# foxmask/tracking/routers.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from foxmask.auth.dependencies import get_current_user
from foxmask.auth.schemas import User
from foxmask.core.tracking import tracking_service, EventType, AuditEvent

router = APIRouter(prefix="/tracking", tags=["tracking"])

@router.get("/events", response_model=List[AuditEvent])
async def get_events(
    event_type: Optional[EventType] = Query(None, description="过滤事件类型"),
    resource_type: Optional[str] = Query(None, description="过滤资源类型"),
    resource_id: Optional[str] = Query(None, description="过滤资源ID"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    limit: int = Query(100, description="返回结果数量限制"),
    skip: int = Query(0, description="跳过结果数量"),
    current_user: User = Depends(get_current_user)
):
    """获取审计事件"""
    events = await tracking_service.get_events(
        user_id=current_user.id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        skip=skip
    )
    return events

@router.get("/events/my-activity", response_model=List[AuditEvent])
async def get_my_activity(
    event_type: Optional[EventType] = Query(None, description="过滤事件类型"),
    limit: int = Query(100, description="返回结果数量限制"),
    skip: int = Query(0, description="跳过结果数量"),
    current_user: User = Depends(get_current_user)
):
    """获取当前用户的活动记录"""
    events = await tracking_service.get_events(
        user_id=current_user.id,
        event_type=event_type,
        limit=limit,
        skip=skip
    )
    return events

@router.get("/events/user/{user_id}", response_model=List[AuditEvent])
async def get_user_events(
    user_id: str,
    event_type: Optional[EventType] = Query(None, description="过滤事件类型"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    limit: int = Query(100, description="返回结果数量限制"),
    skip: int = Query(0, description="跳过结果数量"),
    current_user: User = Depends(get_current_user)
):
    """获取指定用户的活动记录（需要管理员权限）"""
    # TODO: 添加管理员权限检查
    events = await tracking_service.get_events(
        user_id=user_id,
        event_type=event_type,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        skip=skip
    )
    return events

@router.get("/stats/user-activity")
async def get_user_activity_stats(
    days: int = Query(30, description="统计天数"),
    current_user: User = Depends(get_current_user)
):
    """获取用户活动统计"""
    stats = await tracking_service.get_user_activity_stats(
        user_id=current_user.id,
        days=days
    )
    return stats

@router.get("/stats/system-activity")
async def get_system_activity_stats(
    days: int = Query(7, description="统计天数"),
    current_user: User = Depends(get_current_user)
):
    """获取系统活动统计（需要管理员权限）"""
    # TODO: 添加管理员权限检查
    from datetime import timedelta
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    # 获取事件类型统计
    pipeline = [
        {
            "$match": {
                "timestamp": {"$gte": start_time, "$lte": end_time}
            }
        },
        {
            "$group": {
                "_id": "$event_type",
                "count": {"$sum": 1}
            }
        }
    ]
    
    db = tracking_service.db
    results = await db.audit_events.aggregate(pipeline).to_list(None)
    
    # 获取用户活动统计
    user_pipeline = [
        {
            "$match": {
                "timestamp": {"$gte": start_time, "$lte": end_time}
            }
        },
        {
            "$group": {
                "_id": "$user_id",
                "count": {"$sum": 1},
                "username": {"$first": "$username"}
            }
        },
        {
            "$sort": {"count": -1}
        },
        {
            "$limit": 10
        }
    ]
    
    user_results = await db.audit_events.aggregate(user_pipeline).to_list(None)
    
    return {
        "period": f"last_{days}_days",
        "start_time": start_time,
        "end_time": end_time,
        "events_by_type": {result["_id"]: result["count"] for result in results},
        "top_users": [
            {
                "user_id": result["_id"],
                "username": result.get("username", "Unknown"),
                "event_count": result["count"]
            }
            for result in user_results
        ],
        "total_events": sum(result["count"] for result in results)
    }