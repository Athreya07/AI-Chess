import math
import random

# Piece base values (centipawns)
piece_score = {
    "K": 20000,
    "Q": 900,
    "R": 500,
    "B": 330,
    "N": 320,
    "P": 100
}

# Piece-square tables: bonus/penalty per square (from White's perspective).
# Black uses these mirrored (row 7-r).
pst = {
    "P": [
        [ 0,  0,  0,  0,  0,  0,  0,  0],
        [50, 50, 50, 50, 50, 50, 50, 50],
        [10, 10, 20, 30, 30, 20, 10, 10],
        [ 5,  5, 10, 25, 25, 10,  5,  5],
        [ 0,  0,  0, 20, 20,  0,  0,  0],
        [ 5, -5,-10,  0,  0,-10, -5,  5],
        [ 5, 10, 10,-20,-20, 10, 10,  5],
        [ 0,  0,  0,  0,  0,  0,  0,  0]
    ],
    "N": [
        [-50,-40,-30,-30,-30,-30,-40,-50],
        [-40,-20,  0,  0,  0,  0,-20,-40],
        [-30,  0, 10, 15, 15, 10,  0,-30],
        [-30,  5, 15, 20, 20, 15,  5,-30],
        [-30,  0, 15, 20, 20, 15,  0,-30],
        [-30,  5, 10, 15, 15, 10,  5,-30],
        [-40,-20,  0,  5,  5,  0,-20,-40],
        [-50,-40,-30,-30,-30,-30,-40,-50]
    ],
    "B": [
        [-20,-10,-10,-10,-10,-10,-10,-20],
        [-10,  0,  0,  0,  0,  0,  0,-10],
        [-10,  0,  5, 10, 10,  5,  0,-10],
        [-10,  5,  5, 10, 10,  5,  5,-10],
        [-10,  0, 10, 10, 10, 10,  0,-10],
        [-10, 10, 10, 10, 10, 10, 10,-10],
        [-10,  5,  0,  0,  0,  0,  5,-10],
        [-20,-10,-10,-10,-10,-10,-10,-20]
    ],
    "R": [
        [ 0,  0,  0,  0,  0,  0,  0,  0],
        [ 5, 10, 10, 10, 10, 10, 10,  5],
        [-5,  0,  0,  0,  0,  0,  0, -5],
        [-5,  0,  0,  0,  0,  0,  0, -5],
        [-5,  0,  0,  0,  0,  0,  0, -5],
        [-5,  0,  0,  0,  0,  0,  0, -5],
        [-5,  0,  0,  0,  0,  0,  0, -5],
        [ 0,  0,  0,  5,  5,  0,  0,  0]
    ],
    "Q": [
        [-20,-10,-10, -5, -5,-10,-10,-20],
        [-10,  0,  0,  0,  0,  0,  0,-10],
        [-10,  0,  5,  5,  5,  5,  0,-10],
        [ -5,  0,  5,  5,  5,  5,  0, -5],
        [  0,  0,  5,  5,  5,  5,  0, -5],
        [-10,  5,  5,  5,  5,  5,  0,-10],
        [-10,  0,  5,  0,  0,  0,  0,-10],
        [-20,-10,-10, -5, -5,-10,-10,-20]
    ],
    "K": [
        [-30,-40,-40,-50,-50,-40,-40,-30],
        [-30,-40,-40,-50,-50,-40,-40,-30],
        [-30,-40,-40,-50,-50,-40,-40,-30],
        [-30,-40,-40,-50,-50,-40,-40,-30],
        [-20,-30,-30,-40,-40,-30,-30,-20],
        [-10,-20,-20,-20,-20,-20,-20,-10],
        [ 20, 20,  0,  0,  0,  0, 20, 20],
        [ 20, 30, 10,  0,  0, 10, 30, 20]
    ]
}

CHECKMATE = 100000
STALEMATE = 0


def evaluate_board(gs):
    """
    Static evaluation. Positive = good for White, negative = good for Black.
    Combines material counts with piece-square table bonuses.
    """
    if gs.checkmate:
        # The side that just moved delivered checkmate; whiteToMove is now the loser.
        return -CHECKMATE if gs.whiteToMove else CHECKMATE
    if gs.stalemate:
        return STALEMATE

    score = 0
    for r in range(8):
        for c in range(8):
            piece = gs.board[r][c]
            if piece == "--":
                continue
            color, ptype = piece[0], piece[1]
            # Material
            value = piece_score[ptype]
            # Positional bonus from PST
            if color == "w":
                bonus = pst[ptype][r][c]
                score += value + bonus
            else:
                # Mirror the table for black
                bonus = pst[ptype][7 - r][c]
                score -= value + bonus
    return score


def order_moves(moves, gs):
    """
    Simple move-ordering heuristic: score captures first (MVV-LVA style),
    then non-captures. Better ordering improves alpha-beta cutoffs.
    """
    def move_priority(move):
        if move.pieceCaptured != "--":
            # Victim value - attacker value: capture a queen with a pawn = high priority
            return piece_score.get(move.pieceCaptured[1], 0) - piece_score.get(move.pieceMoved[1], 0) / 10
        return 0
    return sorted(moves, key=move_priority, reverse=True)


def minimax(gs, depth, alpha, beta, maximizing):
    """
    Alpha-beta minimax with move ordering and early termination.
    Returns a numeric evaluation score.
    """
    # Terminal node or max depth reached
    if depth == 0:
        return evaluate_board(gs)

    moves = gs.get_valid_moves()

    # Checkmate / stalemate detected by engine after get_valid_moves sets the flag
    if gs.checkmate or gs.stalemate:
        return evaluate_board(gs)

    if not moves:
        return evaluate_board(gs)

    # Order moves for better pruning
    moves = order_moves(moves, gs)

    if maximizing:
        best = -math.inf
        for move in moves:
            gs.make_move(move)
            score = minimax(gs, depth - 1, alpha, beta, False)
            gs.undo_move()
            if score > best:
                best = score
            if score > alpha:
                alpha = score
            if beta <= alpha:
                break  # Beta cutoff
        return best
    else:
        best = math.inf
        for move in moves:
            gs.make_move(move)
            score = minimax(gs, depth - 1, alpha, beta, True)
            gs.undo_move()
            if score < best:
                best = score
            if score < beta:
                beta = score
            if beta <= alpha:
                break  # Alpha cutoff
        return best


def find_best_move(gs, depth=3):
    """
    Find the best move for the current player using alpha-beta minimax.
    Depth 3 is fast and reasonably strong for most positions.
    Returns a Move object or None if no legal moves exist.
    """
    valid_moves = gs.get_valid_moves()
    if not valid_moves:
        return None

    # Small shuffle so equal-score lines vary each game
    random.shuffle(valid_moves)
    valid_moves = order_moves(valid_moves, gs)

    best_move = None
    maximizing = gs.whiteToMove  # White maximizes, Black minimizes

    if maximizing:
        best_score = -math.inf
        for move in valid_moves:
            gs.make_move(move)
            score = minimax(gs, depth - 1, -math.inf, math.inf, False)
            gs.undo_move()
            if score > best_score:
                best_score = score
                best_move = move
    else:
        best_score = math.inf
        for move in valid_moves:
            gs.make_move(move)
            score = minimax(gs, depth - 1, -math.inf, math.inf, True)
            gs.undo_move()
            if score < best_score:
                best_score = score
                best_move = move

    # Fallback (should not be reached if valid_moves is non-empty)
    return best_move if best_move is not None else valid_moves[0]
