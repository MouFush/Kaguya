let starfieldEnabled = false;
        let starfieldAnimId = null;
        let stars = [];
        let shootingStars = [];

        function initStarfield() {
            const canvas = document.getElementById('starfieldCanvas');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;

            stars = [];
            const starCount = Math.floor((canvas.width * canvas.height) / 1500);
            for (let i = 0; i < starCount; i++) {
                stars.push({
                    x: Math.random() * canvas.width,
                    y: Math.random() * canvas.height,
                    radius: Math.random() * 2.2 + 0.3,
                    alpha: Math.random() * 0.9 + 0.3,
                    twinkleSpeed: Math.random() * 0.025 + 0.008,
                    twinkleOffset: Math.random() * Math.PI * 2,
                    color: getStarColor()
                });
            }

            function getStarColor() {
                const colors = [
                    'rgba(255,255,255,',
                    'rgba(200,220,255,',
                    'rgba(180,200,255,',
                    'rgba(255,230,200,',
                    'rgba(200,180,255,',
                    'rgba(125,211,252,',
                    'rgba(192,132,252,',
                    'rgba(240,171,252,',
                    'rgba(94,234,212,'
                ];
                return colors[Math.floor(Math.random() * colors.length)];
            }

            function spawnShootingStar() {
                if (!starfieldEnabled) return;
                if (shootingStars.length < 5 && Math.random() < 0.015) {
                    const startX = Math.random() * canvas.width * 0.8;
                    const startY = Math.random() * canvas.height * 0.4;
                    const angle = Math.PI / 4 + (Math.random() - 0.5) * 0.3;
                    shootingStars.push({
                        x: startX, y: startY,
                        vx: Math.cos(angle) * (6 + Math.random() * 4),
                        vy: Math.sin(angle) * (6 + Math.random() * 4),
                        life: 1.0,
                        decay: 0.012 + Math.random() * 0.008,
                        length: 60 + Math.random() * 80,
                        width: 1 + Math.random() * 1.5
                    });
                }
            }

            function drawStarfield() {
                if (!starfieldEnabled) return;
                ctx.clearRect(0, 0, canvas.width, canvas.height);

                const time = Date.now() * 0.001;

                for (const star of stars) {
                    const twinkle = Math.sin(time * star.twinkleSpeed * 60 + star.twinkleOffset);
                    const alpha = star.alpha * (0.6 + 0.4 * twinkle);
                    const radius = star.radius * (0.8 + 0.2 * twinkle);

                    ctx.beginPath();
                    ctx.arc(star.x, star.y, radius, 0, Math.PI * 2);
                    ctx.fillStyle = star.color + alpha.toFixed(3) + ')';
                    ctx.fill();

                    if (star.radius > 1.2) {
                        ctx.beginPath();
                        ctx.arc(star.x, star.y, radius * 3, 0, Math.PI * 2);
                        const grad = ctx.createRadialGradient(star.x, star.y, 0, star.x, star.y, radius * 3);
                        grad.addColorStop(0, star.color + (alpha * 0.3).toFixed(3) + ')');
                        grad.addColorStop(1, star.color + '0)');
                        ctx.fillStyle = grad;
                        ctx.fill();
                    }
                }

                spawnShootingStar();

                for (let i = shootingStars.length - 1; i >= 0; i--) {
                    const ss = shootingStars[i];
                    ss.x += ss.vx;
                    ss.y += ss.vy;
                    ss.life -= ss.decay;

                    if (ss.life <= 0) {
                        shootingStars.splice(i, 1);
                        continue;
                    }

                    const tailX = ss.x - (ss.vx / Math.sqrt(ss.vx * ss.vx + ss.vy * ss.vy)) * ss.length * ss.life;
                    const tailY = ss.y - (ss.vy / Math.sqrt(ss.vx * ss.vx + ss.vy * ss.vy)) * ss.length * ss.life;

                    const grad = ctx.createLinearGradient(tailX, tailY, ss.x, ss.y);
                    grad.addColorStop(0, 'rgba(255,255,255,0)');
                    grad.addColorStop(0.6, 'rgba(125,211,252,' + (ss.life * 0.5).toFixed(3) + ')');
                    grad.addColorStop(1, 'rgba(255,255,255,' + ss.life.toFixed(3) + ')');

                    ctx.beginPath();
                    ctx.moveTo(tailX, tailY);
                    ctx.lineTo(ss.x, ss.y);
                    ctx.strokeStyle = grad;
                    ctx.lineWidth = ss.width * ss.life;
                    ctx.lineCap = 'round';
                    ctx.stroke();

                    ctx.beginPath();
                    ctx.arc(ss.x, ss.y, 2 * ss.life, 0, Math.PI * 2);
                    ctx.fillStyle = 'rgba(255,255,255,' + (ss.life * 0.8).toFixed(3) + ')';
                    ctx.fill();
                }

                starfieldAnimId = requestAnimationFrame(drawStarfield);
            }

            drawStarfield();

            window.addEventListener('resize', () => {
                canvas.width = window.innerWidth;
                canvas.height = window.innerHeight;
                stars = [];
                const newCount = Math.floor((canvas.width * canvas.height) / 1500);
                for (let i = 0; i < newCount; i++) {
                    stars.push({
                        x: Math.random() * canvas.width,
                        y: Math.random() * canvas.height,
                        radius: Math.random() * 2.2 + 0.3,
                        alpha: Math.random() * 0.9 + 0.3,
                        twinkleSpeed: Math.random() * 0.025 + 0.008,
                        twinkleOffset: Math.random() * Math.PI * 2,
                        color: getStarColor()
                    });
                }
            });
        }

        function enableStarfieldMode() {
            starfieldEnabled = true;
            if (wallpaperEnabled) disableWallpaperMode();
            document.body.classList.add('starfield-mode');
            if (!document.body.classList.contains('dark')) {
                document.body.classList.add('dark');
                settings.dark = true;
                const dm = $('darkModeToggle');
                if (dm) dm.checked = true;
            }
            const canvas = document.getElementById('starfieldCanvas');
            if (canvas) canvas.style.display = 'block';
            const n1 = document.getElementById('nebula1');
            const n2 = document.getElementById('nebula2');
            const n3 = document.getElementById('nebula3');
            if (n1) n1.style.display = 'block';
            if (n2) n2.style.display = 'block';
            if (n3) n3.style.display = 'block';
            if (!starfieldAnimId) initStarfield();
            const btn = document.getElementById('starfieldBtn');
            if (btn) btn.classList.add('active');
            localStorage.setItem('kaguya_starfield', 'true');
            showToast('🌌 星空模式已开启');
        }

        function disableStarfieldMode() {
            starfieldEnabled = false;
            document.body.classList.remove('starfield-mode');
            if (starfieldAnimId) {
                cancelAnimationFrame(starfieldAnimId);
                starfieldAnimId = null;
            }
            const canvas = document.getElementById('starfieldCanvas');
            if (canvas) {
                const ctx = canvas.getContext('2d');
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                canvas.style.display = 'none';
            }
            const n1 = document.getElementById('nebula1');
            const n2 = document.getElementById('nebula2');
            const n3 = document.getElementById('nebula3');
            if (n1) n1.style.display = 'none';
            if (n2) n2.style.display = 'none';
            if (n3) n3.style.display = 'none';
            const btn = document.getElementById('starfieldBtn');
            if (btn) btn.classList.remove('active');
            localStorage.setItem('kaguya_starfield', 'false');
        }

        function toggleStarfieldMode() {
            if (starfieldEnabled) {
                disableStarfieldMode();
                showToast('星空模式已关闭');
            } else {
                enableStarfieldMode();
            }
        }

        let wallpaperEnabled = false;

        function enableWallpaperMode() {
            wallpaperEnabled = true;
            if (starfieldEnabled) disableStarfieldMode();
            document.body.classList.add('wallpaper-mode');
            if (!document.body.classList.contains('dark')) {
                document.body.classList.add('dark');
                settings.dark = true;
                const dm = $('darkModeToggle');
                if (dm) dm.checked = true;
            }
            const btn = document.getElementById('wallpaperBtn');
            if (btn) btn.classList.add('active');
            localStorage.setItem('kaguya_wallpaper', 'true');
            showToast('🖼️ 壁纸模式已开启');
        }

        function disableWallpaperMode() {
            wallpaperEnabled = false;
            document.body.classList.remove('wallpaper-mode');
            const btn = document.getElementById('wallpaperBtn');
            if (btn) btn.classList.remove('active');
            localStorage.setItem('kaguya_wallpaper', 'false');
        }

        function toggleWallpaperMode() {
            if (wallpaperEnabled) {
                disableWallpaperMode();
                showToast('壁纸模式已关闭');
            } else {
                enableWallpaperMode();
            }
        }

        if (localStorage.getItem('kaguya_wallpaper') === 'true') {
            setTimeout(enableWallpaperMode, 300);
        }
        if (localStorage.getItem('kaguya_starfield') === 'true') {
            setTimeout(enableStarfieldMode, 300);
        }
