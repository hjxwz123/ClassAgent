import json
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.errors import not_found
from app.core.responses import success_response
from app.db.models import User
from app.db.session import get_db
from app.schemas.admin import (
    AdminUserCreateRequest,
    AdminUserUpdateRequest,
    CourseTakeoverRequest,
    ModelConfigRequest,
    PasswordResetByAdminRequest,
    ServiceConfigRequest,
    SystemSettingUpdateRequest,
)
from app.schemas.common import UserSummary
from app.services.admin import (
    activate_course_admin,
    assert_admin,
    create_admin_user,
    create_backup,
    export_config_bundle,
    course_summary_admin,
    deactivate_course_admin,
    delete_backup,
    delete_model_config,
    delete_service_config,
    get_admin_dashboard,
    get_backup_summary,
    get_course_detail_admin,
    get_course_stats,
    get_material_stats,
    get_model_usage_stats,
    get_monitoring_overview,
    get_monitoring_timeseries,
    get_service_health,
    get_user_detail_admin,
    get_user_stats,
    list_backups,
    list_courses_admin,
    list_error_logs,
    list_login_logs,
    list_materials_admin,
    list_model_configs,
    list_operation_logs,
    list_user_summaries_admin,
    list_service_configs,
    list_system_settings,
    material_summary_admin,
    mark_error_log_resolved,
    qa_quality_overview,
    remove_material_admin,
    reset_user_password,
    restore_default_system_settings,
    restore_backup,
    save_model_config,
    save_service_config,
    soft_delete_user,
    takeover_course,
    test_model_config,
    test_all_services,
    test_service_config,
    update_system_setting,
    update_user,
    verify_backup,
)


router = APIRouter()


def sa_dict(item):
    data = dict(item.__dict__)
    data.pop("_sa_instance_state", None)
    return data


@router.get("/dashboard")
def get_dashboard_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    activity_days: Annotated[int, Query(description="活跃趋势天数，支持 7、30、90")] = 30,
):
    assert_admin(user)
    return success_response(data=get_admin_dashboard(db, activity_days=int(activity_days)), request_id=request.state.request_id)


@router.get("/qa-quality")
def get_qa_quality_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    days: Annotated[int, Query(description="统计窗口天数，1-365，服务端夹取")] = 30,
    course_id: Annotated[int | None, Query(description="可选课程过滤")] = None,
):
    assert_admin(user)
    return success_response(data=qa_quality_overview(db, days=days, course_id=course_id), request_id=request.state.request_id)


@router.get("/service-health")
def get_service_health_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    return success_response(data=get_service_health(db), request_id=request.state.request_id)


@router.post("/service-health/test-all")
def test_all_services_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    return success_response(data=test_all_services(db), request_id=request.state.request_id)


@router.get("/users/stats")
def get_user_stats_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    return success_response(data=get_user_stats(db), request_id=request.state.request_id)


@router.get("/users")
def list_users_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    role: str | None = Query(default=None),
    status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
):
    assert_admin(user)
    return success_response(data=list_user_summaries_admin(db, role=role, status=status, keyword=keyword), request_id=request.state.request_id)


@router.post("/users/admin")
def create_admin_user_endpoint(
    payload: AdminUserCreateRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    created_user = create_admin_user(
        db,
        email=payload.email,
        password=payload.password,
        nickname=payload.nickname,
        role=payload.role.value,
        student_no=payload.student_no,
        employee_no=payload.employee_no,
        actor_id=user.id,
    )
    return success_response(data=UserSummary.model_validate(created_user).model_dump(mode="json"), request_id=request.state.request_id)


@router.get("/users/{user_id}")
def get_user_detail_admin_endpoint(
    user_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    return success_response(data=get_user_detail_admin(db, user_id=user_id), request_id=request.state.request_id)


@router.patch("/users/{user_id}")
def update_user_endpoint(
    user_id: int,
    payload: AdminUserUpdateRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    updated = update_user(db, user_id=user_id, status=payload.status, role=payload.role, actor_id=user.id)
    return success_response(data=UserSummary.model_validate(updated).model_dump(mode="json"), request_id=request.state.request_id)


@router.post("/users/{user_id}/reset-password")
def reset_user_password_endpoint(
    user_id: int,
    payload: PasswordResetByAdminRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    updated = reset_user_password(db, user_id=user_id, new_password=payload.new_password, actor_id=user.id)
    return success_response(data=UserSummary.model_validate(updated).model_dump(mode="json"), request_id=request.state.request_id)


@router.delete("/users/{user_id}")
def delete_user_endpoint(
    user_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    soft_delete_user(db, user_id=user_id, actor_id=user.id)
    return success_response(message="用户已删除", request_id=request.state.request_id)


@router.get("/courses")
def list_courses_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
):
    assert_admin(user)
    items = [course_summary_admin(db, item) for item in list_courses_admin(db, keyword=keyword, status=status)]
    return success_response(data=items, request_id=request.state.request_id)


@router.get("/courses/stats")
def get_course_stats_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    return success_response(data=get_course_stats(db), request_id=request.state.request_id)


@router.get("/courses/{course_id}")
def get_course_detail_admin_endpoint(
    course_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    return success_response(data=get_course_detail_admin(db, course_id=course_id), request_id=request.state.request_id)


@router.post("/courses/{course_id}/deactivate")
def deactivate_course_admin_endpoint(
    course_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    course = deactivate_course_admin(db, course_id=course_id)
    payload = sa_dict(course)
    return success_response(data=payload, request_id=request.state.request_id)


@router.post("/courses/{course_id}/activate")
def activate_course_admin_endpoint(
    course_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    course = activate_course_admin(db, course_id=course_id)
    payload = sa_dict(course)
    return success_response(data=payload, request_id=request.state.request_id)


@router.post("/courses/{course_id}/takeover")
def takeover_course_endpoint(
    course_id: int,
    payload: CourseTakeoverRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    course = takeover_course(db, course_id=course_id, teacher_id=payload.teacher_id, actor_id=user.id)
    output = sa_dict(course)
    return success_response(data=output, request_id=request.state.request_id)


@router.get("/materials")
def list_materials_admin_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    category: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    material_type: str | None = Query(default=None),
    teacher_id: int | None = Query(default=None),
    start_at: datetime | None = Query(default=None),
    end_at: datetime | None = Query(default=None),
):
    assert_admin(user)
    items = [
        material_summary_admin(db, item)
        for item in list_materials_admin(
            db,
            category=category,
            keyword=keyword,
            material_type=material_type,
            teacher_id=teacher_id,
            start_at=start_at,
            end_at=end_at,
        )
    ]
    return success_response(data=items, request_id=request.state.request_id)


@router.get("/materials/stats")
def get_material_stats_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    return success_response(data=get_material_stats(db), request_id=request.state.request_id)


@router.delete("/materials/{material_id}")
def delete_material_admin_endpoint(
    material_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    remove_material_admin(db, material_id=material_id, actor_id=user.id)
    return success_response(message="资料已删除", request_id=request.state.request_id)


@router.get("/model-configs")
def list_model_configs_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    return success_response(data=list_model_configs(db), request_id=request.state.request_id)


@router.post("/model-configs")
def save_model_config_endpoint(
    payload: ModelConfigRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    config = save_model_config(
        db,
        config_id=payload.config_id,
        provider=payload.provider,
        model_name=payload.model_name,
        purpose=payload.purpose,
        endpoint=payload.endpoint,
        api_key=payload.api_key,
        is_default=payload.is_default,
        extra_config=payload.extra_config,
        actor_id=user.id,
    )
    return success_response(data={"id": config.id}, request_id=request.state.request_id)


@router.post("/model-configs/{config_id}/test")
def test_model_config_endpoint(
    config_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    return success_response(data=test_model_config(db, config_id=config_id), request_id=request.state.request_id)


@router.delete("/model-configs/{config_id}")
def delete_model_config_endpoint(
    config_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    delete_model_config(db, config_id=config_id, actor_id=user.id)
    return success_response(message="模型配置已删除", request_id=request.state.request_id)


@router.get("/model-usage")
def get_model_usage_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    return success_response(data=get_model_usage_stats(db), request_id=request.state.request_id)


@router.get("/service-configs")
def list_service_configs_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    return success_response(data=list_service_configs(db), request_id=request.state.request_id)


@router.post("/service-configs")
def save_service_config_endpoint(
    payload: ServiceConfigRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    config = save_service_config(
        db,
        config_id=payload.config_id,
        service_type=payload.service_type,
        provider=payload.provider,
        name=payload.name,
        config=payload.config,
        is_enabled=payload.is_enabled,
        actor_id=user.id,
    )
    return success_response(data={"id": config.id}, request_id=request.state.request_id)


@router.post("/service-configs/{config_id}/test")
def test_service_config_endpoint(
    config_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    return success_response(data=test_service_config(db, config_id=config_id), request_id=request.state.request_id)


@router.delete("/service-configs/{config_id}")
def delete_service_config_endpoint(
    config_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    delete_service_config(db, config_id=config_id, actor_id=user.id)
    return success_response(message="服务配置已删除", request_id=request.state.request_id)


@router.get("/system-settings")
def list_system_settings_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    return success_response(data=list_system_settings(db), request_id=request.state.request_id)


@router.put("/system-settings/{key}")
def update_system_setting_endpoint(
    key: str,
    payload: SystemSettingUpdateRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    setting = update_system_setting(db, key=key, value=payload.value, actor_id=user.id)
    return success_response(
        data={"id": setting.id, "setting_key": setting.setting_key, "setting_value": setting.setting_value},
        request_id=request.state.request_id,
    )


@router.post("/system-settings/restore-defaults")
def restore_default_system_settings_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    return success_response(data=restore_default_system_settings(db, actor_id=user.id), request_id=request.state.request_id)


@router.get("/monitoring/overview")
def get_monitoring_overview_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    return success_response(data=get_monitoring_overview(db), request_id=request.state.request_id)


@router.get("/monitoring/timeseries")
def get_monitoring_timeseries_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    return success_response(data=get_monitoring_timeseries(db), request_id=request.state.request_id)


@router.get("/logs/login")
def list_login_logs_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=100, ge=1, le=500),
    user_id: int | None = Query(default=None),
    success: bool | None = Query(default=None),
    start_at: datetime | None = Query(default=None),
    end_at: datetime | None = Query(default=None),
):
    assert_admin(user)
    return success_response(
        data=[
            sa_dict(item)
            for item in list_login_logs(
                db,
                limit=limit,
                user_id=user_id,
                success=success,
                start_at=start_at,
                end_at=end_at,
            )
        ],
        request_id=request.state.request_id,
    )


@router.get("/logs/operations")
def list_operation_logs_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=100, ge=1, le=500),
    user_id: int | None = Query(default=None),
    action: str | None = Query(default=None),
    target_type: str | None = Query(default=None),
    start_at: datetime | None = Query(default=None),
    end_at: datetime | None = Query(default=None),
):
    assert_admin(user)
    return success_response(
        data=[
            sa_dict(item)
            for item in list_operation_logs(
                db,
                limit=limit,
                user_id=user_id,
                action=action,
                target_type=target_type,
                start_at=start_at,
                end_at=end_at,
            )
        ],
        request_id=request.state.request_id,
    )


@router.get("/logs/errors")
def list_error_logs_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=100, ge=1, le=500),
    level: str | None = Query(default=None),
    source: str | None = Query(default=None),
    start_at: datetime | None = Query(default=None),
    end_at: datetime | None = Query(default=None),
):
    assert_admin(user)
    return success_response(
        data=[
            sa_dict(item)
            for item in list_error_logs(db, limit=limit, level=level, source=source, start_at=start_at, end_at=end_at)
        ],
        request_id=request.state.request_id,
    )


@router.post("/logs/errors/{error_id}/resolve")
def resolve_error_log_endpoint(
    error_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    return success_response(data=mark_error_log_resolved(db, error_id=error_id, actor_id=user.id), request_id=request.state.request_id)


@router.get("/backups/summary")
def get_backup_summary_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    return success_response(data=get_backup_summary(db), request_id=request.state.request_id)


@router.get("/backups")
def list_backups_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    items = []
    for item in list_backups(db):
        data = sa_dict(item)
        if item.file_path and Path(item.file_path).exists():
            data["file_size_bytes"] = Path(item.file_path).stat().st_size
        else:
            data["file_size_bytes"] = 0
        data["backup_name"] = Path(item.file_path).stem if item.file_path else f"backup_{item.id}"
        items.append(data)
    return success_response(data=items, request_id=request.state.request_id)


@router.post("/backups")
def create_backup_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    backup = create_backup(db, trigger_user_id=user.id)
    return success_response(data=sa_dict(backup), request_id=request.state.request_id)


@router.post("/backups/{backup_id}/restore")
def restore_backup_endpoint(
    backup_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    return success_response(data=restore_backup(db, backup_id=backup_id, actor_id=user.id), request_id=request.state.request_id)


@router.post("/backups/{backup_id}/verify")
def verify_backup_endpoint(
    backup_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    return success_response(data=verify_backup(db, backup_id=backup_id), request_id=request.state.request_id)


@router.get("/backups/{backup_id}/download")
def download_backup_endpoint(
    backup_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    backup = next((item for item in list_backups(db) if item.id == backup_id), None)
    if backup is None or not backup.file_path or not Path(backup.file_path).exists():
        raise not_found("备份文件不存在")
    return FileResponse(backup.file_path, filename=Path(backup.file_path).name)


@router.get("/config/export")
def export_config_endpoint(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """只导出配置数据（模型/API 配置、服务配置、系统设置）为 JSON 文件下载。"""
    assert_admin(user)
    bundle = export_config_bundle(db, actor_id=user.id)
    payload = json.dumps(bundle, ensure_ascii=False, indent=2)
    filename = f"classagent-config-{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/backups/{backup_id}")
def delete_backup_endpoint(
    backup_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    assert_admin(user)
    delete_backup(db, backup_id=backup_id, actor_id=user.id)
    return success_response(message="备份已删除", request_id=request.state.request_id)
