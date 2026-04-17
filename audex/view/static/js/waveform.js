// Waveform Visualizer for Audio Input
class WaveformVisualizer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) {
            console.error('Canvas not found:', canvasId);
            return;
        }

        this.ctx = this.canvas.getContext('2d');
        this.isRecording = false;
        this.audioContext = null;
        this.analyser = null;
        this.dataArray = null;
        this.bufferLength = 0;
        this.animationId = null;

        // Waveform settings
        this.barCount = 64;
        this.barHeights = new Array(this.barCount).fill(0);
        this.targetHeights = new Array(this.barCount).fill(0);
        this.smoothingFactor = 0.15;

        this.resize();
        window.addEventListener('resize', () => this.resize());
    }

    resize() {
        const dpr = window.devicePixelRatio || 1;
        const rect = this.canvas.getBoundingClientRect();

        this.canvas.width = rect.width * dpr;
        this.canvas.height = rect.height * dpr;

        this.ctx.scale(dpr, dpr);
        this.canvasWidth = rect.width;
        this.canvasHeight = rect.height;
    }

    async start() {
        if (this.isRecording) return;

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });

            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 128;
            this.bufferLength = this.analyser.frequencyBinCount;
            this.dataArray = new Uint8Array(this.bufferLength);

            const source = this.audioContext.createMediaStreamSource(stream);
            source.connect(this.analyser);

            this.isRecording = true;
            this.animate();
        } catch (err) {
            console.error('Error accessing microphone:', err);
        }
    }

    stop() {
        this.isRecording = false;

        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }

        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }

        // Smoothly animate bars down to 0
        const fadeOut = () => {
            let allZero = true;
            for (let i = 0; i < this.barCount; i++) {
                if (this.barHeights[i] > 0.5) {
                    this.barHeights[i] *= 0.85;
                    allZero = false;
                }
            }

            this.draw();

            if (!allZero) {
                requestAnimationFrame(fadeOut);
            }
        };

        fadeOut();
    }

    animate() {
        if (!this.isRecording) return;

        this.animationId = requestAnimationFrame(() => this.animate());

        this.analyser.getByteFrequencyData(this.dataArray);

        // Update target heights based on audio data
        for (let i = 0; i < this.barCount; i++) {
            const dataIndex = Math.floor((i / this.barCount) * this.bufferLength);
            const value = this.dataArray[dataIndex] || 0;
            this.targetHeights[i] = (value / 255) * 100;
        }

        // Smooth interpolation
        for (let i = 0; i < this.barCount; i++) {
            this.barHeights[i] += (this.targetHeights[i] - this.barHeights[i]) * this.smoothingFactor;
        }

        this.draw();
    }

    draw() {
        const ctx = this.ctx;
        const width = this.canvasWidth;
        const height = this.canvasHeight;

        // Clear canvas - fully transparent
        ctx.clearRect(0, 0, width, height);

        // Calculate bar dimensions
        const barWidth = Math.max(4, width / this.barCount * 0.75);
        const gap = width / this.barCount * 0.25;
        const centerY = height / 2;

        // Draw waveform bars
        for (let i = 0; i < this.barCount; i++) {
            const x = i * (barWidth + gap) + gap / 2;
            const normalizedHeight = Math.max(3, (this.barHeights[i] / 100) * (height * 0.85));

            // Create gradient for each bar
            const gradient = ctx.createLinearGradient(x, centerY - normalizedHeight / 2, x, centerY + normalizedHeight / 2);

            // Dynamic color based on height
            const intensity = this.barHeights[i] / 100;
            const r = Math.floor(102 + intensity * 50);
            const g = Math.floor(126 - intensity * 20);
            const b = Math.floor(234 - intensity * 72);

            gradient.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0.3)`);
            gradient.addColorStop(0.5, `rgba(${r}, ${g}, ${b}, 0.9)`);
            gradient.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0.3)`);

            ctx.fillStyle = gradient;

            // Draw rounded rectangle bars
            this.roundRect(ctx, x, centerY - normalizedHeight / 2, barWidth, normalizedHeight, barWidth / 2);

            // Add glow effect for active bars
            if (this.barHeights[i] > 30) {
                ctx.shadowBlur = 12;
                ctx.shadowColor = `rgba(${r}, ${g}, ${b}, ${intensity * 0.6})`;
                this.roundRect(ctx, x, centerY - normalizedHeight / 2, barWidth, normalizedHeight, barWidth / 2);
                ctx.shadowBlur = 0;
            }
        }
    }

    roundRect(ctx, x, y, width, height, radius) {
        ctx.beginPath();
        ctx.moveTo(x + radius, y);
        ctx.lineTo(x + width - radius, y);
        ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
        ctx.lineTo(x + width, y + height - radius);
        ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
        ctx.lineTo(x + radius, y + height);
        ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
        ctx.lineTo(x, y + radius);
        ctx.quadraticCurveTo(x, y, x + radius, y);
        ctx.closePath();
        ctx.fill();
    }
}

// Global instance
let waveformVisualizer = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    waveformVisualizer = new WaveformVisualizer('waveform-canvas');
});

// Expose control functions
window.startWaveform = () => {
    if (waveformVisualizer) {
        waveformVisualizer.start();
    }
};

window.stopWaveform = () => {
    if (waveformVisualizer) {
        waveformVisualizer.stop();
    }
};