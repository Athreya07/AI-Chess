/**
 * Chess AI — Frontend
 * Features: click-to-move, drag-and-drop, smooth animation,
 *           AI auto-move, resign button, advantage bar, captured pieces.
 */

// ---------------------------------------------------------------------------
// DOM references
// ---------------------------------------------------------------------------
const chessboard      = document.getElementById('chessboard');
const turnOrb         = document.getElementById('turn-orb');
const turnText        = document.getElementById('turn-text');
const moveHistory     = document.getElementById('move-history');
const gameOverOverlay = document.getElementById('game-over-overlay');
const gameOverText    = document.getElementById('game-over-text');
const restartBtn      = document.getElementById('restart-btn');
const resetBtn        = document.getElementById('reset-btn');
const resignBtn       = document.getElementById('resign-btn');
const messageEl       = document.getElementById('message');

// Advantage bar
const advWhiteFill    = document.getElementById('adv-white-fill');
const advBlackFill    = document.getElementById('adv-black-fill');
const advWhiteLabel   = document.getElementById('adv-white-label');
const advBlackLabel   = document.getElementById('adv-black-label');
const blackCaptures   = document.getElementById('black-captures');
const whiteCaptures   = document.getElementById('white-captures');

// Resign dialog
const resignDialog    = document.getElementById('resign-dialog');
const resignConfirm   = document.getElementById('resign-confirm');
const resignCancel    = document.getElementById('resign-cancel');

// ---------------------------------------------------------------------------
// Piece values for material counting (centipawns)
// ---------------------------------------------------------------------------
const PIECE_VALUE = { P: 1, N: 3, B: 3, R: 5, Q: 9, K: 0 };

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let selectedSquare = null;
let isHumanTurn    = true;
let isBusy         = false;
let gameOver       = false;
let totalMoves     = 0;
let currentBoard   = [];
let validMoves     = [];

// Drag state
let dragPiece  = null;
let dragSrc    = null;
let dragOffset = { x: 0, y: 0 };

// ---------------------------------------------------------------------------
// Board construction
// ---------------------------------------------------------------------------
function createBoard() {
    chessboard.innerHTML = '';
    for (let r = 0; r < 8; r++) {
        for (let c = 0; c < 8; c++) {
            const sq = document.createElement('div');
            sq.className = `square ${(r + c) % 2 === 0 ? 'light-square' : 'dark-square'}`;
            sq.dataset.row = r;
            sq.dataset.col = c;
            sq.addEventListener('click',      () => handleSquareClick(r, c));
            sq.addEventListener('mousedown',  e  => onDragStart(e, r, c));
            sq.addEventListener('touchstart', e  => onDragStart(e, r, c), { passive: false });
            chessboard.appendChild(sq);
        }
    }
}

function getSquare(r, c) {
    return chessboard.querySelector(`.square[data-row="${r}"][data-col="${c}"]`);
}

// ---------------------------------------------------------------------------
// Fetch game state
// ---------------------------------------------------------------------------
async function fetchState() {
    try {
        const res   = await fetch('/state');
        const state = await res.json();
        currentBoard = state.board;
        validMoves   = state.validMoves || [];
        renderBoard(state);
        updateAdvantage(state.board);
        updateStatus(state);
        return state;
    } catch (err) {
        console.error('[fetchState] failed:', err);
        showMessage('Could not load game state. Is the server running?');
    }
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------
function renderBoard(state) {
    clearHighlights();
    for (let r = 0; r < 8; r++) {
        for (let c = 0; c < 8; c++) {
            const sq    = getSquare(r, c);
            sq.innerHTML = '';
            const piece = state.board[r][c];
            if (piece !== '--') {
                const img = document.createElement('img');
                img.src       = `/static/images/${piece}.png`;
                img.alt       = piece;
                img.draggable = false;
                sq.appendChild(img);
            }
        }
    }
    if (state.inCheck && !state.checkmate) {
        const king = state.whiteToMove ? state.whiteKingLocation : state.blackKingLocation;
        getSquare(king[0], king[1]).classList.add('in-check');
    }
}

function updateStatus(state) {
    if (state.checkmate) {
        const winner = state.whiteToMove ? 'Black wins' : 'White wins';
        endGame(`Checkmate — ${winner}`);
        turnText.textContent = winner;
        turnText.classList.remove('thinking');
        turnOrb.className    = state.whiteToMove ? 'orb black' : 'orb white';
        return;
    }
    if (state.stalemate) {
        endGame('Stalemate — Draw');
        turnText.textContent = 'Draw';
        turnText.classList.remove('thinking');
        turnOrb.className    = 'orb white';
        return;
    }

    if (state.whiteToMove) {
        turnOrb.className    = 'orb white';
        turnText.textContent = state.inCheck ? 'White to move — Check' : 'White to move';
        turnText.classList.remove('thinking');
        isHumanTurn = true;
        isBusy      = false;
        setResignEnabled(true);
    } else {
        turnOrb.className    = 'orb black';
        turnText.textContent = 'AI thinking...';
        turnText.classList.add('thinking');
        isHumanTurn = false;
        setResignEnabled(false);
        setTimeout(triggerAIMove, 30);
    }
}

// ---------------------------------------------------------------------------
// Advantage bar + captured pieces
// ---------------------------------------------------------------------------
function computeMaterial(board) {
    let white = 0, black = 0;
    const whiteCaptured = [];  // pieces Black has captured (white pieces gone)
    const blackCaptured = [];  // pieces White has captured (black pieces gone)

    // Starting piece counts
    const start = { P: 8, N: 2, B: 2, R: 2, Q: 1 };

    // Count what's on the board
    const onBoard = { w: {}, b: {} };
    for (const row of board) {
        for (const piece of row) {
            if (piece === '--') continue;
            const color = piece[0], type = piece[1];
            if (type === 'K') continue;
            onBoard[color][type] = (onBoard[color][type] || 0) + 1;
        }
    }

    // Derive captures: pieces missing from starting position
    for (const type of ['P','N','B','R','Q']) {
        const wCount = onBoard['w'][type] || 0;
        const bCount = onBoard['b'][type] || 0;
        const wMissing = start[type] - wCount; // white pieces captured by Black
        const bMissing = start[type] - bCount; // black pieces captured by White

        for (let i = 0; i < wMissing; i++) whiteCaptured.push('w' + type);
        for (let i = 0; i < bMissing; i++) blackCaptured.push('b' + type);

        white += wCount * PIECE_VALUE[type];
        black += bCount * PIECE_VALUE[type];
    }

    return { white, black, whiteCaptured, blackCaptured };
}

// Piece type display order (most valuable first for captured display)
const CAPTURE_ORDER = ['Q','R','B','N','P'];

function sortCaptures(pieces) {
    return pieces.slice().sort((a, b) =>
        CAPTURE_ORDER.indexOf(a[1]) - CAPTURE_ORDER.indexOf(b[1])
    );
}

function updateAdvantage(board) {
    const { white, black, whiteCaptured, blackCaptured } = computeMaterial(board);
    const total = white + black || 1;
    const diff  = white - black; // positive = white leads

    // Bar fill: white side grows from left
    const whitePct = Math.round((white / total) * 100);
    const blackPct = 100 - whitePct;
    advWhiteFill.style.width = `${whitePct}%`;
    advBlackFill.style.width = `${blackPct}%`;

    // Labels: show lead amount for the leading side, 0 for trailing
    if (diff > 0) {
        advWhiteLabel.textContent = `+${diff}`;
        advBlackLabel.textContent = '';
    } else if (diff < 0) {
        advWhiteLabel.textContent = '';
        advBlackLabel.textContent = `+${Math.abs(diff)}`;
    } else {
        advWhiteLabel.textContent = '=';
        advBlackLabel.textContent = '';
    }

    // Render captured pieces
    // Black captures = white pieces missing = shown above bar (black's trophies)
    renderCaptured(blackCaptures, sortCaptures(whiteCaptured), diff < 0 ? Math.abs(diff) : 0);
    // White captures = black pieces missing = shown below bar (white's trophies)
    renderCaptured(whiteCaptures, sortCaptures(blackCaptured), diff > 0 ? diff : 0);
}

function renderCaptured(container, pieces, lead) {
    container.innerHTML = '';
    for (const piece of pieces) {
        const img = document.createElement('img');
        img.src = `/static/images/${piece}.png`;
        img.alt = piece;
        container.appendChild(img);
    }
    if (lead > 0) {
        const badge = document.createElement('span');
        badge.className   = 'material-lead';
        badge.textContent = `+${lead}`;
        container.appendChild(badge);
    }
}

// ---------------------------------------------------------------------------
// Click-to-move
// ---------------------------------------------------------------------------
function handleSquareClick(r, c) {
    if (!isHumanTurn || isBusy) return;
    const piece = currentBoard?.[r]?.[c];

    if (!selectedSquare) {
        if (piece && piece.startsWith('w')) selectSquare(r, c);
        return;
    }

    const { r: sr, c: sc } = selectedSquare;

    if (sr === r && sc === c) {
        clearHighlights();
        selectedSquare = null;
        return;
    }

    if (piece && piece.startsWith('w')) {
        selectSquare(r, c);
        return;
    }

    submitMove(sr, sc, r, c);
}

function selectSquare(r, c) {
    clearHighlights();
    selectedSquare = { r, c };
    getSquare(r, c).classList.add('selected');
    showLegalHints(r, c);
}

function showLegalHints(r, c) {
    validMoves
        .filter(m => m.startRow === r && m.startCol === c)
        .forEach(m => {
            const target  = getSquare(m.endRow, m.endCol);
            const isEmpty = currentBoard[m.endRow][m.endCol] === '--';
            target.classList.add(isEmpty ? 'legal-move' : 'capture-move');
        });
}

// ---------------------------------------------------------------------------
// Drag-and-drop
// ---------------------------------------------------------------------------
function onDragStart(e, r, c) {
    if (!isHumanTurn || isBusy) return;
    const piece = currentBoard?.[r]?.[c];
    if (!piece || !piece.startsWith('w')) return;

    e.preventDefault();

    const sq  = getSquare(r, c);
    const img = sq.querySelector('img');
    if (!img) return;

    const rect    = img.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;

    dragOffset = { x: clientX - rect.left, y: clientY - rect.top };
    dragSrc    = { r, c };

    dragPiece = img.cloneNode();
    dragPiece.style.cssText = `
        position: fixed;
        width: ${rect.width}px; height: ${rect.height}px;
        left: ${rect.left}px;  top: ${rect.top}px;
        pointer-events: none; z-index: 9999;
        opacity: 0.9; transform: scale(1.1);
        filter: drop-shadow(0 8px 12px rgba(0,0,0,0.5));
        transition: none;
    `;
    document.body.appendChild(dragPiece);
    img.style.opacity = '0.3';

    clearHighlights();
    sq.classList.add('selected');
    showLegalHints(r, c);

    document.addEventListener('mousemove', onDragMove);
    document.addEventListener('touchmove', onDragMove, { passive: false });
    document.addEventListener('mouseup',   onDragEnd);
    document.addEventListener('touchend',  onDragEnd);
}

function onDragMove(e) {
    if (!dragPiece) return;
    e.preventDefault();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    dragPiece.style.left = `${clientX - dragOffset.x}px`;
    dragPiece.style.top  = `${clientY - dragOffset.y}px`;
}

function onDragEnd(e) {
    document.removeEventListener('mousemove', onDragMove);
    document.removeEventListener('touchmove', onDragMove);
    document.removeEventListener('mouseup',   onDragEnd);
    document.removeEventListener('touchend',  onDragEnd);

    if (!dragPiece || !dragSrc) return;

    const srcImg = getSquare(dragSrc.r, dragSrc.c)?.querySelector('img');
    if (srcImg) srcImg.style.opacity = '';

    dragPiece.style.display = 'none';
    const clientX = e.changedTouches ? e.changedTouches[0].clientX : e.clientX;
    const clientY = e.changedTouches ? e.changedTouches[0].clientY : e.clientY;
    const target  = document.elementFromPoint(clientX, clientY);
    dragPiece.style.display = '';
    dragPiece.remove();
    dragPiece = null;

    const sq = target?.closest('.square');
    if (sq) {
        const endR = parseInt(sq.dataset.row);
        const endC = parseInt(sq.dataset.col);

        if (endR === dragSrc.r && endC === dragSrc.c) {
            dragSrc = null;
            return;
        }

        const isLegal = validMoves.some(
            m => m.startRow === dragSrc.r && m.startCol === dragSrc.c &&
                 m.endRow   === endR      && m.endCol   === endC
        );

        if (isLegal) {
            const src = dragSrc;
            dragSrc   = null;
            submitMove(src.r, src.c, endR, endC);
            return;
        }
    }

    clearHighlights();
    selectedSquare = null;
    dragSrc        = null;
}

// ---------------------------------------------------------------------------
// Move submission
// ---------------------------------------------------------------------------
async function submitMove(startR, startC, endR, endC) {
    isBusy         = true;
    selectedSquare = null;
    showMessage('');
    clearHighlights();

    try {
        const res    = await fetch('/move', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ startRow: startR, startCol: startC, endRow: endR, endCol: endC })
        });
        const result = await res.json();

        if (result.success) {
            addMoveToHistory(result.move.notation);
            await animateMove(startR, startC, endR, endC);
            // Clear isBusy BEFORE fetchState so triggerAIMove is not blocked
            isBusy = false;
            await fetchState();
        } else {
            isBusy = false;
            showMessage(result.error || 'Illegal move');
            console.warn('[submitMove] rejected:', result.error);
        }
    } catch (err) {
        isBusy = false;
        showMessage('Move failed. Check the console.');
        console.error('[submitMove] error:', err);
    }
}

// ---------------------------------------------------------------------------
// AI move
// ---------------------------------------------------------------------------
async function triggerAIMove() {
    if (isBusy) return;
    isBusy = true;
    showMessage('AI thinking...');

    try {
        const res    = await fetch('/ai-move', { method: 'POST' });
        const result = await res.json();

        if (result.success) {
            addMoveToHistory(result.move.notation);
            await animateMove(
                result.move.startRow, result.move.startCol,
                result.move.endRow,   result.move.endCol
            );
            isBusy = false;
            await fetchState();
        } else {
            console.warn('[triggerAIMove] no move:', result.error);
            isBusy = false;
            await fetchState();
        }
    } catch (err) {
        isBusy = false;
        showMessage('AI move failed. Check the console.');
        console.error('[triggerAIMove] error:', err);
    }
}

// ---------------------------------------------------------------------------
// Resign
// ---------------------------------------------------------------------------
function setResignEnabled(enabled) {
    resignBtn.disabled = !enabled || gameOver;
}

resignBtn.addEventListener('click', () => {
    if (gameOver || !isHumanTurn) return;
    resignDialog.classList.remove('hidden');
});

resignCancel.addEventListener('click', () => {
    resignDialog.classList.add('hidden');
});

resignConfirm.addEventListener('click', () => {
    resignDialog.classList.add('hidden');
    endGame('White resigned — Black wins');
    turnText.textContent = 'Black wins';
    turnText.classList.remove('thinking');
    turnOrb.className    = 'orb black';
});

// ---------------------------------------------------------------------------
// Smooth piece animation
// ---------------------------------------------------------------------------
function animateMove(startR, startC, endR, endC) {
    return new Promise(resolve => {
        const srcSq = getSquare(startR, startC);
        const dstSq = getSquare(endR,   endC);
        const img   = srcSq.querySelector('img');

        if (!img) { resolve(); return; }

        const srcRect = srcSq.getBoundingClientRect();
        const dstRect = dstSq.getBoundingClientRect();

        const clone = img.cloneNode();
        clone.style.cssText = `
            position: fixed;
            width: ${srcRect.width}px; height: ${srcRect.height}px;
            left: ${srcRect.left}px;  top: ${srcRect.top}px;
            pointer-events: none; z-index: 9998;
            transition: left 180ms ease, top 180ms ease;
        `;
        document.body.appendChild(clone);

        img.style.opacity = '0';
        const dstImg = dstSq.querySelector('img');
        if (dstImg) dstImg.style.opacity = '0';

        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                clone.style.left = `${dstRect.left}px`;
                clone.style.top  = `${dstRect.top}px`;
            });
        });

        clone.addEventListener('transitionend', () => {
            clone.remove();
            if (img) img.style.opacity = '';
            resolve();
        }, { once: true });

        setTimeout(() => { clone.remove(); resolve(); }, 400);
    });
}

// ---------------------------------------------------------------------------
// Move history
// ---------------------------------------------------------------------------
function addMoveToHistory(notation) {
    totalMoves++;
    const turnNum = Math.ceil(totalMoves / 2);
    const isWhite = totalMoves % 2 !== 0;

    if (isWhite) {
        const li = document.createElement('li');
        li.innerHTML = `
            <span class="turn-num">${turnNum}.</span>
            <span class="move-white">${notation}</span>
            <span class="move-black"></span>`;
        moveHistory.appendChild(li);
    } else {
        const last = moveHistory.lastElementChild;
        if (last) last.querySelector('.move-black').textContent = notation;
    }
    moveHistory.scrollTop = moveHistory.scrollHeight;
}

// ---------------------------------------------------------------------------
// UI helpers
// ---------------------------------------------------------------------------
function endGame(text) {
    gameOver = true;
    isHumanTurn = false;
    isBusy      = true; // block further moves
    setResignEnabled(false);
    showGameOver(text);
    showMessage('');
}

function showGameOver(text) {
    gameOverText.textContent = text;
    gameOverOverlay.classList.remove('hidden');
}

function showMessage(text) {
    messageEl.textContent = text;
}

function clearHighlights() {
    chessboard.querySelectorAll('.square').forEach(sq =>
        sq.classList.remove('selected', 'legal-move', 'capture-move', 'in-check')
    );
}

async function resetGame() {
    gameOverOverlay.classList.add('hidden');
    moveHistory.innerHTML = '';
    totalMoves     = 0;
    selectedSquare = null;
    isBusy         = false;
    gameOver       = false;
    dragSrc        = null;
    if (dragPiece) { dragPiece.remove(); dragPiece = null; }
    showMessage('');
    setResignEnabled(true);
    await fetch('/reset', { method: 'POST' });
    await fetchState();
}

// ---------------------------------------------------------------------------
// Initialise
// ---------------------------------------------------------------------------
restartBtn.addEventListener('click', resetGame);
resetBtn.addEventListener('click',   resetGame);

createBoard();
fetchState();
