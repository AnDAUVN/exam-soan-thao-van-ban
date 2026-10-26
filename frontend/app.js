// Trạng thái ứng dụng client
let examData = null;
let userAnswers = {}; // {question_id: selected_text}
let timerInterval = null;
let syncInterval = null;
let remainingSeconds = 0;
let classesCatalog = {};

// 0. TẢI DANH MỤC KHÓA & LỚP KHI MỞ TRANG
async function loadClassesCatalog() {
    try {
        const response = await fetch('/api/classes');
        const res = await response.json();
        if (res.status === 'success') {
            classesCatalog = res.catalog;
            const cohortSelect = document.getElementById('input-cohort');
            cohortSelect.innerHTML = Object.keys(classesCatalog).map(c => `<option value="${c}">${c}</option>`).join('');
            onCohortChange();
        }
    } catch (e) {
        console.error('Lỗi tải danh mục lớp:', e);
    }
}

function onCohortChange() {
    const selectedCohort = document.getElementById('input-cohort').value;
    const classSelect = document.getElementById('input-class');
    const classes = classesCatalog[selectedCohort] || [];
    classSelect.innerHTML = classes.map(cls => `<option value="${cls}">${cls}</option>`).join('');
    onClassChange();
}

function onClassChange() {
    const sid = (document.getElementById('input-student-id')?.value || '').trim();
    if (sid) {
        lookupStudentRoster(false);
    }
}

let lookupDebounceTimer = null;
function onStudentIdInput() {
    if (lookupDebounceTimer) clearTimeout(lookupDebounceTimer);
    lookupDebounceTimer = setTimeout(() => {
        lookupStudentRoster(false);
    }, 350);
}

let lastLookupResult = null;

async function lookupStudentRoster(isBlur = false) {
    const cohort = document.getElementById('input-cohort')?.value;
    const className = document.getElementById('input-class')?.value;
    const studentIdInput = document.getElementById('input-student-id');
    const studentId = studentIdInput ? studentIdInput.value.trim() : '';
    const nameInput = document.getElementById('input-student-name');
    const sbdInput = document.getElementById('input-student-sbd');
    const badgeEl = document.getElementById('roster-status-badge');
    const spinnerEl = document.getElementById('roster-loading-spinner');
    const submitBtn = document.getElementById('btn-submit-start-exam');

    if (!cohort || !className || !studentId) {
        if (badgeEl) badgeEl.innerHTML = '';
        lastLookupResult = null;
        if (nameInput) {
            nameInput.readOnly = false;
            nameInput.classList.remove('bg-slate-100', 'cursor-not-allowed');
        }
        if (sbdInput) {
            sbdInput.readOnly = false;
            sbdInput.classList.remove('bg-slate-100', 'cursor-not-allowed');
        }
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        }
        return;
    }

    if (spinnerEl) spinnerEl.classList.remove('hidden');

    try {
        const response = await fetch(`/api/exam/lookup-student?cohort=${encodeURIComponent(cohort)}&class_name=${encodeURIComponent(className)}&student_id=${encodeURIComponent(studentId)}`);
        const data = await response.json();
        lastLookupResult = data;

        if (data.status === 'success') {
            if (data.found) {
                // Đã tìm thấy trong danh sách chính thức
                if (nameInput) {
                    nameInput.value = data.student_name;
                    nameInput.readOnly = true;
                    nameInput.classList.add('bg-slate-100', 'cursor-not-allowed');
                }
                if (sbdInput) {
                    sbdInput.value = data.sbd || data.student_id;
                    sbdInput.readOnly = true;
                    sbdInput.classList.add('bg-slate-100', 'cursor-not-allowed');
                }
                if (badgeEl) {
                    badgeEl.innerHTML = `<span class="inline-flex items-center gap-1.5 text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-md text-xs font-semibold animate-fadeIn"><i class="fa-solid fa-circle-check text-emerald-600"></i> Đã xác thực danh sách lớp: <b>${data.student_name}</b> (${data.sbd || ''})</span>`;
                }
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
                }
            } else {
                // Không có trong danh sách
                if (data.enforced) {
                    if (badgeEl) {
                        badgeEl.innerHTML = `<span class="inline-flex items-center gap-1.5 text-rose-700 bg-rose-50 border border-rose-200 px-2.5 py-1 rounded-md text-xs font-semibold"><i class="fa-solid fa-ban text-rose-600"></i> MSSV '<b>${studentId}</b>' KHÔNG CÓ TRONG DANH SÁCH lớp '${className}'. Bạn không có quyền truy cập phòng thi!</span>`;
                    }
                    if (nameInput) {
                        nameInput.readOnly = false;
                        nameInput.classList.remove('bg-slate-100', 'cursor-not-allowed');
                    }
                    if (sbdInput) {
                        sbdInput.readOnly = false;
                        sbdInput.classList.remove('bg-slate-100', 'cursor-not-allowed');
                    }
                    if (submitBtn) {
                        submitBtn.disabled = true;
                        submitBtn.classList.add('opacity-50', 'cursor-not-allowed');
                    }
                } else {
                    if (badgeEl) {
                        badgeEl.innerHTML = `<span class="inline-flex items-center gap-1.5 text-slate-600 bg-slate-50 border border-slate-200 px-2 py-0.5 rounded text-[11px]"><i class="fa-solid fa-circle-info text-blue-500"></i> Lớp chưa khóa danh sách (Tự do nhập SBD và Họ tên).</span>`;
                    }
                    if (nameInput) {
                        nameInput.readOnly = false;
                        nameInput.classList.remove('bg-slate-100', 'cursor-not-allowed');
                    }
                    if (sbdInput) {
                        sbdInput.readOnly = false;
                        sbdInput.classList.remove('bg-slate-100', 'cursor-not-allowed');
                    }
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
                    }
                }
            }
        }
    } catch (e) {
        console.error('Lỗi tra cứu danh sách thí sinh:', e);
    } finally {
        if (spinnerEl) spinnerEl.classList.add('hidden');
    }
}

// Gọi tải danh mục ngay khi khởi động
loadClassesCatalog();

// Quản lý định danh thiết bị độc nhất (Chống gian lận 1 thí sinh - 1 thiết bị duy nhất)
function getOrCreateDeviceId() {
    let devId = localStorage.getItem('exam_device_id');
    if (!devId) {
        devId = 'DEV_' + Math.random().toString(36).substring(2, 10) + '_' + Date.now().toString(36);
        localStorage.setItem('exam_device_id', devId);
    }
    return devId;
}

function getDeviceInfo() {
    const ua = navigator.userAgent;
    let os = "Thiết bị khác";
    if (ua.indexOf("Win") !== -1) os = "Windows PC";
    else if (ua.indexOf("Mac") !== -1) os = "MacBook / macOS";
    else if (ua.indexOf("Android") !== -1) os = "Điện thoại Android";
    else if (ua.indexOf("iPhone") !== -1) os = "iPhone (iOS)";
    else if (ua.indexOf("iPad") !== -1) os = "iPad (iOS)";
    else if (ua.indexOf("Linux") !== -1) os = "Linux PC";

    let browser = "Web Browser";
    if (ua.indexOf("Edg") !== -1) browser = "Edge";
    else if (ua.indexOf("Chrome") !== -1) browser = "Chrome";
    else if (ua.indexOf("Safari") !== -1 && ua.indexOf("Chrome") === -1) browser = "Safari";
    else if (ua.indexOf("Firefox") !== -1) browser = "Firefox";

    const screenRes = `${window.screen.width}x${window.screen.height}`;
    return `${os} - ${browser} (${screenRes})`;
}

// 1. BẮT ĐẦU THI
document.getElementById('start-exam-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const sbd = (document.getElementById('input-student-sbd')?.value || '').trim();
    const studentId = document.getElementById('input-student-id').value.trim();
    const studentName = document.getElementById('input-student-name').value.trim();
    const cohort = document.getElementById('input-cohort').value;
    const className = document.getElementById('input-class').value;
    const duration = 60; // Thời gian làm bài chính thức do Giảng viên quy định trên máy chủ

    // Chặn trước ở client nếu lớp bật bảo mật danh sách mà MSSV không hợp lệ
    if (lastLookupResult && lastLookupResult.enforced && !lastLookupResult.found) {
        alert(`⛔ TỪ CHỐI TRUY CẬP PHÒNG THI:\nMã sinh viên '${studentId}' KHÔNG CÓ TRONG DANH SÁCH chính thức của lớp ${cohort} - ${className}!\nChỉ sinh viên có tên trong danh sách được giảng viên phê duyệt mới được cấp đề thi.`);
        return;
    }

    const deviceId = getOrCreateDeviceId();
    const deviceInfo = getDeviceInfo();

    try {
        const response = await fetch('/api/exam/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sbd: sbd || studentId,
                student_id: studentId,
                student_name: studentName,
                cohort: cohort,
                class_name: className,
                duration_minutes: duration,
                device_id: deviceId,
                device_info: deviceInfo
            })
        });

        const res = await response.json();
        if (res.status === 'success') {
            examData = res.data;
            if (examData.exam_token) {
                sessionStorage.setItem('exam_token', examData.exam_token);
            }
            if (examData.is_resumed) {
                alert(`📋 KHÔI PHỤC BÀI THI THÀNH CÔNG:\nChào ${examData.student_name}, bài thi đang làm dở của bạn đã được khôi phục trên thiết bị này!\nThời gian còn lại: ~${Math.ceil(examData.remaining_seconds / 60)} phút.`);
            }
            initExamRoom();
        } else {
            alert(res.detail || res.error || 'Không thể tạo phiên thi');
        }
    } catch (err) {
        alert('Lỗi kết nối máy chủ thi: ' + err.message);
    }
});

// 2. KHỞI TẠO PHÒNG THI
function initExamRoom() {
    document.getElementById('login-screen').classList.add('hidden');
    document.getElementById('exam-screen').classList.remove('hidden');

    document.getElementById('header-student-name').innerText = examData.student_name;
    document.getElementById('header-student-id').innerText = examData.student_id;
    const headerSbd = document.getElementById('header-student-sbd');
    if (headerSbd) {
        headerSbd.innerText = examData.sbd || examData.student_id;
    }
    const cohortClassEl = document.getElementById('header-cohort-class');
    if (cohortClassEl) {
        cohortClassEl.innerText = `${examData.cohort} - ${examData.class_name}`;
    }

    remainingSeconds = examData.remaining_seconds;
    startTimer();
    startSessionSync();

    // Thiết lập đường dẫn tải phôi Word bảo mật cá nhân (nhúng token)
    const tok = examData.exam_token || sessionStorage.getItem('exam_token') || '';
    const tokQuery = tok ? `?token=${encodeURIComponent(tok)}` : '';
    const btnTemplate1 = document.getElementById('btn-download-template-1');
    if (btnTemplate1) btnTemplate1.href = `/api/exam/download-template/${examData.student_id}/1${tokQuery}`;
    const btnTemplate2 = document.getElementById('btn-download-template-2');
    if (btnTemplate2) btnTemplate2.href = `/api/exam/download-template/${examData.student_id}/2${tokQuery}`;

    renderQuizQuestions(examData.quiz_questions);
    renderPracticeCases(examData.practice_cases);
}

// 3. ĐỒNG HỒ ĐẾM NGƯỢC
function startTimer() {
    updateTimerDisplay();
    timerInterval = setInterval(() => {
        remainingSeconds--;
        if (remainingSeconds <= 0) {
            clearInterval(timerInterval);
            alert('Đã hết thời gian làm bài! Hệ thống đang tự động thu bài.');
            finishExam();
        }
        updateTimerDisplay();
    }, 1000);
}

function updateTimerDisplay() {
    const hours = Math.floor(remainingSeconds / 3600);
    const minutes = Math.floor((remainingSeconds % 3600) / 60);
    const seconds = remainingSeconds % 60;
    const formatted = [
        hours.toString().padStart(2, '0'),
        minutes.toString().padStart(2, '0'),
        seconds.toString().padStart(2, '0')
    ].join(':');

    const timerEl = document.getElementById('exam-timer');
    timerEl.innerText = formatted;

    if (remainingSeconds < 300) {
        timerEl.classList.remove('text-amber-400');
        timerEl.classList.add('text-rose-500', 'animate-pulse');
    } else {
        timerEl.classList.remove('text-rose-500', 'animate-pulse');
        timerEl.classList.add('text-amber-400');
    }
}

// 3b. ĐỒNG BỘ THỜI GIAN VÀ TRẠNG THÁI TỪ MÁY CHỦ (GIA HẠN / ĐÌNH CHỈ / CHỐNG ĐĂNG NHẬP THIẾT BỊ 2)
function startSessionSync() {
    if (!examData || !examData.student_id) return;
    if (syncInterval) clearInterval(syncInterval);
    syncInterval = setInterval(async () => {
        try {
            const devId = getOrCreateDeviceId();
            const response = await fetch(`/api/exam/session/${encodeURIComponent(examData.student_id)}?device_id=${encodeURIComponent(devId)}`);
            if (response.ok) {
                const session = await response.json();
                
                // 0. Kiểm tra cảnh báo nếu có thiết bị khác cố tình đăng nhập trái phép
                if (session.is_device_mismatch) {
                    clearInterval(timerInterval);
                    clearInterval(syncInterval);
                    alert(`⛔ CẢNH BÁO VI PHẠM QUY CHẾ THI:\n\nThiết bị này không khớp với thiết bị ban đầu được đăng ký cho bài thi của bạn!\nMỗi thí sinh CHỈ ĐƯỢC PHÉP LÀM BÀI TRÊN 01 THIẾT BỊ DUY NHẤT.\nVui lòng dừng làm bài và báo ngay cho Giám thị.`);
                    location.reload();
                    return;
                }

                // 1. Kiểm tra nếu giảng viên đình chỉ thi
                if (session.is_terminated) {
                    clearInterval(timerInterval);
                    clearInterval(syncInterval);
                    const reason = session.termination_reason || "Giáo viên đã đình chỉ / thu bài bắt buộc!";
                    alert(`⛔ THÔNG BÁO TỪ GIÁNG VIÊN:\n${reason}`);
                    finishExam();
                    return;
                }

                // 2. Kiểm tra nếu giảng viên gia hạn thêm thời gian
                const serverRemaining = session.remaining_seconds;
                if (serverRemaining > remainingSeconds + 20) {
                    const extraAdded = Math.round((serverRemaining - remainingSeconds) / 60);
                    remainingSeconds = serverRemaining;
                    updateTimerDisplay();
                    showTimeExtensionToast(`Giáo viên vừa gia hạn thêm +${extraAdded} phút làm bài cho bạn!`);
                } else if (Math.abs(serverRemaining - remainingSeconds) > 10 && remainingSeconds > 5) {
                    remainingSeconds = serverRemaining;
                    updateTimerDisplay();
                }
            }
        } catch (e) {
            // Bỏ qua lỗi gián đoạn mạng tạm thời
        }
    }, 4000);
}

function showTimeExtensionToast(msg) {
    let toast = document.getElementById('toast-time-extension');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast-time-extension';
        toast.className = 'fixed top-20 right-6 z-50 bg-emerald-600 text-white px-5 py-3 rounded-2xl shadow-2xl font-bold text-xs flex items-center gap-2 border border-emerald-400 transition transform duration-300';
        document.body.appendChild(toast);
    }
    toast.innerHTML = `<i class="fa-solid fa-clock-rotate-left text-base text-emerald-200"></i> ${msg}`;
    toast.classList.remove('hidden');
    setTimeout(() => {
        if (toast) toast.classList.add('hidden');
    }, 6000);
}

// 4. HIỂN THỊ CÂU HỎI TRẮC NGHIỆM
function renderQuizQuestions(questions) {
    const listEl = document.getElementById('quiz-questions-list');
    const navGridEl = document.getElementById('quiz-nav-grid');
    listEl.innerHTML = '';
    navGridEl.innerHTML = '';

    const totalQ = (questions || []).length;
    const navQuizTitle = document.getElementById('nav-quiz-title');
    if (navQuizTitle) {
        navQuizTitle.innerText = `1. Trắc nghiệm (${totalQ} câu)`;
    }
    const badge = document.getElementById('quiz-badge');
    if (badge) {
        badge.innerText = `0/${totalQ}`;
    }

    questions.forEach((q, idx) => {
        const card = document.createElement('div');
        card.id = `q-card-${idx + 1}`;
        card.className = 'bg-white rounded-xl p-5 border border-slate-200 shadow-sm space-y-3';
        card.innerHTML = `
            <div class="flex items-start gap-3">
                <span class="px-2.5 py-1 bg-blue-100 text-blue-700 font-bold text-xs rounded-md">Câu ${idx + 1}</span>
                <p class="text-sm font-semibold text-slate-800 leading-snug">${q.question}</p>
            </div>
            <div class="space-y-2 pt-1">
                ${q.options.map((opt, optIdx) => `
                    <label class="flex items-center gap-3 p-3 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer text-sm transition text-slate-700">
                        <input type="radio" name="question_${q.question_id}" value="${opt}" 
                               onchange="selectAnswer(${q.question_id}, '${opt.replace(/'/g, "\\'")}', ${idx + 1})"
                                class="w-4 h-4 text-blue-600 focus:ring-blue-500">
                        <span><b>${String.fromCharCode(65 + optIdx)}.</b> ${opt}</span>
                    </label>
                `).join('')}
            </div>
        `;
        listEl.appendChild(card);

        const navBtn = document.createElement('button');
        navBtn.id = `nav-q-${idx + 1}`;
        navBtn.className = 'h-9 text-xs font-semibold rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 transition';
        navBtn.innerText = idx + 1;
        navBtn.onclick = () => {
            switchTab('quiz');
            card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        };
        navGridEl.appendChild(navBtn);
    });
}

function selectAnswer(questionId, selectedOption, index) {
    userAnswers[questionId] = selectedOption;

    const navBtn = document.getElementById(`nav-q-${index}`);
    if (navBtn) {
        navBtn.classList.remove('border-slate-200', 'text-slate-600');
        navBtn.classList.add('bg-blue-600', 'text-white', 'border-blue-600');
    }

    const answeredCount = Object.keys(userAnswers).length;
    const totalQ = (examData && examData.quiz_questions) ? examData.quiz_questions.length : 10;
    const badge = document.getElementById('quiz-badge');
    if (badge) {
        badge.innerText = `${answeredCount}/${totalQ}`;
    }
}

// 5. HIỂN THỊ ĐỀ THI TÌNH HUỐNG WORD
function renderPracticeCases(cases) {
    if (!cases || cases.length === 0) return;

    // Tình huống 1: Văn bản thực hành 1 (4 điểm)
    const c1 = cases[0];
    if (c1) {
        const b1 = document.getElementById('case1-badge');
        if (b1) b1.innerText = 'Văn bản thực hành 1 (4.0 điểm)';
        const t1 = document.getElementById('case1-title');
        if (t1) t1.innerText = 'Tình huống thực hành 1';
        const ctx1 = document.getElementById('case1-context');
        if (ctx1) ctx1.innerText = c1.context || '';
        const req1 = document.getElementById('case1-requirements');
        if (req1) req1.innerHTML = (c1.requirements || []).map(r => `<li>${r}</li>`).join('');
    }

    // Tình huống 2: Văn bản thực hành 2 (4 điểm)
    if (cases.length > 1) {
        const c2 = cases[1];
        const b2 = document.getElementById('case2-badge');
        if (b2) b2.innerText = 'Văn bản thực hành 2 (4.0 điểm)';
        const t2 = document.getElementById('case2-title');
        if (t2) t2.innerText = 'Tình huống thực hành 2';
        const ctx2 = document.getElementById('case2-context');
        if (ctx2) ctx2.innerText = c2.context || '';
        const req2 = document.getElementById('case2-requirements');
        if (req2) req2.innerHTML = (c2.requirements || []).map(r => `<li>${r}</li>`).join('');
    }
}

// ================= CHỐNG GIAN LẬN: 2 GIAI ĐOẠN THI (GIẢI PHÁP 1) =================
let currentExamPhase = "QUIZ"; // "QUIZ" (Đang làm trắc nghiệm) hoặc "WORD" (Đang thực hành Word)
let tabSwitchCount = 0;
let lastBlurTime = 0;

function updatePhaseUI() {
    const banner = document.getElementById('phase-status-banner');
    const icon = document.getElementById('phase-status-icon');
    const badge = document.getElementById('phase-status-badge');
    const title = document.getElementById('phase-status-title');
    const desc = document.getElementById('phase-status-desc');
    const action = document.getElementById('phase-status-action');

    if (!banner) return;

    if (currentExamPhase === "QUIZ") {
        banner.className = "bg-amber-50 border border-amber-300 rounded-xl p-3.5 mb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs font-medium transition-all shadow-xs";
        if (icon) {
            icon.className = "w-8 h-8 rounded-full bg-amber-200 text-amber-900 flex items-center justify-center font-bold text-sm shrink-0";
            icon.innerHTML = '<i class="fa-solid fa-shield-halved"></i>';
        }
        if (badge) {
            badge.className = "px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-amber-200 text-amber-950 border border-amber-300";
            badge.innerText = "Giai đoạn 1";
        }
        if (title) title.innerText = "Đang làm bài Trắc nghiệm (Giám sát màn hình BẬT)";
        if (desc) desc.innerHTML = `⚠️ Vui lòng <b>không chuyển tab</b> hoặc mở ứng dụng khác khi đang làm trắc nghiệm. (${tabSwitchCount > 0 ? `Đã cảnh báo: ${tabSwitchCount}/3 lần` : 'Chưa có vi phạm'})`;
        if (action) {
            action.innerHTML = `
                <button type="button" onclick="transitionToWordPhase()" class="px-3.5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold text-xs shadow-sm transition flex items-center gap-1.5 shrink-0">
                    <i class="fa-solid fa-file-word"></i> Sang Thực hành Word <i class="fa-solid fa-arrow-right text-[10px]"></i>
                </button>
            `;
        }
    } else {
        banner.className = "bg-emerald-50 border border-emerald-300 rounded-xl p-3.5 mb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs font-medium transition-all shadow-xs";
        if (icon) {
            icon.className = "w-8 h-8 rounded-full bg-emerald-200 text-emerald-900 flex items-center justify-center font-bold text-sm shrink-0";
            icon.innerHTML = '<i class="fa-solid fa-check-circle"></i>';
        }
        if (badge) {
            badge.className = "px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-200 text-emerald-950 border border-emerald-300";
            badge.innerText = "Giai đoạn 2";
        }
        if (title) title.innerText = "Đang làm Thực hành Soạn thảo Word";
        if (desc) desc.innerHTML = '✅ <b>Đã tạm ngưng cảnh báo chuyển tab</b>. Bạn có thể mở Microsoft Word trên máy tính để làm bài theo Nghị định 30.';
        if (action) {
            action.innerHTML = `
                <button type="button" onclick="transitionToQuizPhase()" class="px-3 py-1.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-lg font-semibold text-xs transition flex items-center gap-1.5 shrink-0">
                    <i class="fa-solid fa-list-check text-blue-600"></i> Xem lại Trắc nghiệm
                </button>
            `;
        }
    }
}

async function transitionToWordPhase(notify = true) {
    if (currentExamPhase === "WORD") return;
    currentExamPhase = "WORD";
    updatePhaseUI();
    if (notify) {
        alert("✅ BẠN ĐÃ CHUYỂN SANG PHẦN THỰC HÀNH SOẠN THẢO WORD:\n\nChế độ giám sát chuyển tab đã được TẠM NGƯNG để bạn có thể mở Microsoft Word trên máy tính soạn thảo theo Nghị định 30.\n\nLưu ý: Hệ thống sẽ tự động giám định tính toàn vẹn (thời gian soạn thảo, mã phôi ẩn, số lần lưu) khi bạn nộp file Word.");
    }
    if (examData && examData.student_id) {
        try {
            const tok = examData.exam_token || sessionStorage.getItem('exam_token') || '';
            await fetch('/api/exam/set-phase', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-Exam-Token': tok
                },
                body: JSON.stringify({ 
                    student_id: examData.student_id, 
                    phase: 'WORD',
                    token: tok 
                })
            });
        } catch (e) {}
    }
}

async function transitionToQuizPhase() {
    currentExamPhase = "QUIZ";
    updatePhaseUI();
    switchTab('quiz');
}

// Bắt sự kiện chuyển tab / thu nhỏ trình duyệt khi đang ở GIAI ĐOẠN TRẮC NGHIỆM
window.addEventListener('blur', () => {
    if (!examData || examData.is_submitted) return;
    if (currentExamPhase === "QUIZ") {
        lastBlurTime = Date.now();
    }
});

document.addEventListener('visibilitychange', () => {
    if (!examData || examData.is_submitted) return;
    if (document.hidden) {
        if (currentExamPhase === "QUIZ") {
            lastBlurTime = Date.now();
        }
    } else {
        if (currentExamPhase === "QUIZ" && lastBlurTime > 0) {
            const awaySeconds = Math.round((Date.now() - lastBlurTime) / 1000);
            lastBlurTime = 0;
            if (awaySeconds >= 1) {
                tabSwitchCount++;
                updatePhaseUI();
                reportTabViolation(tabSwitchCount, awaySeconds);
            }
        }
    }
});

async function reportTabViolation(count, awaySeconds) {
    if (count === 1) {
        alert(`⚠️ CẢNH BÁO RỜI MÀN HÌNH THI (Lần 1/3):\n\nBạn vừa chuyển tab hoặc rời màn hình thi (${awaySeconds} giây) khi đang làm Trắc nghiệm!\nHành vi này đã được gửi về Giám thị phòng thi.\n\nVui lòng tập trung làm bài, rời quá 3 lần sẽ bị đánh dấu gian lận!`);
    } else if (count === 2) {
        alert(`⚠️ CẢNH BÁO RỜI MÀN HÌNH THI (Lần 2/3):\n\nBạn tiếp tục rời màn hình thi (${awaySeconds} giây).\nNếu rời thêm 1 lần nữa, bài thi của bạn sẽ bị bật cờ đỏ GIAN LẬN!`);
    } else {
        alert(`⛔ CẢNH BÁO VI PHẠM QUY CHẾ THI (Lần ${count}):\n\nBạn đã rời màn hình quá 3 lần khi đang làm Trắc nghiệm!\nHệ thống đã BẬT CỜ ĐỎ GIAN LẬN trên máy Giám thị và ghi vào biên bản thi.`);
    }

    if (examData && examData.student_id) {
        try {
            const tok = examData.exam_token || sessionStorage.getItem('exam_token') || '';
            await fetch('/api/exam/report-violation', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-Exam-Token': tok
                },
                body: JSON.stringify({
                    student_id: examData.student_id,
                    violation_type: 'TAB_SWITCH',
                    detail: `Rời màn hình khi làm trắc nghiệm (Lần ${count}, vắng ${awaySeconds}s)`,
                    token: tok
                })
            });
        } catch (e) {}
    }
}

// 6. CHUYỂN TAB LÀM BÀI
function switchTab(tab) {
    const tabs = ['quiz', 'case1', 'case2'];
    tabs.forEach(t => {
        document.getElementById(`content-${t}`).classList.add('hidden');
        const navBtn = document.getElementById(`nav-tab-${t}`);
        navBtn.classList.remove('bg-blue-50', 'text-blue-700', 'font-semibold', 'border-l-4', 'border-blue-600');
        navBtn.classList.add('text-slate-600');
    });

    document.getElementById(`content-${tab}`).classList.remove('hidden');
    const activeBtn = document.getElementById(`nav-tab-${tab}`);
    activeBtn.classList.add('bg-blue-50', 'text-blue-700', 'font-semibold', 'border-l-4', 'border-blue-600');
    activeBtn.classList.remove('text-slate-600');

    // Tự động chuyển sang giai đoạn Word nếu sinh viên chủ động bấm vào tab thực hành văn bản
    if ((tab === 'case1' || tab === 'case2') && currentExamPhase === 'QUIZ') {
        transitionToWordPhase(false);
    }
}

// 7. NỘP TRẮC NGHIỆM ĐỘC LẬP
async function submitQuizAnswers() {
    if (!examData) return;
    try {
        const tok = examData.exam_token || sessionStorage.getItem('exam_token') || '';
        const response = await fetch('/api/exam/submit-quiz', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-Exam-Token': tok
            },
            body: JSON.stringify({
                student_id: examData.student_id,
                answers: userAnswers,
                token: tok
            })
        });
        const res = await response.json();
        if (res.status === 'success') {
            alert(`Đã lưu kết quả trắc nghiệm!\nĐúng: ${res.results.correct_count}/${res.results.total_questions} câu\nĐiểm: ${res.results.score} điểm.`);
            // Sau khi nộp trắc nghiệm, tự động kích hoạt giai đoạn làm Word
            transitionToWordPhase(true);
            switchTab('case1');
        }
    } catch (err) {
        alert('Lỗi lưu trắc nghiệm: ' + err.message);
    }
}

// 8. TẢI LÊN FILE WORD & ĐỐI CHIẾU THỂ THỨC Ô 1 - Ô 9
async function handleFileUpload(caseIndex) {
    const fileInput = document.getElementById(`file-upload-case${caseIndex}`);
    if (!fileInput.files || fileInput.files.length === 0) return;

    const file = fileInput.files[0];
    const tok = examData.exam_token || sessionStorage.getItem('exam_token') || '';
    const formData = new FormData();
    formData.append('student_id', examData.student_id);
    formData.append('case_index', caseIndex);
    formData.append('file', file);
    formData.append('token', tok);

    const resultBox = document.getElementById(`case${caseIndex}-grade-result`);
    resultBox.classList.remove('hidden');
    resultBox.innerHTML = '<p class="text-xs text-blue-600"><i class="fa-solid fa-spinner fa-spin"></i> Đang tải lên và đối chiếu quy chuẩn Ô 1 - Ô 9 theo Nghị định 30...</p>';

    try {
        const response = await fetch('/api/exam/upload-docx', {
            method: 'POST',
            headers: {
                'X-Exam-Token': tok
            },
            body: formData
        });
        const res = await response.json();
        if (res.status === 'success') {
            const grade = res.grade;
            document.getElementById(`case${caseIndex}-status`).innerHTML = '<i class="fa-solid fa-circle-check text-emerald-500"></i>';

            const ac = grade.anti_cheat || {};
            let acBadge = '';
            if (ac.violations && ac.violations.length > 0) {
                acBadge = `<span class="px-2 py-0.5 bg-rose-100 text-rose-800 text-[10px] font-bold rounded flex items-center gap-1 border border-rose-300"><i class="fa-solid fa-triangle-exclamation text-rose-600"></i> ${ac.violations.join(', ')}</span>`;
            } else if (ac.status === 'SAFE') {
                acBadge = `<span class="px-2 py-0.5 bg-emerald-100 text-emerald-800 text-[10px] font-bold rounded flex items-center gap-1"><i class="fa-solid fa-shield-check"></i> Phôi thi hợp lệ</span>`;
            } else if (ac.status === 'WARNING') {
                acBadge = `<span class="px-2 py-0.5 bg-amber-100 text-amber-800 text-[10px] font-bold rounded flex items-center gap-1"><i class="fa-solid fa-triangle-exclamation"></i> Cảnh báo thời gian</span>`;
            } else {
                acBadge = `<span class="px-2 py-0.5 bg-rose-100 text-rose-800 text-[10px] font-bold rounded flex items-center gap-1"><i class="fa-solid fa-triangle-exclamation"></i> Nghi vấn gian lận</span>`;
            }

            resultBox.innerHTML = `
                <div class="flex items-center justify-between mb-2 border-b border-emerald-200 pb-2">
                    <div class="flex items-center gap-2">
                        <span class="font-bold text-sm text-emerald-900 flex items-center gap-1.5">
                            <i class="fa-solid fa-circle-check text-emerald-600"></i> Đối chiếu Thể thức NĐ 30:
                        </span>
                        ${acBadge}
                    </div>
                    <span class="font-bold text-base text-emerald-700 bg-emerald-100 px-3 py-0.5 rounded-full">
                        ${grade.format_score}/${grade.format_max} điểm
                    </span>
                </div>
                <div class="text-xs text-slate-700 space-y-1.5">
                    ${grade.details.map(d => `
                        <div class="flex items-start justify-between py-1 border-b border-emerald-100/60">
                            <div>
                                <span class="font-bold text-slate-800 bg-slate-200 px-1.5 py-0.5 rounded text-[10px] mr-1">${d.cell || 'Quy cách'}</span>
                                <span class="font-medium text-slate-800">${d.item}</span>
                                <div class="text-[11px] text-slate-500 italic mt-0.5">${d.comment}</div>
                            </div>
                            <span class="font-bold ${d.score > 0 ? 'text-emerald-700' : 'text-rose-600'} shrink-0 ml-2">
                                ${d.score}/${d.max}đ
                            </span>
                        </div>
                    `).join('')}
                </div>
                ${(ac.flags && ac.flags.length > 0) ? `
                    <div class="mt-2 pt-2 border-t border-emerald-200 text-[11px] text-slate-600">
                        <span class="font-bold">Kiểm tra bảo mật file:</span>
                        <ul class="list-disc pl-4 space-y-0.5 mt-0.5 text-slate-500">
                            ${ac.flags.map(f => `<li>${f}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
            `;
        } else {
            resultBox.innerHTML = `<p class="text-xs text-rose-600">Lỗi: ${res.detail}</p>`;
        }
    } catch (err) {
        resultBox.innerHTML = `<p class="text-xs text-rose-600">Lỗi kết nối: ${err.message}</p>`;
    }
}

// 9. NỘP TOÀN BỘ BÀI THI & XEM BÁO CÁO
document.getElementById('btn-finish-exam').addEventListener('click', () => {
    if (confirm('Bạn có chắc chắn muốn nộp bài thi kết thúc phiên làm bài không?')) {
        finishExam();
    }
});

async function finishExam() {
    clearInterval(timerInterval);
    if (syncInterval) clearInterval(syncInterval);
    await submitQuizAnswers();

    try {
        const tok = examData.exam_token || sessionStorage.getItem('exam_token') || '';
        const tokQuery = tok ? `?token=${encodeURIComponent(tok)}` : '';
        const response = await fetch(`/api/exam/final-report/${encodeURIComponent(examData.student_id)}${tokQuery}`, {
            headers: {
                'X-Exam-Token': tok
            }
        });
        const res = await response.json();

        document.getElementById('result-name').innerText = res.student_name;
        const resSbdEl = document.getElementById('result-sbd');
        if (resSbdEl) resSbdEl.innerText = res.sbd || (examData && examData.sbd) || res.student_id;
        document.getElementById('result-id').innerText = res.student_id;
        const cfg = res.sections_config || {
            quiz_max: 2.0,
            case_1_format_max: 2.0,
            case_1_content_max: 2.0,
            case_2_format_max: 2.0,
            case_2_content_max: 2.0
        };
        const autoMax = Number(((cfg.quiz_max || 2.0) + (cfg.case_1_format_max || 2.0) + (cfg.case_2_format_max || 2.0)).toFixed(2));
        const contentMax = Number(((cfg.case_1_content_max || 2.0) + (cfg.case_2_content_max || 2.0)).toFixed(2));

        document.getElementById('result-quiz-score').innerText = `${res.quiz_score}/${cfg.quiz_max} điểm (${res.quiz_correct} câu)`;
        document.getElementById('result-w1-score').innerText = `${res.word_case_1_format_score}/${cfg.case_1_format_max} điểm`;
        document.getElementById('result-w2-score').innerText = `${res.word_case_2_format_score}/${cfg.case_2_format_max} điểm`;
        document.getElementById('result-total-auto').innerText = `${res.total_format_score}/${autoMax} điểm`;
        
        const acEl = document.getElementById('result-anti-cheat');
        if (acEl) {
            if (res.anti_cheat_violations && res.anti_cheat_violations.length > 0) {
                acEl.className = 'font-bold text-xs text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200';
                acEl.innerHTML = `<i class="fa-solid fa-triangle-exclamation mr-1"></i>${res.anti_cheat_violations.join(', ')}`;
            } else if (res.anti_cheat_overall === 'SAFE') {
                acEl.className = 'font-bold text-xs text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200';
                acEl.innerHTML = `<i class="fa-solid fa-shield-check mr-1"></i>Hợp lệ`;
            } else {
                acEl.className = 'font-bold text-xs text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200';
                acEl.innerHTML = `<i class="fa-solid fa-triangle-exclamation mr-1"></i>Cảnh báo`;
            }
        }

        const noteEl = document.getElementById('result-content-note');
        if (noteEl) {
            noteEl.innerText = `* ${contentMax} điểm nội dung còn lại sẽ do Giảng viên chấm trực tiếp theo rubric.`;
        }

        const modal = document.getElementById('modal-result');
        modal.classList.remove('hidden');
        modal.classList.add('flex');

        // Bắt đầu lắng nghe tự động nếu Giảng viên mở lại bài thi
        startReopenSync();
    } catch (err) {
        alert('Lỗi lấy bảng điểm tổng hợp: ' + err.message);
    }
}

// 9b. TỰ ĐỘNG LẮNG NGHE & KHÔI PHỤC KHI GIẢNG VIÊN MỞ LẠI BÀI THI (DO LỠ NỘP NHẦM)
let reopenSyncInterval = null;

function startReopenSync() {
    if (reopenSyncInterval) clearInterval(reopenSyncInterval);
    reopenSyncInterval = setInterval(async () => {
        if (!examData || !examData.student_id) return;
        try {
            const response = await fetch(`/api/exam/session/${examData.student_id}`);
            if (response.ok) {
                const session = await response.json();
                if (!session.is_submitted && session.remaining_seconds > 0) {
                    clearInterval(reopenSyncInterval);
                    reopenSyncInterval = null;
                    resumeExamUI(session);
                }
            }
        } catch (e) {
            // bỏ qua lỗi mạng tạm thời
        }
    }, 3000);
}

function resumeExamUI(session) {
    const modal = document.getElementById('modal-result');
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }

    remainingSeconds = session.remaining_seconds;
    startTimer();
    startSessionSync();

    alert(`🎉 THÔNG BÁO TỪ GIẢNG VIÊN:\nGiảng viên đã mở lại bài thi cho bạn!\nThời gian còn lại: ~${Math.ceil(remainingSeconds / 60)} phút.\nBạn có thể tiếp tục hoàn thiện bài làm và nộp lại.`);
}

async function checkResumeFromModal() {
    if (!examData || !examData.student_id) {
        alert('Chưa có thông tin phiên thi.');
        return;
    }
    const btn = document.getElementById('btn-resume-exam');
    const origHtml = btn ? btn.innerHTML : '';
    if (btn) {
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i> Đang kiểm tra...';
        btn.disabled = true;
    }

    try {
        const response = await fetch(`/api/exam/session/${examData.student_id}`);
        if (response.ok) {
            const session = await response.json();
            if (!session.is_submitted && session.remaining_seconds > 0) {
                if (reopenSyncInterval) clearInterval(reopenSyncInterval);
                resumeExamUI(session);
            } else {
                alert('⚠️ Giảng viên chưa bấm duyệt mở lại bài thi cho bạn.\n\nBạn vui lòng báo Giảng viên bấm nút "Cho làm lại" trên bảng điểm quản lý ca thi, sau đó thử bấm lại nút này nhé!');
            }
        } else {
            alert('Không thể kết nối máy chủ thi.');
        }
    } catch (err) {
        alert('Lỗi kết nối: ' + err.message);
    } finally {
        if (btn) {
            btn.innerHTML = origHtml;
            btn.disabled = false;
        }
    }
}

// 10. MODAL TRA CỨU ĐỐI CHIẾU Ô 1 - Ô 9
function openSpecModal() {
    const modal = document.getElementById('modal-spec');
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

function closeSpecModal() {
    const modal = document.getElementById('modal-spec');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
}

// 11. TOÀN MÀN HÌNH (FULLSCREEN ANTI-CHEAT)
document.getElementById('btn-fullscreen').addEventListener('click', () => {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(err => {
            alert(`Lỗi kích hoạt toàn màn hình: ${err.message}`);
        });
    } else {
        document.exitFullscreen();
    }
});
