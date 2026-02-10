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

/* Sound toggle (bell icon) */
.sound-toggle {
    width: 20px;
    height: 20px;
    cursor: pointer;
    flex-shrink: 0;
    opacity: 0.6;
    transition: opacity 0.2s;
}
.sound-toggle:hover {
    opacity: 1;
}
.sound-toggle.muted .bell-on { display: none; }
.sound-toggle.muted .bell-off { display: block; }
.sound-toggle .bell-on { display: block; }
.sound-toggle .bell-off { display: none; }
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
    
    <div class="sound-toggle" id="sound-toggle" onclick="toggleSound()">
        <svg class="bell-on" width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M15 17V18C15 19.6569 13.6569 21 12 21C10.3431 21 9 19.6569 9 18V17M15 17H9M15 17H18.5905C18.973 17 19.1652 17 19.3201 16.9478C19.616 16.848 19.8475 16.6156 19.9473 16.3198C19.9997 16.1643 19.9997 15.9715 19.9997 15.5859C19.9997 15.4172 19.9995 15.3329 19.9863 15.2524C19.9614 15.1004 19.9024 14.9563 19.8126 14.8312C19.7651 14.7651 19.7048 14.7048 19.5858 14.5858L19.1963 14.1963C19.0706 14.0706 19 13.9001 19 13.7224V10C19 6.134 15.866 2.99999 12 3C8.13401 3.00001 5 6.13401 5 10V13.7224C5 13.9002 4.92924 14.0706 4.80357 14.1963L4.41406 14.5858C4.29476 14.7051 4.23504 14.765 4.1875 14.8312C4.09766 14.9564 4.03815 15.1004 4.0132 15.2524C4 15.3329 4 15.4172 4 15.586C4 15.9715 4 16.1642 4.05245 16.3197C4.15225 16.6156 4.3848 16.848 4.68066 16.9478C4.83556 17 5.02701 17 5.40956 17H9" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <svg class="bell-off" width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M9 17V18C9 19.6569 10.3431 21 12 21C13.6569 21 15 19.6569 15 18V17M9 17L15 17M9 17L5.00022 17.0002C4.48738 17.0002 4.06449 16.6141 4.00673 16.1168L4 15.9998V15.4141C4 15.1489 4.10544 14.8949 4.29297 14.7073L4.80371 14.1963C4.92939 14.0706 5 13.9003 5 13.7225V9.99986C5 8.15821 5.7112 6.48267 6.87393 5.23291M15 17L18.9999 17M5 3L21 19M18.9995 12.999L19.0004 10C19.0004 6.13402 15.8665 3 12.0005 3L11.7598 3.00406C10.9548 3.03125 10.1845 3.19404 9.4707 3.47081" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
    </div>
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

// Sound effects (MP3 notification)
let notificationSound = null;

function initAudio() {
    if (!notificationSound) {
        notificationSound = new Audio('/static/notification.mp3');
        notificationSound.volume = 0.5;
    }
}

function playBlip(type) {
    if (!botState.soundEnabled || !notificationSound) return;
    notificationSound.currentTime = 0;
    notificationSound.play().catch(function() {});
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
        initAudio();
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
    var count = Object.keys(positions).length;
    var word = count === 1 ? 'strategy' : 'strategies';
    showBotMessage('System online - monitoring ' + count + ' ' + word, 'info');
    
    // Check for sleep mode every minute
    setInterval(checkSleepMode, 60000);
});
"""
