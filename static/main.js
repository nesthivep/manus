// 动态产生随机粒子
function createRandomParticle() {
    const container = document.querySelector('.particle-container');

    if (!container) return;

    setInterval(() => {
        const particle = document.createElement('div');
        particle.className = 'particle';

        // 随机位置
        particle.style.left = `${Math.random() * 100}%`;
        particle.style.top = '100%';

        // 随机大小
        const size = Math.random() * 2 + 1;
        particle.style.width = `${size}px`;
        particle.style.height = `${size}px`;

        // 获取CSS变量
        const styles = getComputedStyle(document.documentElement);
        const colorOptions = [
            styles.getPropertyValue('--accent-green').trim(),
            styles.getPropertyValue('--accent-color-5').trim(),
            styles.getPropertyValue('--accent-blue').trim(),
            styles.getPropertyValue('--accent-color-1').trim()
        ];

        // 随机颜色
        const randomColor = colorOptions[Math.floor(Math.random() * colorOptions.length)];
        particle.style.backgroundColor = randomColor;
        particle.style.boxShadow = `0 0 5px ${randomColor}`;

        // 随机透明度
        particle.style.opacity = (Math.random() * 0.5 + 0.3).toString();

        // 添加到容器
        container.appendChild(particle);

        // 设置动画结束后移除元素
        setTimeout(() => {
            particle.remove();
        }, 5000);
    }, 600); // 每600ms创建一个新粒子
}

// 添加主题选项动画效果
function animateThemeOptions() {
    const themeOptions = document.querySelectorAll('.theme-option');
    themeOptions.forEach((option, index) => {
        // 直接显示元素，不使用动画过渡
        option.style.opacity = '1';
    });
}

// 页面加载完成后初始化效果
document.addEventListener('DOMContentLoaded', function() {
    // 初始化粒子效果
    createRandomParticle();

    // 初始化主题选项动画
    animateThemeOptions();
});
