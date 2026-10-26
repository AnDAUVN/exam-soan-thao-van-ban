"""
FastAPI Server phục vụ phần mềm thi môn Soạn thảo văn bản hành chính theo Nghị định 30.
Bao gồm Cổng Sinh Viên và Cổng Giảng Viên (Quản lý Khóa - Lớp).
"""

import os
import re
import shutil
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional

from exam_engine import ExamEngine, ACTIVE_SESSIONS, COHORTS_AND_CLASSES
from gdrive_service import GDriveService
from grading_service import GradingService

app = FastAPI(title="Hệ thống thi Soạn thảo Văn bản Hành chính (Nghị định 30/2020/NĐ-CP)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(FRONTEND_DIR, exist_ok=True)

class StartExamRequest(BaseModel):
    student_id: str
    student_name: str
    sbd: Optional[str] = ""
    cohort: str = "Khóa 1"
    class_name: str = "Lớp 01 - Văn thư lưu trữ"
    duration_minutes: int = 60
    device_id: Optional[str] = ""
    device_info: Optional[str] = ""

class UnlockDeviceRequest(BaseModel):
    student_id: str

class SubmitQuizRequest(BaseModel):
    student_id: str
    answers: Dict[str, str]

class GradeContentRequest(BaseModel):
    student_id: str
    case_1_content_score: float = 0.0
    case_2_content_score: float = 0.0
    case_1_format_score: Optional[float] = None
    case_2_format_score: Optional[float] = None
    teacher_comment: str = ""

class GradingConfigRequest(BaseModel):
    action: Optional[str] = "save"
    config: Optional[Dict[str, Any]] = None

class ClassManageRequest(BaseModel):
    action: str = "add"
    cohort: str = ""
    class_name: Optional[str] = ""
    old_name: Optional[str] = ""
    new_name: Optional[str] = ""

class ExtendTimeRequest(BaseModel):
    student_id: str
    extra_minutes: int = 10

class TerminateExamRequest(BaseModel):
    student_id: str
    reason: Optional[str] = ""

class RetakeExamRequest(BaseModel):
    student_id: str
    mode: Optional[str] = "resume"
    extra_minutes: Optional[int] = 15

class ReportViolationRequest(BaseModel):
    student_id: str
    violation_type: str = "TAB_SWITCH"
    detail: str = ""

class PhaseTransitionRequest(BaseModel):
    student_id: str
    phase: str = "WORD"

class SaveRosterRequest(BaseModel):
    cohort: str
    class_name: str
    students: list

class AddStudentRosterRequest(BaseModel):
    cohort: str
    class_name: str
    sbd: Optional[str] = ""
    student_id: str
    student_name: str

class DeleteStudentRosterRequest(BaseModel):
    cohort: str
    class_name: str
    student_id: str

class SetRosterEnforceRequest(BaseModel):
    cohort: Optional[str] = ""
    class_name: Optional[str] = ""
    enforce: Optional[bool] = None
    enforced: Optional[bool] = None

class ParseRosterTextRequest(BaseModel):
    text: Optional[str] = None
    raw_text: Optional[str] = None

class ExamConfigRequest(BaseModel):
    mcq_count: Optional[int] = None
    duration_minutes: Optional[int] = None

class AddMCQRequest(BaseModel):
    question: str
    options: list
    correct_index: int = 0
    explanation: Optional[str] = ""
    group: Optional[str] = "Nghị định 30/2020/NĐ-CP"

class DeleteMCQRequest(BaseModel):
    question_id: Any

class ParseTextRequest(BaseModel):
    text: str

class ImportBatchMCQRequest(BaseModel):
    questions: list

class AddCaseRequest(BaseModel):
    bucket: str = "A"
    doc_type: str = "QUYẾT ĐỊNH"
    title: str
    context: str
    requirements: Optional[list] = []

class DeleteCaseRequest(BaseModel):
    bucket: str = "A"
    case_id: str

class ClearQuestionsRequest(BaseModel):
    target: Optional[str] = "all"

class GDriveConfigRequest(BaseModel):
    webhook_url: Optional[str] = ""
    auto_upload: Optional[bool] = True

class GDriveTestRequest(BaseModel):
    webhook_url: Optional[str] = ""

@app.get("/api/classes")
def get_classes():
    return {"status": "success", "catalog": ExamEngine.get_classes_catalog()}

@app.post("/api/teacher/classes")
def manage_classes(req: ClassManageRequest):
    action = req.action
    cohort = (req.cohort or "").strip()
    if action == "add":
        return ExamEngine.add_cohort_or_class(cohort, (req.class_name or "").strip())
    elif action == "edit_class":
        return ExamEngine.edit_class(cohort, (req.old_name or "").strip(), (req.new_name or "").strip())
    elif action == "delete_class":
        return ExamEngine.delete_class(cohort, (req.class_name or "").strip())
    elif action == "delete_cohort":
        return ExamEngine.delete_cohort(cohort)
    return {"error": "Hành động không hợp lệ"}

# ================= QUẢN LÝ DANH SÁCH THÍ SINH THEO LỚP (ROSTER) =================
@app.get("/api/teacher/roster")
def get_roster_endpoint(cohort: str = Query(...), class_name: str = Query(...)):
    enforce, roster = ExamEngine.get_class_roster(cohort, class_name)
    full_data = ExamEngine.get_full_roster_data()
    return {
        "status": "success",
        "cohort": cohort,
        "class_name": class_name,
        "enforced": enforce,
        "enforce_roster": enforce,
        "students": roster,
        "roster": roster,
        "count": len(roster),
        "total": len(roster),
        "all_rosters": full_data.get("rosters", {})
    }

@app.post("/api/teacher/roster/save")
def save_roster_endpoint(req: SaveRosterRequest):
    return ExamEngine.save_roster_for_class(req.cohort, req.class_name, req.students)

@app.post("/api/teacher/roster/add-student")
def add_student_roster_endpoint(req: AddStudentRosterRequest):
    return ExamEngine.add_student_to_roster(req.cohort, req.class_name, req.sbd or "", req.student_id, req.student_name)

@app.post("/api/teacher/roster/delete-student")
def delete_student_roster_endpoint(req: DeleteStudentRosterRequest):
    return ExamEngine.delete_student_from_roster(req.cohort, req.class_name, req.student_id)

@app.post("/api/teacher/roster/set-enforce")
def set_roster_enforce_endpoint(req: SetRosterEnforceRequest):
    val = req.enforce if req.enforce is not None else (req.enforced if req.enforced is not None else True)
    return ExamEngine.set_roster_enforce(cohort=req.cohort or "", class_name=req.class_name or "", enforce=val)

@app.post("/api/teacher/roster/parse-text")
def parse_roster_text_endpoint(req: ParseRosterTextRequest):
    t = req.raw_text if req.raw_text is not None else (req.text or "")
    students = ExamEngine.parse_roster_text(t)
    return {"status": "success", "students": students, "count": len(students)}

@app.get("/api/exam/lookup-student")
def lookup_student_endpoint(
    cohort: str = Query(...),
    class_name: str = Query(...),
    student_id: str = Query(...)
):
    return ExamEngine.lookup_student_in_roster(cohort, class_name, student_id)

@app.post("/api/exam/start")
def start_exam(req: StartExamRequest):
    if not req.student_id or not req.student_name:
        raise HTTPException(status_code=400, detail="Vui lòng nhập Mã sinh viên và Họ tên")
    sbd_val = (req.sbd or "").strip() or req.student_id
    exam_data = ExamEngine.generate_exam_for_student(
        student_id=req.student_id,
        student_name=req.student_name,
        cohort=req.cohort,
        class_name=req.class_name,
        duration_minutes=req.duration_minutes,
        sbd=sbd_val,
        device_id=(req.device_id or "").strip(),
        device_info=(req.device_info or "").strip()
    )
    if "error" in exam_data:
        raise HTTPException(status_code=400, detail=exam_data["error"])
    return {"status": "success", "data": exam_data}

@app.get("/api/exam/download-template/{student_id}/{case_index}")
def download_student_template(student_id: str, case_index: int):
    docx_path = ExamEngine.create_official_docx_template(student_id, case_index)
    if os.path.exists(docx_path):
        return FileResponse(
            docx_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"Phoi_Thi_VB{case_index}_{student_id}.docx"
        )
    raise HTTPException(status_code=404, detail="Không tìm thấy phôi thi")

@app.post("/api/exam/upload-docx")
async def upload_docx(
    student_id: str = Form(...),
    case_index: int = Form(...),
    file: UploadFile = File(...)
):
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file định dạng Microsoft Word (.docx)")

    student_upload_dir = os.path.join(UPLOAD_DIR, student_id)
    os.makedirs(student_upload_dir, exist_ok=True)

    file_path = os.path.join(student_upload_dir, f"Case_{case_index}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    grade_res = ExamEngine.grade_practice_file(student_id, file_path, case_index)

    # Tự động đồng bộ lên Google Drive theo lớp (cttrung@ntt.edu.vn)
    session = ACTIVE_SESSIONS.get(student_id, {})
    s_name = session.get("student_name", "SinhVien")
    cohort = session.get("cohort", "Khóa 1")
    class_name = session.get("class_name", "Lớp 01")
    GDriveService.upload_file_async(
        student_id=student_id,
        student_name=s_name,
        cohort=cohort,
        class_name=class_name,
        case_index=case_index,
        docx_path=file_path,
        active_sessions_dict=ACTIVE_SESSIONS
    )

    return {
        "status": "success",
        "message": f"Nộp thành công bài thực hành {case_index}",
        "grade": grade_res
    }

@app.get("/api/exam/session/{student_id}")
def get_session(student_id: str, device_id: Optional[str] = Query(None)):
    session = ACTIVE_SESSIONS.get(student_id)
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên thi")
    import time
    remaining = max(0, int(session.get("end_time", time.time()) - time.time()))
    if remaining <= 0 and not session.get("is_submitted", False):
        session["is_submitted"] = True

    is_device_mismatch = False
    bound_dev = session.get("device_id")
    if bound_dev and device_id and bound_dev != device_id.strip():
        is_device_mismatch = True

    return {
        "student_id": session["student_id"],
        "student_name": session["student_name"],
        "sbd": session.get("sbd", session["student_id"]),
        "cohort": session.get("cohort", "Khóa 1"),
        "class_name": session.get("class_name", "Lớp 01"),
        "remaining_seconds": remaining,
        "is_submitted": session.get("is_submitted", False),
        "is_terminated": session.get("is_terminated", False),
        "termination_reason": session.get("termination_reason", ""),
        "is_device_mismatch": is_device_mismatch,
        "device_info": session.get("device_info", ""),
        "current_phase": session.get("current_phase", "QUIZ"),
        "extra_minutes_added": session.get("extra_minutes_added", 0),
        "duration_minutes": session.get("duration_minutes", 60),
        "quiz_score": session.get("quiz_score", 0.0),
        "word_scores": session.get("word_scores", {})
    }

@app.post("/api/exam/report-violation")
def report_violation(req: ReportViolationRequest):
    session = ACTIVE_SESSIONS.get(req.student_id)
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy sinh viên")
    
    violations = session.setdefault("anti_cheat_violations", [])
    violations.append({
        "time": time.strftime("%H:%M:%S"),
        "type": req.violation_type,
        "detail": req.detail
    })
    
    tab_violations = [v for v in violations if v.get("type") == "TAB_SWITCH"]
    if len(tab_violations) >= 3:
        session["anti_cheat_overall"] = "CHEATING"
        session["anti_cheat_summary"] = f"CẢNH BÁO: Rời màn hình {len(tab_violations)} lần khi làm trắc nghiệm!"
    elif len(tab_violations) >= 1:
        if session.get("anti_cheat_overall") != "CHEATING":
            session["anti_cheat_overall"] = "WARNING"
            session["anti_cheat_summary"] = f"Cảnh báo: Rời màn hình {len(tab_violations)} lần"
            
    return {"status": "success", "violations_count": len(violations)}

@app.post("/api/exam/set-phase")
def set_phase(req: PhaseTransitionRequest):
    session = ACTIVE_SESSIONS.get(req.student_id)
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy sinh viên")
    session["current_phase"] = req.phase
    if req.phase == "WORD":
        session["word_started_at"] = time.strftime("%H:%M:%S")
    return {"status": "success", "phase": req.phase}

@app.post("/api/exam/submit-quiz")
def submit_quiz(req: SubmitQuizRequest):
    res = ExamEngine.submit_quiz(req.student_id, req.answers)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return {"status": "success", "results": res}

@app.get("/api/exam/final-report/{student_id}")
def get_final_report(student_id: str):
    session = ACTIVE_SESSIONS.get(student_id)
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy sinh viên")
    session["is_submitted"] = True
    quiz = session.get("quiz_results", {})
    words = session.get("word_scores", {})
    quiz_pt = quiz.get("score", 0.0)
    w1_pt = words.get("case_1", {}).get("format_score", 0.0)
    w2_pt = words.get("case_2", {}).get("format_score", 0.0)
    sec_cfg = GradingService.get_sections()
    return {
        "student_id": session["student_id"],
        "student_name": session["student_name"],
        "sbd": session.get("sbd", session["student_id"]),
        "cohort": session.get("cohort", "Khóa 1"),
        "class_name": session.get("class_name", "Lớp 01"),
        "quiz_score": quiz_pt,
        "quiz_correct": f"{quiz.get('correct_count', 0)}/{quiz.get('total_questions', 0)}",
        "word_case_1_format_score": w1_pt,
        "word_case_2_format_score": w2_pt,
        "total_format_score": round(quiz_pt + w1_pt + w2_pt, 2),
        "sections_config": sec_cfg,
        "anti_cheat_overall": session.get("anti_cheat_overall", "SAFE"),
        "anti_cheat_violations": session.get("anti_cheat_violations", []),
        "anti_cheat_summary": session.get("anti_cheat_summary", "Hợp lệ"),
        "word_details": words
    }

# ----------------- TEACHER APIS -----------------
@app.get("/api/teacher/students")
def get_teacher_students(
    cohort: Optional[str] = Query(None),
    class_name: Optional[str] = Query(None)
):
    links_store = GDriveService.load_links()
    student_list = []
    for s_id, s_data in ACTIVE_SESSIONS.items():
        s_cohort = s_data.get("cohort", "Khóa 1")
        s_class = s_data.get("class_name", "Lớp 01")

        if cohort and cohort != "ALL" and s_cohort != cohort:
            continue
        if class_name and class_name != "ALL" and s_class != class_name:
            continue

        quiz = s_data.get("quiz_results", {})
        words = s_data.get("word_scores", {})
        quiz_score = quiz.get("score", 0.0)
        w1_format = words.get("case_1", {}).get("format_score", 0.0)
        w1_content = words.get("case_1", {}).get("content_score", 0.0)
        w2_format = words.get("case_2", {}).get("format_score", 0.0)
        w2_content = words.get("case_2", {}).get("content_score", 0.0)
        total_score = round(quiz_score + w1_format + w1_content + w2_format + w2_content, 2)
        is_graded = ("content_score" in words.get("case_1", {})) and ("content_score" in words.get("case_2", {}))
        rem_sec = max(0, int(s_data.get("end_time", time.time()) - time.time()))

        s_glinks = links_store.get(s_id, {})
        c1_drive = s_data.get("gdrive_links", {}).get("case_1", {}) or s_glinks.get("case_1", {})
        c2_drive = s_data.get("gdrive_links", {}).get("case_2", {}) or s_glinks.get("case_2", {})

        p_cases = s_data.get("practice_cases") or []
        c1_meta = p_cases[0] if len(p_cases) > 0 else {}
        c2_meta = p_cases[1] if len(p_cases) > 1 else {}

        student_list.append({
            "student_id": s_id,
            "student_name": s_data.get("student_name", ""),
            "sbd": s_data.get("sbd", s_id),
            "cohort": s_cohort,
            "class_name": s_class,
            "is_submitted": s_data.get("is_submitted", False),
            "is_terminated": s_data.get("is_terminated", False),
            "termination_reason": s_data.get("termination_reason", ""),
            "remaining_seconds": rem_sec,
            "extra_minutes_added": s_data.get("extra_minutes_added", 0),
            "duration_minutes": s_data.get("duration_minutes", 60),
            "quiz_score": quiz_score,
            "quiz_correct": f"{quiz.get('correct_count', 0)}/{quiz.get('total_questions', 0)}",
            "anti_cheat_overall": s_data.get("anti_cheat_overall", "SAFE"),
            "anti_cheat_violations": s_data.get("anti_cheat_violations", []),
            "anti_cheat_summary": s_data.get("anti_cheat_summary", "Hợp lệ"),
            "device_info": s_data.get("device_info", "Chưa xác định"),
            "device_first_login": s_data.get("device_first_login", ""),
            "current_phase": s_data.get("current_phase", "QUIZ"),
            "exam_token": s_data.get("exam_token", ""),
            "case_1": {
                "title": c1_meta.get("title", "Văn bản 1"),
                "doc_type": c1_meta.get("doc_type", ""),
                "format_score": w1_format,
                "content_score": w1_content,
                "details": words.get("case_1", {}).get("details", []),
                "anti_cheat": words.get("case_1", {}).get("anti_cheat", {}),
                "gdrive_url": c1_drive.get("file_url", ""),
                "gdrive_folder": c1_drive.get("folder_url", "")
            },
            "case_2": {
                "title": c2_meta.get("title", "Văn bản 2"),
                "doc_type": c2_meta.get("doc_type", ""),
                "format_score": w2_format,
                "content_score": w2_content,
                "details": words.get("case_2", {}).get("details", []),
                "anti_cheat": words.get("case_2", {}).get("anti_cheat", {}),
                "gdrive_url": c2_drive.get("file_url", ""),
                "gdrive_folder": c2_drive.get("folder_url", "")
            },
            "total_score": total_score,
            "teacher_comment": s_data.get("teacher_comment", ""),
            "is_graded": is_graded
        })
    return {
        "status": "success", 
        "students": student_list,
        "catalog": ExamEngine.get_classes_catalog(),
        "gdrive_config": GDriveService.load_config(),
        "grading_config": GradingService.load_config()
    }

@app.post("/api/teacher/extend-time")
def extend_time(req: ExtendTimeRequest):
    res = ExamEngine.extend_student_time(req.student_id, req.extra_minutes)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@app.post("/api/teacher/terminate-exam")
def terminate_exam(req: TerminateExamRequest):
    res = ExamEngine.terminate_student_exam(req.student_id, req.reason or "")
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@app.post("/api/teacher/retake-exam")
def retake_exam(req: RetakeExamRequest):
    res = ExamEngine.reopen_or_retake_exam(req.student_id, req.mode or "resume", req.extra_minutes or 15)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@app.post("/api/teacher/unlock-device")
def unlock_device(req: UnlockDeviceRequest):
    res = ExamEngine.unlock_student_device(req.student_id)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@app.post("/api/teacher/grade-content")
def grade_content(req: GradeContentRequest):
    session = ACTIVE_SESSIONS.get(req.student_id)
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy sinh viên")
    sec_cfg = GradingService.get_sections()
    c1_c_max = float(sec_cfg.get("case_1_content_max", 1.5))
    c2_c_max = float(sec_cfg.get("case_2_content_max", 1.5))
    c1_f_max = float(sec_cfg.get("case_1_format_max", 2.0))
    c2_f_max = float(sec_cfg.get("case_2_format_max", 2.0))

    words = session.setdefault("word_scores", {})
    words.setdefault("case_1", {})["content_score"] = min(c1_c_max, max(0.0, req.case_1_content_score))
    words.setdefault("case_2", {})["content_score"] = min(c2_c_max, max(0.0, req.case_2_content_score))

    if req.case_1_format_score is not None:
        words.setdefault("case_1", {})["format_score"] = min(c1_f_max, max(0.0, req.case_1_format_score))
    if req.case_2_format_score is not None:
        words.setdefault("case_2", {})["format_score"] = min(c2_f_max, max(0.0, req.case_2_format_score))

    session["teacher_comment"] = req.teacher_comment
    return {"status": "success", "message": "Đã lưu điểm và nhận xét thành công"}

@app.get("/api/grading-config")
@app.get("/api/teacher/grading-config")
def get_grading_config():
    return {"status": "success", "config": GradingService.load_config()}

@app.post("/api/teacher/grading-config")
def update_grading_config(req: GradingConfigRequest):
    if req.action == "reset":
        return GradingService.reset_to_default()
    cfg = req.config or {}
    return GradingService.save_config(cfg)

@app.get("/api/teacher/questions-bank")
def get_questions_bank():
    return {"status": "success", "data": ExamEngine.get_questions_bank()}

@app.post("/api/teacher/exam-config")
def update_exam_config(req: ExamConfigRequest):
    return ExamEngine.update_exam_config(mcq_count=req.mcq_count, duration_minutes=req.duration_minutes)

@app.post("/api/teacher/questions/add-mcq")
def add_mcq(req: AddMCQRequest):
    return ExamEngine.add_mcq(
        question=req.question,
        options=req.options,
        correct_index=req.correct_index,
        explanation=req.explanation or "",
        group=req.group or "Nghị định 30/2020/NĐ-CP"
    )

@app.post("/api/teacher/questions/delete-mcq")
def delete_mcq(req: DeleteMCQRequest):
    return ExamEngine.delete_mcq(req.question_id)

@app.get("/api/teacher/questions/sample-docx")
def get_sample_mcq_docx():
    sample_file = ExamEngine.get_sample_mcq_docx_path()
    if os.path.exists(sample_file):
        return FileResponse(
            sample_file,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename="Mau_De_Thi_Trac_Nghiem_Nghi_Dinh_30.docx"
        )
    raise HTTPException(status_code=404, detail="Không tìm thấy file mẫu")

@app.post("/api/teacher/questions/parse-docx")
async def parse_mcq_docx_file(file: UploadFile = File(...)):
    content = await file.read()
    return ExamEngine.parse_mcq_docx(content)

@app.post("/api/teacher/questions/parse-text")
def parse_mcq_text_route(req: ParseTextRequest):
    return ExamEngine.parse_mcq_text(req.text)

@app.post("/api/teacher/questions/import-batch")
def import_mcq_batch_route(req: ImportBatchMCQRequest):
    return ExamEngine.add_mcq_batch(req.questions)

@app.post("/api/teacher/questions/add-case")
def add_case(req: AddCaseRequest):
    return ExamEngine.add_practice_case(
        bucket=req.bucket,
        doc_type=req.doc_type,
        title=req.title,
        context=req.context,
        requirements=req.requirements or []
    )

@app.post("/api/teacher/questions/delete-case")
def delete_case(req: DeleteCaseRequest):
    return ExamEngine.delete_practice_case(req.bucket, req.case_id)

@app.post("/api/teacher/questions/clear-all")
def clear_all_questions_route(req: Optional[ClearQuestionsRequest] = None):
    target = req.target if req else "all"
    return ExamEngine.clear_questions_bank(target)

@app.post("/api/teacher/questions/restore-samples")
def restore_sample_questions_route():
    return ExamEngine.restore_sample_questions_bank()

@app.get("/api/teacher/download-file/{student_id}/{case_index}")
def download_student_file(student_id: str, case_index: int):
    student_dir = os.path.join(UPLOAD_DIR, student_id)
    if os.path.exists(student_dir):
        for fname in os.listdir(student_dir):
            if fname.startswith(f"Case_{case_index}_"):
                return FileResponse(
                    os.path.join(student_dir, fname),
                    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    filename=fname
                )
    raise HTTPException(status_code=404, detail="Không tìm thấy file bài làm")

@app.get("/api/teacher/gdrive-config")
def get_gdrive_config():
    return {
        "status": "success",
        "config": GDriveService.load_config(),
        "apps_script_code": GDriveService.get_apps_script_code()
    }

@app.post("/api/teacher/gdrive-config")
def update_gdrive_config(req: GDriveConfigRequest):
    cfg = GDriveService.load_config()
    if req.webhook_url is not None:
        cfg["webhook_url"] = req.webhook_url.strip()
    if req.auto_upload is not None:
        cfg["auto_upload"] = req.auto_upload
    GDriveService.save_config(cfg)
    return {"status": "success", "message": "Đã lưu cấu hình Google Drive thành công", "config": cfg}

@app.post("/api/teacher/gdrive-test")
def test_gdrive(req: GDriveTestRequest):
    return GDriveService.test_connection(req.webhook_url)

@app.post("/api/teacher/gdrive-sync-all")
def sync_all_gdrive():
    count = 0
    for s_id, s_data in ACTIVE_SESSIONS.items():
        s_dir = os.path.join(UPLOAD_DIR, s_id)
        if not os.path.exists(s_dir):
            continue
        s_name = s_data.get("student_name", "SinhVien")
        cohort = s_data.get("cohort", "Khóa 1")
        class_name = s_data.get("class_name", "Lớp 01")
        for c_idx in [1, 2]:
            f_name = f"Case_{c_idx}_submitted.docx"
            f_path = os.path.join(s_dir, f_name)
            if os.path.exists(f_path):
                GDriveService.upload_file_async(
                    student_id=s_id,
                    student_name=s_name,
                    cohort=cohort,
                    class_name=class_name,
                    case_index=c_idx,
                    docx_path=f_path,
                    active_sessions_dict=ACTIVE_SESSIONS
                )
                count += 1
    return {"status": "success", "message": f"Đã bắt đầu đồng bộ nền {count} bài thi lên Google Drive (cttrung@ntt.edu.vn)"}

@app.get("/api/teacher/export-excel")
def export_excel(
    cohort: Optional[str] = Query(None),
    class_name: Optional[str] = Query(None)
):
    links_store = GDriveService.load_links()
    sec_cfg = GradingService.get_sections()
    q_m = sec_cfg.get("quiz_max", 3.0)
    c1_f_m = sec_cfg.get("case_1_format_max", 2.0)
    c1_c_m = sec_cfg.get("case_1_content_max", 1.5)
    c2_f_m = sec_cfg.get("case_2_format_max", 2.0)
    c2_c_m = sec_cfg.get("case_2_content_max", 1.5)
    tot_m = round(q_m + c1_f_m + c1_c_m + c2_f_m + c2_c_m, 2)
    csv_lines = [
        f"STT,Khóa,Lớp,SBD,Mã sinh viên,Họ và tên,Điểm Trắc nghiệm ({q_m}đ),Thể thức VB1 - Công văn ({c1_f_m}đ),Nội dung VB1 ({c1_c_m}đ),Thể thức VB2 - Tờ trình/TB ({c2_f_m}đ),Nội dung VB2 ({c2_c_m}đ),Tổng điểm ({tot_m}đ),Chống Gian Lận,Link Drive VB1 (cttrung@ntt.edu.vn),Link Drive VB2 (cttrung@ntt.edu.vn),Trạng thái,Nhận xét giảng viên"
    ]
    stt = 1
    for s_id, s_data in ACTIVE_SESSIONS.items():
        s_cohort = s_data.get("cohort", "Khóa 1")
        s_class = s_data.get("class_name", "Lớp 01")

        if cohort and cohort != "ALL" and s_cohort != cohort:
            continue
        if class_name and class_name != "ALL" and s_class != class_name:
            continue

        quiz = s_data.get("quiz_results", {})
        words = s_data.get("word_scores", {})
        q_score = quiz.get("score", 0.0)
        w1_f = words.get("case_1", {}).get("format_score", 0.0)
        w1_c = words.get("case_1", {}).get("content_score", 0.0)
        w2_f = words.get("case_2", {}).get("format_score", 0.0)
        w2_c = words.get("case_2", {}).get("content_score", 0.0)
        total = round(q_score + w1_f + w1_c + w2_f + w2_c, 2)
        if s_data.get("is_terminated", False):
            status = f"ĐÌNH CHỈ THI ({s_data.get('termination_reason', 'Vi phạm')})"
        elif w1_c > 0 or w2_c > 0:
            status = "Đã chấm xong"
        elif not s_data.get("is_submitted", False) and (s_data.get("end_time", 0) > time.time()):
            rem_m = max(1, int((s_data.get("end_time", 0) - time.time()) / 60))
            status = f"Đang làm bài (còn {rem_m}p)"
        else:
            status = "Chờ GV chấm"
        comment = (s_data.get("teacher_comment", "") or "").replace('"', '""')
        name = s_data.get("student_name", "").replace('"', '""')
        cheat = s_data.get("anti_cheat_overall", "SAFE")
        cheat_summary = s_data.get("anti_cheat_summary", "")
        if cheat_summary and cheat_summary != "Hợp lệ":
            cheat_text = cheat_summary.replace('"', '""')
        else:
            cheat_text = "Hợp lệ" if cheat == "SAFE" else ("Cảnh báo" if cheat == "WARNING" else "NGHI VẤN GIAN LẬN")

        s_glinks = links_store.get(s_id, {})
        c1_link = s_data.get("gdrive_links", {}).get("case_1", {}).get("file_url") or s_glinks.get("case_1", {}).get("file_url", "")
        c2_link = s_data.get("gdrive_links", {}).get("case_2", {}).get("file_url") or s_glinks.get("case_2", {}).get("file_url", "")

        s_sbd = s_data.get("sbd", s_id)
        line = f'{stt},"{s_cohort}","{s_class}","{s_sbd}","{s_id}","{name}",{q_score},{w1_f},{w1_c},{w2_f},{w2_c},{total},"{cheat_text}","{c1_link}","{c2_link}","{status}","{comment}"'
        csv_lines.append(line)
        stt += 1

    csv_content = "\ufeff" + "\n".join(csv_lines)
    safe_c_name = "Tat_Ca_Cac_Lop"
    if class_name and class_name != "ALL":
        safe_c_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', class_name)
    elif cohort and cohort != "ALL":
        safe_c_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', cohort)

    return Response(
        content=csv_content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="Bang_Diem_{safe_c_name}.csv"'}
    )

@app.get("/api/exam/download-spec")
def download_spec():
    spec_path = os.path.join(PROJECT_ROOT, "SO_TAY_THE_THUC_NGHI_DINH_30_O_1_DEN_O_9.md")
    if os.path.exists(spec_path):
        return FileResponse(spec_path, media_type="text/markdown", filename="SO_TAY_THE_THUC_NGHI_DINH_30_O_1_DEN_O_9.md")
    raise HTTPException(status_code=404, detail="Không tìm thấy file quy chuẩn")

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/teacher")
def serve_teacher():
    return FileResponse(os.path.join(FRONTEND_DIR, "teacher.html"))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
