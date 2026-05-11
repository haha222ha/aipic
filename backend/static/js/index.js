const WAITING_TIPS = [
    "AI正在理解你的创意，请稍候...",
    "GPT Image 2 擅长文字渲染，试试在提示词中加入文字",
    "提示词越具体，出图效果越好哦",
    "AI正在为你调配色彩，每一笔都独一无二",
    "好的作品值得等待，AI正在精心绘制",
    "试试添加风格关键词，如'水彩风'、'赛博朋克'",
    "GPT Image 2 支持最高4K分辨率输出",
    "反向提示词可以帮助排除不想要的元素",
    "AI绘画就像真正的画家，需要时间构思和创作",
    "每张AI画作都是独一无二的，这是你的专属作品",
    "提示词中描述光影效果可以让画面更有层次感",
    "试试在提示词中加入情绪词，如'温暖'、'神秘'",
    "AI正在将你的想象变为现实...",
    "高清画质仅需3积分，超清10积分",
    "图生图功能可以基于参考图进行创作",
];

const STAGE_DURATIONS = [5, 15, 30, 50];
const QUALITY_CREDITS = { standard: 1, hd: 3, ultra: 10 };

let waitingTimer = null;
let tipTimer = null;
let stageTimer = null;
let waitingStartTime = 0;
let currentTipIndex = 0;
let currentUserInfo = null;
let heroParticles = null;
let loginParticles = null;

document.addEventListener('DOMContentLoaded', () => {
    checkLogin();
    document.getElementById('qualitySelect').addEventListener('change', updateGenCost);
    updateGenCost();
    initHeroParticles();
    initLoginParticles();
    initScrollAnimations();
    initModularLazyLoading();
    initParallaxScroll();
    initScrollProgress();
    initStaggerAnimations();
    initCardTilt();
    initMagneticButtons();
    initBackToTop();
    initStatCounters();
    initNavScroll();
    initGalleryInfiniteScroll();
    initCreditsInfiniteScroll();
});

class ParticleSystem {
    constructor(canvas, options = {}) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.particles = [];
        this.mouse = { x: -1000, y: -1000 };
        this.running = true;
        this.colors = options.colors || ['#6366f1', '#8b5cf6', '#a855f7', '#ec4899', '#3b82f6'];
        this.maxParticles = options.maxParticles || 80;
        this.connectDistance = options.connectDistance || 120;
        this.speed = options.speed || 0.3;
        this.sizeRange = options.sizeRange || [1, 3];

        this.resize();
        this.initParticles();

        this._onResize = () => this.resize();
        this._onMouse = (e) => {
            const rect = this.canvas.getBoundingClientRect();
            this.mouse.x = e.clientX - rect.left;
            this.mouse.y = e.clientY - rect.top;
        };
        this._onMouseLeave = () => {
            this.mouse.x = -1000;
            this.mouse.y = -1000;
        };

        window.addEventListener('resize', this._onResize);
        this.canvas.parentElement.addEventListener('mousemove', this._onMouse);
        this.canvas.parentElement.addEventListener('mouseleave', this._onMouseLeave);

        this.animate();
    }

    resize() {
        const parent = this.canvas.parentElement;
        this.canvas.width = parent.offsetWidth;
        this.canvas.height = parent.offsetHeight;
    }

    initParticles() {
        this.particles = [];
        for (let i = 0; i < this.maxParticles; i++) {
            this.particles.push(this.createParticle());
        }
    }

    createParticle() {
        return {
            x: Math.random() * this.canvas.width,
            y: Math.random() * this.canvas.height,
            vx: (Math.random() - 0.5) * this.speed,
            vy: (Math.random() - 0.5) * this.speed,
            size: Math.random() * (this.sizeRange[1] - this.sizeRange[0]) + this.sizeRange[0],
            color: this.colors[Math.floor(Math.random() * this.colors.length)],
            opacity: Math.random() * 0.5 + 0.2,
            pulse: Math.random() * Math.PI * 2,
            pulseSpeed: Math.random() * 0.02 + 0.005,
        };
    }

    animate() {
        if (!this.running) return;
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        for (let i = 0; i < this.particles.length; i++) {
            const p = this.particles[i];

            p.x += p.vx;
            p.y += p.vy;
            p.pulse += p.pulseSpeed;

            if (p.x < 0) p.x = this.canvas.width;
            if (p.x > this.canvas.width) p.x = 0;
            if (p.y < 0) p.y = this.canvas.height;
            if (p.y > this.canvas.height) p.y = 0;

            const dx = this.mouse.x - p.x;
            const dy = this.mouse.y - p.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < 150) {
                const force = (150 - dist) / 150;
                p.vx -= (dx / dist) * force * 0.02;
                p.vy -= (dy / dist) * force * 0.02;
            }

            p.vx *= 0.99;
            p.vy *= 0.99;

            const currentOpacity = p.opacity + Math.sin(p.pulse) * 0.15;
            const currentSize = p.size + Math.sin(p.pulse) * 0.5;

            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, Math.max(0.5, currentSize), 0, Math.PI * 2);
            this.ctx.fillStyle = p.color;
            this.ctx.globalAlpha = Math.max(0.05, currentOpacity);
            this.ctx.fill();

            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, Math.max(0.5, currentSize * 2), 0, Math.PI * 2);
            this.ctx.fillStyle = p.color;
            this.ctx.globalAlpha = Math.max(0.02, currentOpacity * 0.2);
            this.ctx.fill();

            for (let j = i + 1; j < this.particles.length; j++) {
                const p2 = this.particles[j];
                const ddx = p.x - p2.x;
                const ddy = p.y - p2.y;
                const d = Math.sqrt(ddx * ddx + ddy * ddy);
                if (d < this.connectDistance) {
                    const lineOpacity = (1 - d / this.connectDistance) * 0.15;
                    this.ctx.beginPath();
                    this.ctx.moveTo(p.x, p.y);
                    this.ctx.lineTo(p2.x, p2.y);
                    this.ctx.strokeStyle = p.color;
                    this.ctx.globalAlpha = lineOpacity;
                    this.ctx.lineWidth = 0.5;
                    this.ctx.stroke();
                }
            }
        }

        this.ctx.globalAlpha = 1;
        requestAnimationFrame(() => this.animate());
    }

    destroy() {
        this.running = false;
        window.removeEventListener('resize', this._onResize);
        if (this.canvas.parentElement) {
            this.canvas.parentElement.removeEventListener('mousemove', this._onMouse);
            this.canvas.parentElement.removeEventListener('mouseleave', this._onMouseLeave);
        }
    }
}

function initHeroParticles() {
    const canvas = document.getElementById('particleCanvas');
    if (!canvas) return;
    heroParticles = new ParticleSystem(canvas, {
        maxParticles: 70,
        connectDistance: 130,
        speed: 0.25,
        sizeRange: [1, 3.5],
        colors: ['#6366f1', '#8b5cf6', '#a855f7', '#ec4899', '#3b82f6', '#06b6d4'],
    });
}

function initLoginParticles() {
    const canvas = document.getElementById('loginParticleCanvas');
    if (!canvas) return;
    loginParticles = new ParticleSystem(canvas, {
        maxParticles: 50,
        connectDistance: 100,
        speed: 0.2,
        sizeRange: [1, 2.5],
        colors: ['#6366f1', '#8b5cf6', '#ec4899'],
    });
}

function initScrollAnimations() {
    const lazyObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const rect = entry.target.getBoundingClientRect();
                const viewportCenter = window.innerHeight / 2;
                const isAbove = rect.top < viewportCenter;
                entry.target.style.setProperty('--lazy-direction', isAbove ? '-1' : '1');
                entry.target.classList.add('loaded');
                lazyObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.05, rootMargin: '200px 0px 200px 0px' });

    document.querySelectorAll('.showcase-item.lazy-load:not(.loaded)').forEach(el => {
        lazyObserver.observe(el);
    });

    document.querySelectorAll('.lazy-load:not(.showcase-item):not(.loaded)').forEach(el => {
        lazyObserver.observe(el);
    });

    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

    document.querySelectorAll('.feature-card, .tier-card, .pkg-card, .calc-card, .faq-item').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(24px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        revealObserver.observe(el);
    });

    const style = document.createElement('style');
    style.textContent = `.feature-card.visible, .tier-card.visible, .pkg-card.visible, .calc-card.visible, .faq-item.visible { opacity: 1 !important; transform: translateY(0) !important; }`;
    document.head.appendChild(style);
}

function initModularLazyLoading() {
    const modules = document.querySelectorAll('[data-module]');
    if (modules.length === 0) return;

    const moduleObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            const module = entry.target;
            if (entry.isIntersecting) {
                module.classList.add('module-loading');
                
                setTimeout(() => {
                    module.classList.remove('module-loading');
                    module.classList.add('module-visible');
                }, 100);
            } else {
                module.classList.remove('module-visible', 'module-loading');
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    });

    modules.forEach((module) => {
        module.classList.add('module-hidden');
        moduleObserver.observe(module);
    });
}

function initParallaxScroll() {
    let ticking = false;

    window.addEventListener('scroll', () => {
        if (!ticking) {
            requestAnimationFrame(() => {
                const scrollY = window.pageYOffset;
                const parallaxElements = document.querySelectorAll('.parallax-layer');
                
                parallaxElements.forEach(el => {
                    const speed = parseFloat(el.style.getPropertyValue('--parallax-speed')) || 0.5;
                    const yPos = -(scrollY * speed);
                    el.style.transform = `translateY(${yPos}px)`;
                });

                ticking = false;
            });
            ticking = true;
        }
    });
}

function initScrollProgress() {
    const progressBar = document.createElement('div');
    progressBar.className = 'scroll-progress';
    document.body.appendChild(progressBar);

    window.addEventListener('scroll', () => {
        const scrollTop = window.pageYOffset;
        const docHeight = document.documentElement.scrollHeight - window.innerHeight;
        const scrollPercent = (scrollTop / docHeight) * 100;
        progressBar.style.width = `${scrollPercent}%`;
    });
}

function initStaggerAnimations() {
    const staggerObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate');
                staggerObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.2 });

    document.querySelectorAll('.stagger-children').forEach(el => {
        staggerObserver.observe(el);
    });
}

function initCardTilt() {
    document.querySelectorAll('.card-tilt').forEach(card => {
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            const rotateX = ((y - centerY) / centerY) * -5;
            const rotateY = ((x - centerX) / centerX) * 5;
            card.style.transform = `rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(1.02)`;
        });

        card.addEventListener('mouseleave', () => {
            card.style.transform = 'rotateX(0) rotateY(0) scale(1)';
        });
    });
}

function initMagneticButtons() {
    document.querySelectorAll('.magnetic-btn').forEach(btn => {
        btn.addEventListener('mousemove', (e) => {
            const rect = btn.getBoundingClientRect();
            const x = e.clientX - rect.left - rect.width / 2;
            const y = e.clientY - rect.top - rect.height / 2;
            btn.style.transform = `translate(${x * 0.2}px, ${y * 0.2}px)`;
        });

        btn.addEventListener('mouseleave', () => {
            btn.style.transform = 'translate(0, 0)';
        });
    });
}

function initBackToTop() {
    const btn = document.getElementById('backToTop');
    if (!btn) return;

    let lastScrollY = 0;
    let ticking = false;

    window.addEventListener('scroll', () => {
        lastScrollY = window.pageYOffset;
        
        if (!ticking) {
            requestAnimationFrame(() => {
                if (lastScrollY > 400) {
                    btn.classList.add('visible');
                    if (lastScrollY > 1000) {
                        btn.classList.add('pulse');
                    } else {
                        btn.classList.remove('pulse');
                    }
                } else {
                    btn.classList.remove('visible', 'pulse');
                }
                ticking = false;
            });
            ticking = true;
        }
    });
}

function scrollToTop() {
    const btn = document.getElementById('backToTop');
    if (btn) {
        btn.style.transform = 'scale(0.9)';
        setTimeout(() => {
            btn.style.transform = '';
        }, 150);
    }

    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

function initStatCounters() {
    const statNums = document.querySelectorAll('.stat-num[data-count]');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !entry.target.dataset.animated) {
                entry.target.dataset.animated = 'true';
                animateCounter(entry.target);
            }
        });
    }, { threshold: 0.5 });

    statNums.forEach(el => observer.observe(el));
}

function animateCounter(el) {
    const target = parseInt(el.dataset.count);
    const duration = 1500;
    const start = performance.now();

    function update(now) {
        const elapsed = now - start;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(target * eased);
        if (progress < 1) requestAnimationFrame(update);
    }

    requestAnimationFrame(update);
}

function initNavScroll() {
    const nav = document.getElementById('mainNav');

    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;
        if (currentScroll > 80) {
            nav.classList.add('nav-scrolled');
        } else {
            nav.classList.remove('nav-scrolled');
        }
    });
}

function navigateTo(page) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const target = document.getElementById(`page-${page}`);
    if (target) target.classList.add('active');

    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    const navLink = document.querySelector(`.nav-link[data-page="${page}"]`);
    if (navLink) navLink.classList.add('active');

    if (page === 'studio' && !currentUserInfo) {
        navigateTo('login');
        return;
    }
    if (page === 'gallery' && !currentUserInfo) {
        navigateTo('login');
        return;
    }
    if (page === 'credits' && !currentUserInfo) {
        navigateTo('login');
        return;
    }
    if (page === 'gallery') loadWorks();
    if (page === 'studio') loadStyles();
    if (page === 'credits') loadCreditsPage();
    if (page === 'home') {
        setTimeout(() => {
            initLazyLoadForContainer(document.querySelector('.showcase-grid') || document.getElementById('page-home'));
            initModularLazyLoading();
            initStaggerAnimations();
            initCardTilt();
            initMagneticButtons();
        }, 100);
    }
    if (page === 'login' && loginParticles) {
        setTimeout(() => loginParticles.resize(), 100);
    }

    window.scrollTo(0, 0);
}

async function checkLogin() {
    const res = await apiGet('/api/auth/verify');
    if (res.code === 200 && res.data) {
        currentUserInfo = res.data;
        updateUIForLoggedIn();
    } else {
        updateUIForLoggedOut();
    }
}

function updateUIForLoggedIn() {
    document.getElementById('loginBtn').style.display = 'none';
    document.getElementById('studioBtn').style.display = 'inline-flex';
    document.getElementById('logoutBtn').style.display = 'inline-flex';
    document.getElementById('creditsBadge').style.display = 'flex';
    document.getElementById('creditsNavLink').style.display = 'inline-block';

    const credits = currentUserInfo.credits || 0;
    document.getElementById('creditsCount').textContent = credits;
    document.getElementById('studioCredits').textContent = credits;

    const maxCredits = 500;
    const barWidth = Math.min((credits / maxCredits) * 100, 100);
    document.getElementById('creditsBar').style.width = barWidth + '%';
}

function updateUIForLoggedOut() {
    document.getElementById('loginBtn').style.display = 'inline-flex';
    document.getElementById('studioBtn').style.display = 'none';
    document.getElementById('logoutBtn').style.display = 'none';
    document.getElementById('creditsBadge').style.display = 'none';
    document.getElementById('creditsNavLink').style.display = 'none';
    currentUserInfo = null;
}

async function handleActivate(e) {
    e.preventDefault();
    const authCode = document.getElementById('authCode').value.trim();
    if (!authCode) return;

    const btn = e.target.querySelector('button[type="submit"]');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="btn-shimmer"></span>激活中...';
    btn.disabled = true;

    try {
        const res = await apiPost('/api/auth/activate', { auth_code: authCode });

        if (res.code === 200) {
            currentUserInfo = res.data;
            updateUIForLoggedIn();
            document.getElementById('authCode').value = '';
            btn.innerHTML = originalText;
            btn.disabled = false;
            navigateTo('studio');
        } else {
            alert(res.msg);
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    } catch (err) {
        alert('激活失败，请重试');
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

async function logout() {
    await apiPost('/api/auth/logout', {});
    currentUserInfo = null;
    updateUIForLoggedOut();
    navigateTo('home');
}

function updateGenCost() {
    const quality = document.getElementById('qualitySelect').value;
    const cost = QUALITY_CREDITS[quality] || 1;
    document.getElementById('genCost').textContent = `-${cost}积分`;
}

async function loadStyles() {
    try {
        const res = await apiGet('/api/generate/styles');
        const styleSelect = document.getElementById('styleSelect');
        styleSelect.innerHTML = '<option value="">无风格</option>';
        if (res.code === 200 && res.data.styles) {
            res.data.styles.forEach(style => {
                const opt = document.createElement('option');
                opt.value = style.style_name;
                opt.textContent = `${style.style_name} (${style.category})`;
                styleSelect.appendChild(opt);
            });
        }
    } catch (e) {
        console.error('加载风格列表失败:', e);
    }
}

async function submitGenerate() {
    if (!currentUserInfo) {
        navigateTo('login');
        return;
    }

    const prompt = document.getElementById('prompt').value.trim();
    if (!prompt) { alert('请输入提示词'); return; }

    const ratio = document.getElementById('ratioSelect').value;
    const quality = document.getElementById('qualitySelect').value;

    const data = {
        prompt,
        negative_prompt: document.getElementById('negativePrompt').value.trim(),
        model: 'gpt-image-2',
        style: document.getElementById('styleSelect').value,
        ratio,
        seed: parseInt(document.getElementById('seed').value) || -1,
        quality,
    };

    const btn = document.getElementById('generateBtn');
    btn.disabled = true;
    btn.style.opacity = '0.7';

    const res = await apiPost('/api/generate/text2img', data);

    btn.disabled = false;
    btn.style.opacity = '1';

    if (res.code === 200) {
        showWaitingOverlay(prompt);
        pollTaskStatus(res.data.task_id);
    } else {
        alert(res.msg);
    }
}

function showWaitingOverlay(prompt) {
    const overlay = document.getElementById('waitingOverlay');
    overlay.style.display = 'flex';
    overlay.classList.remove('hiding', 'success-flash');

    document.getElementById('promptPreview').textContent = `"${prompt}"`;

    resetStages();
    setStage(0);

    waitingStartTime = Date.now();
    currentTipIndex = Math.floor(Math.random() * WAITING_TIPS.length);
    updateTip();

    waitingTimer = setInterval(() => {
        const elapsed = Math.floor((Date.now() - waitingStartTime) / 1000);
        const mins = Math.floor(elapsed / 60);
        const secs = elapsed % 60;
        document.getElementById('waitingTimer').textContent =
            mins > 0 ? `已等待 ${mins} 分 ${secs} 秒` : `已等待 ${secs} 秒`;
    }, 1000);

    tipTimer = setInterval(() => {
        currentTipIndex = (currentTipIndex + 1) % WAITING_TIPS.length;
        updateTip();
    }, 5000);

    stageTimer = setInterval(() => {
        const elapsed = Math.floor((Date.now() - waitingStartTime) / 1000);
        autoAdvanceStage(elapsed);
    }, 2000);
}

function hideWaitingOverlay(success) {
    clearInterval(waitingTimer);
    clearInterval(tipTimer);
    clearInterval(stageTimer);

    const overlay = document.getElementById('waitingOverlay');

    if (success) {
        completeAllStages();
        overlay.classList.add('success-flash');
        setTimeout(() => {
            overlay.classList.add('hiding');
            setTimeout(() => {
                overlay.style.display = 'none';
                overlay.classList.remove('hiding', 'success-flash');
            }, 500);
        }, 800);
    } else {
        overlay.classList.add('hiding');
        setTimeout(() => {
            overlay.style.display = 'none';
            overlay.classList.remove('hiding');
        }, 500);
    }
}

function resetStages() {
    for (let i = 0; i < 4; i++) {
        const stage = document.getElementById(`stage-${i}`);
        stage.classList.remove('active', 'completed');
    }
    for (let i = 0; i < 3; i++) {
        document.getElementById(`stageLine${i}`).style.width = '0%';
    }
}

function setStage(index) {
    for (let i = 0; i < 4; i++) {
        const stage = document.getElementById(`stage-${i}`);
        if (i < index) {
            stage.classList.remove('active');
            stage.classList.add('completed');
        } else if (i === index) {
            stage.classList.remove('completed');
            stage.classList.add('active');
        } else {
            stage.classList.remove('active', 'completed');
        }
    }
    for (let i = 0; i < 3; i++) {
        if (i < index) {
            document.getElementById(`stageLine${i}`).style.width = '100%';
        } else if (i === index) {
            document.getElementById(`stageLine${i}`).style.width = '50%';
        } else {
            document.getElementById(`stageLine${i}`).style.width = '0%';
        }
    }
}

function completeAllStages() {
    for (let i = 0; i < 4; i++) {
        const stage = document.getElementById(`stage-${i}`);
        stage.classList.remove('active');
        stage.classList.add('completed');
    }
    for (let i = 0; i < 3; i++) {
        document.getElementById(`stageLine${i}`).style.width = '100%';
    }
}

function autoAdvanceStage(elapsed) {
    let stageIndex = 0;
    for (let i = 0; i < STAGE_DURATIONS.length; i++) {
        if (elapsed >= STAGE_DURATIONS[i]) {
            stageIndex = i;
        }
    }
    setStage(stageIndex);
}

function updateTip() {
    const tipText = document.getElementById('tipText');
    tipText.style.animation = 'none';
    tipText.offsetHeight;
    tipText.textContent = WAITING_TIPS[currentTipIndex];
    tipText.style.animation = 'tipFadeIn 0.5s ease';
}

async function pollTaskStatus(taskId) {
    const maxAttempts = 120;
    let attempt = 0;

    const poll = async () => {
        attempt++;
        if (attempt > maxAttempts) {
            hideWaitingOverlay(false);
            alert('生成超时，请稍后查看');
            return;
        }

        const res = await apiGet(`/api/generate/status/${taskId}`);
        if (res.code !== 200) {
            hideWaitingOverlay(false);
            alert('查询失败');
            return;
        }

        const task = res.data;
        if (task.status === '已完成') {
            hideWaitingOverlay(true);

            document.getElementById('studioEmpty').style.display = 'none';
            const resultDiv = document.getElementById('studioResult');
            resultDiv.style.display = 'block';

            if (task.output_image_path) {
                const imgSrc = `/static/outputs/${task.output_image_path.split('/').pop()}`;
                document.getElementById('resultImg').src = imgSrc;
            }

            const qualityLabel = { standard: '标准', hd: '高清', ultra: '超清', master: '大师' }[task.quality_tier] || '标准';
            const ratioLabels = { square: '1:1', portrait_34: '3:4', portrait_916: '9:16', landscape_43: '4:3', landscape_169: '16:9' };
            const ratioLabel = ratioLabels[task.ratio_key] || '1:1';
            document.getElementById('resultMeta').textContent =
                `${ratioLabel} · ${qualityLabel} · 消耗${task.credits_cost}积分`;

            checkLogin();
        } else if (task.status === '失败') {
            hideWaitingOverlay(false);
            alert(`生成失败: ${task.fail_reason || '未知错误'}`);
            checkLogin();
        } else {
            setTimeout(poll, 2000);
        }
    };

    poll();
}

let galleryPage = 1;
let galleryLoading = false;
let galleryHasMore = true;

let galleryFilterType = 'all';

async function loadWorks(page = 1, append = false) {
    if (galleryLoading) return;
    galleryLoading = true;

    let url = `/api/user/works?page=${page}&size=20`;
    if (galleryFilterType && galleryFilterType !== 'all') {
        url += `&type=${galleryFilterType}`;
    }

    const res = await apiGet(url);
    if (res.code !== 200) { galleryLoading = false; return; }

    const grid = document.getElementById('galleryGrid');

    if (!append) {
        grid.innerHTML = '';
        galleryPage = 1;
        galleryHasMore = true;
    }

    if (!res.data.works || res.data.works.length === 0) {
        if (!append) {
            grid.innerHTML = `
                <div class="gallery-empty">
                    <div class="gallery-empty-icon">&#9998;</div>
                    <div class="gallery-empty-text">
                        <h3>你的画廊还是空的</h3>
                        <p>去创作工坊开始你的第一幅AI画作吧</p>
                    </div>
                    <button class="gallery-empty-btn" onclick="navigateTo('studio')">立即创作</button>
                </div>
            `;
        }
        galleryHasMore = false;
        galleryLoading = false;
        return;
    }

    const qualityLabels = { standard: '标准', hd: '高清', ultra: '超清', master: '大师' };
    const ratioLabels = { square: '1:1', portrait_34: '3:4', portrait_916: '9:16', landscape_43: '4:3', landscape_169: '16:9' };

    res.data.works.forEach((work, i) => {
        const card = document.createElement('div');
        card.className = 'work-card lazy-load';
        card.style.animationDelay = `${i * 0.05}s`;
        const imgSrc = work.output_image_path
            ? `/static/outputs/${work.output_image_path.split('/').pop()}`
            : '';
        const qLabel = qualityLabels[work.quality_tier] || '标准';
        const qClass = `q-${work.quality_tier || 'standard'}`;
        const rLabel = ratioLabels[work.ratio_key] || '1:1';
        const time = work.finish_time ? work.finish_time.substring(5, 16).replace('T', ' ') : '';

        card.innerHTML = `
            <img src="${imgSrc}" alt="" loading="lazy" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22200%22><rect fill=%22%2316161f%22 width=%22200%22 height=%22200%22/><text x=%2250%25%22 y=%2250%25%22 fill=%22%236a6a82%22 text-anchor=%22middle%22 dy=%22.3em%22 font-size=%2214%22>暂无预览</text></svg>'">
            <div class="work-info">
                <div class="work-prompt">${work.prompt.substring(0, 50)}${work.prompt.length > 50 ? '...' : ''}</div>
            </div>
            <div class="work-meta">
                <span>${rLabel} · ${time}</span>
                <span class="work-quality ${qClass}">${qLabel}</span>
            </div>
        `;
        grid.appendChild(card);
    });

    galleryPage = page;
    galleryHasMore = res.data.works.length >= 20;
    galleryLoading = false;

    initLazyLoadForContainer(grid);
}

function initLazyLoadForContainer(container) {
    const items = Array.from(container.querySelectorAll('.lazy-load:not(.loaded)'));
    if (items.length === 0) return;

    const lazyObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const index = items.indexOf(entry.target);
                const staggerDelay = (index % 4) * 80;
                setTimeout(() => {
                    entry.target.classList.add('loaded');
                }, staggerDelay);
                lazyObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.05, rootMargin: '200px 0px 200px 0px' });

    items.forEach(el => {
        lazyObserver.observe(el);
    });
}

function initGalleryInfiniteScroll() {
    const sentinel = document.getElementById('gallerySentinel');
    if (!sentinel) return;

    const scrollObserver = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting && galleryHasMore && !galleryLoading && currentUserInfo) {
            loadWorks(galleryPage + 1, true);
        }
    }, { rootMargin: '200px' });

    scrollObserver.observe(sentinel);
}

function filterWorks(type, btn) {
    document.querySelectorAll('.gallery-header .filter-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    galleryFilterType = type || 'all';
    loadWorks(1);
}

function toggleFaq(el) {
    el.parentElement.classList.toggle('open');
}

function downloadResult() {
    const img = document.getElementById('resultImg');
    if (!img || !img.src) return;

    const link = document.createElement('a');
    link.href = img.src;
    link.download = `artforge_${Date.now()}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function showBuyModal(pkgName) {
    const modal = document.getElementById('buyModal');
    const title = document.getElementById('modalTitle');
    const body = document.getElementById('modalBody');

    title.textContent = `获取「${pkgName}」授权码`;

    body.innerHTML = `
        <p>请联系管理员购买「${pkgName}」授权码，激活后即可获得对应积分。</p>
        <div style="margin-top:16px;padding:16px;background:var(--bg-input);border-radius:8px;border:1px solid var(--border);">
            <p style="font-size:0.85rem;color:var(--text-secondary);">💡 购买方式：添加客服微信或访问官方渠道获取授权码</p>
        </div>
        <p style="margin-top:12px;font-size:0.8rem;color:var(--text-muted);">已有授权码？直接在登录页输入即可激活</p>
    `;

    modal.style.display = 'flex';
}

function closeBuyModal() {
    document.getElementById('buyModal').style.display = 'none';
}

let creditsPage = 1;
let creditsLoading = false;
let creditsHasMore = true;
let creditsCurrentFilter = '';

async function loadCreditsPage() {
    await loadCreditsSummary();
    await loadCreditsLog(1, creditsCurrentFilter);
}

async function loadCreditsSummary() {
    const res = await apiGet('/api/user/credits/summary');
    if (res.code !== 200) return;

    const d = res.data;
    document.getElementById('csCurrent').textContent = d.current_credits || 0;
    document.getElementById('csPurchased').textContent = d.total_purchased || 0;
    document.getElementById('csUsed').textContent = d.total_used || 0;
    document.getElementById('csGenerated').textContent = d.total_generated || 0;

    const statsEl = document.getElementById('creditsQualityStats');
    const qualityColors = { standard: '#8b5cf6', hd: '#3b82f6', ultra: '#ec4899' };
    const qualityLabels = { standard: '标准', hd: '高清', ultra: '超清' };
    let statsHtml = '';
    if (d.quality_breakdown) {
        for (const [tier, info] of Object.entries(d.quality_breakdown)) {
            const color = qualityColors[tier] || '#6b7280';
            const label = qualityLabels[tier] || tier;
            statsHtml += `<div class="cqs-item"><span class="cqs-dot" style="background:${color}"></span>${label}：<span class="cqs-count">${info.count}张</span> / ${info.total_cost || 0}积分</div>`;
        }
    }
    statsEl.innerHTML = statsHtml;
}

async function loadCreditsLog(page, type, append = false) {
    if (creditsLoading) return;
    creditsLoading = true;
    creditsPage = page;
    creditsCurrentFilter = type;

    let url = `/api/user/credits/log?page=${page}&size=20`;
    if (type) url += `&type=${type}`;

    const res = await apiGet(url);
    if (res.code !== 200) { creditsLoading = false; return; }

    const grid = document.getElementById('creditsCardGrid');
    if (!append) {
        grid.innerHTML = '';
        creditsPage = 1;
        creditsHasMore = true;
    }

    const typeLabels = { consume: '消费', purchase: '充值', refund: '退还', daily: '每日赠送', admin_adjust: '管理员调整' };

    if (!res.data.logs || res.data.logs.length === 0) {
        if (!append) {
            grid.innerHTML = '<p style="text-align:center;color:var(--text-muted);padding:60px 0;column-span:all;">暂无记录</p>';
        }
        creditsHasMore = false;
        creditsLoading = false;
        document.getElementById('creditsPagination').innerHTML = '';
        return;
    }

    res.data.logs.forEach((log, i) => {
        const typeLabel = typeLabels[log.change_type] || log.change_type;
        const typeClass = `type-${log.change_type || 'consume'}`;
        const amountClass = log.change_amount >= 0 ? 'positive' : 'negative';
        const amountText = log.change_amount >= 0 ? `+${log.change_amount}` : `${log.change_amount}`;
        const time = log.create_time ? log.create_time.substring(5, 16).replace('T', ' ') : '';

        const card = document.createElement('div');
        card.className = `credit-card lazy-load ${typeClass}`;
        card.style.animationDelay = `${i * 0.04}s`;
        card.innerHTML = `
            <span class="cc-type">${typeLabel}</span>
            <div class="cc-amount ${amountClass}">${amountText}</div>
            <div class="cc-desc">${log.description || ''}</div>
            <div class="cc-footer">
                <span>${time}</span>
                <span class="cc-balance">余额 ${log.balance_after}</span>
            </div>
        `;
        grid.appendChild(card);
    });

    creditsPage = page;
    creditsHasMore = res.data.logs.length >= 20;
    creditsLoading = false;
    document.getElementById('creditsPagination').innerHTML = '';

    initLazyLoadForContainer(grid);
}

function initCreditsInfiniteScroll() {
    const sentinel = document.getElementById('creditsSentinel');
    if (!sentinel) return;

    const scrollObserver = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting && creditsHasMore && !creditsLoading && currentUserInfo) {
            loadCreditsLog(creditsPage + 1, creditsCurrentFilter, true);
        }
    }, { rootMargin: '200px' });

    scrollObserver.observe(sentinel);
}

function filterCredits(type, btn) {
    document.querySelectorAll('.credits-filters .filter-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    loadCreditsLog(1, type);
}
