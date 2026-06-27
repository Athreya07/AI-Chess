from flask import Flask, render_template, request, jsonify
from engine import GameState, Move
from ai import find_best_move

app = Flask(__name__)
gs = GameState()


def serialize_move(move):
    return {
        "startRow": move.startRow,
        "startCol": move.startCol,
        "endRow": move.endRow,
        "endCol": move.endCol,
        "notation": move.getChessNotation(),
        "isCastleMove": move.isCastleMove
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/state", methods=["GET"])
def get_state():
    valid_moves = gs.get_valid_moves()
    in_check = False
    if not gs.checkmate and not gs.stalemate:
        in_check = gs.in_check()

    return jsonify({
        "board": gs.board,
        "whiteToMove": gs.whiteToMove,
        "checkmate": gs.checkmate,
        "stalemate": gs.stalemate,
        "inCheck": in_check,
        "whiteKingLocation": list(gs.whiteKingLocation),
        "blackKingLocation": list(gs.blackKingLocation),
        "validMoves": [serialize_move(m) for m in valid_moves]
    })


@app.route("/move", methods=["POST"])
def make_move():
    data = request.json
    if not data:
        return jsonify({"success": False, "error": "No data received"})

    try:
        start_sq = (int(data["startRow"]), int(data["startCol"]))
        end_sq   = (int(data["endRow"]),   int(data["endCol"]))
    except (KeyError, ValueError) as e:
        return jsonify({"success": False, "error": f"Bad request data: {e}"})

    chess_move = Move(start_sq, end_sq, gs.board)
    valid_moves = gs.get_valid_moves()

    for vm in valid_moves:
        if chess_move == vm:
            gs.make_move(vm)
            # Refresh checkmate/stalemate flags
            gs.get_valid_moves()
            return jsonify({
                "success": True,
                "move": serialize_move(vm),
                "checkmate": gs.checkmate,
                "stalemate": gs.stalemate
            })

    return jsonify({"success": False, "error": "Illegal move"})


@app.route("/ai-move", methods=["POST"])
def ai_move():
    """
    Trigger the AI to compute and play its move.
    Using POST prevents accidental double-firing from browser pre-fetch.
    """
    if gs.checkmate or gs.stalemate:
        return jsonify({"success": False, "error": "Game over"})

    if gs.whiteToMove:
        # Safety guard: AI only plays for Black in this setup
        return jsonify({"success": False, "error": "Not AI turn"})

    move = find_best_move(gs, depth=3)
    if move is None:
        return jsonify({"success": False, "error": "No legal moves for AI"})

    gs.make_move(move)
    # Refresh checkmate/stalemate
    gs.get_valid_moves()

    return jsonify({
        "success": True,
        "move": serialize_move(move),
        "checkmate": gs.checkmate,
        "stalemate": gs.stalemate
    })


@app.route("/reset", methods=["POST"])
def reset():
    global gs
    gs = GameState()
    return jsonify({"success": True})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
