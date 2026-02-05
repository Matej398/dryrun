"""
DRYRUN Bot Component - Animated Pixel Bot for Dashboard Header
Tamagotchi-style bot with expressions, typewriter messages, and sound
"""

# =============================================================================
# BOT CSS - Styling and Animations
# =============================================================================

BOT_CSS = """
/* Header Frame */
.header-frame {
    background: #0E1218;
    border: 1px solid #171E27;
    padding: 8px 12px;
    margin-bottom: 15px;
    display: flex;
    align-items: center;
    gap: 12px;
}

/* Pixel Bot Container */
.bot-container {
    width: 25px;
    height: 20px;
    flex-shrink: 0;
}

.pixel-bot {
    width: 100%;
    height: 100%;
}

/* Bot pixel styling - single white color */
.bot-pixel {
    fill: none;
}
.bot-border {
    fill: #f0f6fc;
}
.bot-eye {
    fill: #f0f6fc;
    transition: opacity 0.1s;
}
.bot-mouth {
    fill: #f0f6fc;
}

/* Blink animation */
@keyframes blink {
    0%, 90%, 100% { opacity: 1; }
    95% { opacity: 0; }
}
.bot-eye {
    animation: blink 4s infinite;
}

/* Sleep mode - eyes closed */
.bot-sleeping .bot-eye {
    animation: none;
    opacity: 0;
}
.bot-sleeping .bot-eye-closed {
    opacity: 1;
}
.bot-eye-closed {
    opacity: 0;
    fill: #f0f6fc;
}

/* Loading mode - eyes look around */
@keyframes lookAround {
    0%, 100% { transform: translateX(0); }
    25% { transform: translateX(2px); }
    75% { transform: translateX(-2px); }
}
.bot-loading .bot-eye {
    animation: lookAround 1s infinite;
}

/* Happy expression (default) */
.bot-happy .bot-mouth-happy { opacity: 1; }
.bot-happy .bot-mouth-sad { opacity: 0; }

/* Sad expression */
.bot-sad .bot-mouth-happy { opacity: 0; }
.bot-sad .bot-mouth-sad { opacity: 1; }

.bot-mouth-sad {
    opacity: 0;
    fill: #f0f6fc;
}

/* Message Area */
.message-area {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 13px;
    color: #67778E;
    overflow: hidden;
}

.message-text {
    white-space: nowrap;
    overflow: hidden;
}

.message-text.info { color: #67778E; }
.message-text.trade { color: #3CE3AB; }
.message-text.error { color: #F23674; }
.message-text.win { color: #3CE3AB; }
.message-text.loss { color: #F23674; }

/* Blinking cursor */
.cursor {
    display: inline-block;
    width: 2px;
    height: 16px;
    background: #67778E;
    margin-left: 2px;
    animation: cursorBlink 1s infinite;
}
@keyframes cursorBlink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
}

/* Version badge */
.version-badge {
    font-size: 11px;
    color: #67778E;
    padding: 4px 8px;
    background: #171E27;
    flex-shrink: 0;
}

/* Sound toggle (pixel bell) */
.sound-toggle {
    width: 16px;
    height: 16px;
    cursor: pointer;
    flex-shrink: 0;
    opacity: 0.6;
    transition: opacity 0.2s;
}
.sound-toggle:hover {
    opacity: 1;
}
.sound-toggle.muted .bell-on { opacity: 0; }
.sound-toggle.muted .bell-off { opacity: 1; }
.sound-toggle .bell-off { opacity: 0; }
.bell-pixel {
    fill: #f0f6fc;
}
"""

# =============================================================================
# BOT HTML - SVG Pixel Art
# =============================================================================

BOT_HTML = """
<div class="header-frame">
    <div class="bot-container">
        <svg class="pixel-bot bot-happy" id="pixel-bot" viewBox="0 0 10 8" xmlns="http://www.w3.org/2000/svg">
            <!-- Border - top -->
            <rect class="bot-border" x="0" y="0" width="10" height="1"/>
            <!-- Border - bottom -->
            <rect class="bot-border" x="0" y="7" width="10" height="1"/>
            <!-- Border - left -->
            <rect class="bot-border" x="0" y="1" width="1" height="6"/>
            <!-- Border - right -->
            <rect class="bot-border" x="9" y="1" width="1" height="6"/>
            
            <!-- Left Eye (1x1) -->
            <rect class="bot-eye" x="3" y="2" width="1" height="1"/>
            <!-- Right Eye (1x1) -->
            <rect class="bot-eye" x="6" y="2" width="1" height="1"/>
            
            <!-- Closed eyes (for sleep) -->
            <rect class="bot-eye-closed" x="3" y="2" width="1" height="1"/>
            <rect class="bot-eye-closed" x="6" y="2" width="1" height="1"/>
            
            <!-- Happy Mouth (smile) -->
            <g class="bot-mouth-happy">
                <rect class="bot-mouth" x="2" y="4" width="1" height="1"/>
                <rect class="bot-mouth" x="7" y="4" width="1" height="1"/>
                <rect class="bot-mouth" x="3" y="5" width="4" height="1"/>
            </g>
            
            <!-- Sad Mouth (frown - hidden by default) -->
            <g class="bot-mouth-sad">
                <rect class="bot-mouth" x="2" y="5" width="1" height="1"/>
                <rect class="bot-mouth" x="7" y="5" width="1" height="1"/>
                <rect class="bot-mouth" x="3" y="4" width="4" height="1"/>
            </g>
        </svg>
    </div>
    
    <div class="message-area">
        <span class="message-text" id="bot-message"></span>
        <span class="cursor"></span>
    </div>
    
    <div class="version-badge">v5.1</div>
    
    <svg class="sound-toggle" id="sound-toggle" viewBox="0 0 8 8" xmlns="http://www.w3.org/2000/svg" onclick="toggleSound()">
        <!-- Bell On -->
        <g class="bell-on">
            <rect class="bell-pixel" x="3" y="0" width="2" height="1"/>
            <rect class="bell-pixel" x="2" y="1" width="4" height="1"/>
            <rect class="bell-pixel" x="1" y="2" width="6" height="3"/>
            <rect class="bell-pixel" x="0" y="5" width="8" height="1"/>
            <rect class="bell-pixel" x="3" y="6" width="2" height="1"/>
        </g>
        <!-- Bell Off (muted - X over bell) -->
        <g class="bell-off">
            <rect class="bell-pixel" x="3" y="0" width="2" height="1"/>
            <rect class="bell-pixel" x="2" y="1" width="4" height="1"/>
            <rect class="bell-pixel" x="1" y="2" width="6" height="3"/>
            <rect class="bell-pixel" x="0" y="5" width="8" height="1"/>
            <rect class="bell-pixel" x="3" y="6" width="2" height="1"/>
            <!-- X slash -->
            <rect class="bell-pixel" style="fill:#F23674" x="0" y="0" width="1" height="1"/>
            <rect class="bell-pixel" style="fill:#F23674" x="1" y="1" width="1" height="1"/>
            <rect class="bell-pixel" style="fill:#F23674" x="2" y="2" width="1" height="1"/>
            <rect class="bell-pixel" style="fill:#F23674" x="5" y="5" width="1" height="1"/>
            <rect class="bell-pixel" style="fill:#F23674" x="6" y="6" width="1" height="1"/>
            <rect class="bell-pixel" style="fill:#F23674" x="7" y="7" width="1" height="1"/>
        </g>
    </svg>
</div>
"""

# =============================================================================
# BOT JS - Animations and Interactions
# =============================================================================

BOT_JS = """
// Bot state
let botState = {
    sleeping: false,
    lastActivity: Date.now(),
    soundEnabled: false,
    messageQueue: [],
    isTyping: false
};

// Sound effects (Web Audio API - lightweight blips)
let audioContext = null;

function initAudio() {
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
}

function playBlip(type) {
    if (!botState.soundEnabled || !audioContext) return;
    
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    if (type === 'open') {
        oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
        oscillator.frequency.exponentialRampToValueAtTime(1200, audioContext.currentTime + 0.1);
    } else if (type === 'close') {
        oscillator.frequency.setValueAtTime(1200, audioContext.currentTime);
        oscillator.frequency.exponentialRampToValueAtTime(800, audioContext.currentTime + 0.1);
    }
    
    gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.15);
    
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.15);
}

function toggleSound() {
    initAudio();
    botState.soundEnabled = !botState.soundEnabled;
    const toggle = document.getElementById('sound-toggle');
    if (botState.soundEnabled) {
        toggle.classList.remove('muted');
        playBlip('open');
    } else {
        toggle.classList.add('muted');
    }
    localStorage.setItem('dryrunSoundEnabled', botState.soundEnabled);
}

// Load saved sound preference
function loadSoundPreference() {
    const saved = localStorage.getItem('dryrunSoundEnabled');
    if (saved === 'true') {
        botState.soundEnabled = true;
        document.getElementById('sound-toggle').classList.remove('muted');
    } else {
        document.getElementById('sound-toggle').classList.add('muted');
    }
}

// Bot expressions
function setBotExpression(expression) {
    const bot = document.getElementById('pixel-bot');
    bot.className = 'pixel-bot bot-' + expression;
}

function setBotLoading(loading) {
    const bot = document.getElementById('pixel-bot');
    if (loading) {
        bot.classList.add('bot-loading');
    } else {
        bot.classList.remove('bot-loading');
    }
}

// Sleep mode
function checkSleepMode() {
    const idleTime = Date.now() - botState.lastActivity;
    const fiveMinutes = 5 * 60 * 1000;
    
    if (idleTime > fiveMinutes && !botState.sleeping) {
        botState.sleeping = true;
        document.getElementById('pixel-bot').classList.add('bot-sleeping');
    }
}

function wakeBot() {
    botState.lastActivity = Date.now();
    if (botState.sleeping) {
        botState.sleeping = false;
        document.getElementById('pixel-bot').classList.remove('bot-sleeping');
    }
}

// Typewriter effect
function typeMessage(text, type) {
    return new Promise((resolve) => {
        const msgEl = document.getElementById('bot-message');
        msgEl.className = 'message-text ' + (type || 'info');
        msgEl.textContent = '';
        
        let i = 0;
        const speed = 30; // ms per character
        
        function typeChar() {
            if (i < text.length) {
                msgEl.textContent += text.charAt(i);
                i++;
                setTimeout(typeChar, speed);
            } else {
                resolve();
            }
        }
        typeChar();
    });
}

async function showBotMessage(text, type) {
    wakeBot();
    botState.messageQueue.push({ text, type });
    
    if (botState.isTyping) return;
    
    botState.isTyping = true;
    
    while (botState.messageQueue.length > 0) {
        const msg = botState.messageQueue.shift();
        await typeMessage(msg.text, msg.type);
        
        // Wait before next message or clear
        if (botState.messageQueue.length > 0) {
            await new Promise(r => setTimeout(r, 2000));
        }
    }
    
    botState.isTyping = false;
    
    // Clear message after 10 seconds if no new messages
    setTimeout(() => {
        if (!botState.isTyping && botState.messageQueue.length === 0) {
            document.getElementById('bot-message').textContent = '';
        }
    }, 10000);
}

// Trade notifications
function onTradeOpen(strategy, direction, price) {
    playBlip('open');
    setBotExpression('happy');
    showBotMessage(strategy + ': ' + direction.toUpperCase() + ' @ $' + price.toFixed(2), 'trade');
}

function onTradeClose(strategy, result, pnl) {
    playBlip('close');
    if (pnl >= 0) {
        setBotExpression('happy');
        showBotMessage(strategy + ': +$' + pnl.toFixed(2) + ' WIN', 'win');
    } else {
        setBotExpression('sad');
        showBotMessage(strategy + ': -$' + Math.abs(pnl).toFixed(2) + ' LOSS', 'loss');
        // Return to happy after 5 seconds
        setTimeout(() => setBotExpression('happy'), 5000);
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    loadSoundPreference();
    showBotMessage('System online - monitoring ' + Object.keys(positions).length + ' strategies', 'info');
    
    // Check for sleep mode every minute
    setInterval(checkSleepMode, 60000);
});
"""
