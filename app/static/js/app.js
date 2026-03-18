/**
 * BlogPilot 공통 JavaScript 유틸리티
 * 모든 페이지에서 사용하는 공통 함수 모음
 */

// ── API 헬퍼 ──────────────────────────────────────────────────────────────────

const api = {
    /**
     * GET 요청
     * @param {string} url
     * @returns {Promise<any>}
     */
    async get(url) {
        const res = await fetch(url, {
            headers: { 'Accept': 'application/json' }
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }
        return res.json();
    },

    /**
     * POST 요청 (JSON 바디)
     * @param {string} url
     * @param {object} data
     * @returns {Promise<any>}
     */
    async post(url, data = {}) {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }
        // 204 No Content는 빈 응답
        if (res.status === 204) return null;
        return res.json();
    },

    /**
     * PATCH 요청
     * @param {string} url
     * @param {object} data
     * @returns {Promise<any>}
     */
    async patch(url, data = {}) {
        const res = await fetch(url, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }
        if (res.status === 204) return null;
        return res.json();
    },

    /**
     * DELETE 요청
     * @param {string} url
     * @returns {Promise<any>}
     */
    async delete(url) {
        const res = await fetch(url, {
            method: 'DELETE',
            headers: { 'Accept': 'application/json' }
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }
        return null;
    },
};


// ── 토스트 알림 ────────────────────────────────────────────────────────────────

/**
 * 토스트 알림 표시
 * @param {string} message - 표시할 메시지
 * @param {'success'|'error'|'info'} type - 알림 유형
 * @param {number} duration - 표시 시간 (ms)
 */
function showToast(message, type = 'info', duration = 3500) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const icons = { success: '✅', error: '❌', info: 'ℹ️' };
    const colors = {
        success: 'bg-green-600',
        error:   'bg-red-600',
        info:    'bg-blue-600',
    };

    const toast = document.createElement('div');
    toast.className = `flex items-center gap-2 px-4 py-3 rounded-xl shadow-xl text-white text-sm font-medium
        ${colors[type] || colors.info} transform translate-x-full transition-transform duration-300`;
    toast.innerHTML = `<span>${icons[type] || icons.info}</span><span>${message}</span>`;

    container.appendChild(toast);

    // 슬라이드 인
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            toast.classList.remove('translate-x-full');
        });
    });

    // 자동 제거
    setTimeout(() => {
        toast.classList.add('translate-x-full');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}


// ── 날짜/시간 유틸리티 ────────────────────────────────────────────────────────

/**
 * 날짜를 한국어 상대 표현으로 변환
 * @param {string|Date} dateStr
 * @returns {string}
 */
function timeAgo(dateStr) {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);

    if (diff < 60)       return '방금 전';
    if (diff < 3600)     return `${Math.floor(diff / 60)}분 전`;
    if (diff < 86400)    return `${Math.floor(diff / 3600)}시간 전`;
    if (diff < 604800)   return `${Math.floor(diff / 86400)}일 전`;
    return date.toLocaleDateString('ko-KR');
}

/**
 * SEO 점수에 따른 색상 클래스 반환
 * @param {number} score
 * @returns {string}
 */
function seoScoreClass(score) {
    if (score >= 70) return 'text-green-600';
    if (score >= 50) return 'text-yellow-600';
    return 'text-red-600';
}

/**
 * 숫자를 한국어 단위로 포맷
 * @param {number} num
 * @returns {string}
 */
function formatNumber(num) {
    if (num >= 10000) return `${(num / 10000).toFixed(1)}만`;
    if (num >= 1000)  return `${(num / 1000).toFixed(1)}천`;
    return num.toString();
}


// ── 클립보드 ──────────────────────────────────────────────────────────────────

/**
 * 텍스트를 클립보드에 복사
 * @param {string} text
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('클립보드에 복사되었습니다', 'success', 2000);
    } catch {
        showToast('복사 실패', 'error');
    }
}


// ── 모달 헬퍼 ─────────────────────────────────────────────────────────────────

/**
 * 모달 표시
 * @param {string} modalId
 */
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
    }
}

/**
 * 모달 숨기기
 * @param {string} modalId
 */
function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }
}

// 모달 배경 클릭 시 닫기
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('fixed') && e.target.classList.contains('inset-0')) {
        e.target.classList.add('hidden');
    }
});

// ESC 키로 모달 닫기
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        document.querySelectorAll('.fixed.inset-0:not(.hidden)').forEach(modal => {
            modal.classList.add('hidden');
        });
    }
});


// ── 페이지 초기화 ─────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    // 페이지 페이드인 애니메이션
    document.querySelector('main')?.classList.add('animate-fadein');

    // 상대 시간 자동 업데이트 (30초마다)
    const timeElements = document.querySelectorAll('[data-time]');
    if (timeElements.length > 0) {
        timeElements.forEach(el => {
            el.textContent = timeAgo(el.dataset.time);
        });
        setInterval(() => {
            timeElements.forEach(el => {
                el.textContent = timeAgo(el.dataset.time);
            });
        }, 30000);
    }

    // WordPress 연결 상태 체크 (발행 페이지)
    if (window.location.pathname === '/posts') {
        checkWordPressStatus();
    }
});

/**
 * WordPress 연결 상태 비동기 확인
 */
async function checkWordPressStatus() {
    try {
        const res = await api.get('/api/publish/test-connection');
        if (!res.connected) {
            console.warn('WordPress 미연결:', res.message);
        }
    } catch { /* 무시 */ }
}
