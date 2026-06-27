class CastleRights:
    def __init__(self, wks=True, bks=True, wqs=True, bqs=True):
        self.wks = wks
        self.bks = bks
        self.wqs = wqs
        self.bqs = bqs

    def copy(self):
        return CastleRights(self.wks, self.bks, self.wqs, self.bqs)


class GameState():

    def __init__(self):

        self.board = [
            ["bR","bN","bB","bQ","bK","bB","bN","bR"],
            ["bP","bP","bP","bP","bP","bP","bP","bP"],
            ["--","--","--","--","--","--","--","--"],
            ["--","--","--","--","--","--","--","--"],
            ["--","--","--","--","--","--","--","--"],
            ["--","--","--","--","--","--","--","--"],
            ["wP","wP","wP","wP","wP","wP","wP","wP"],
            ["wR","wN","wB","wQ","wK","wB","wN","wR"]
        ]

        self.whiteToMove = True
        self.moveLog = []

        self.whiteKingLocation = (7, 4)
        self.blackKingLocation = (0, 4)

        self.checkmate = False
        self.stalemate = False

        self.currentCastlingRights = CastleRights()
        self.castleRightsLog = [self.currentCastlingRights.copy()]

    # ---------------------------------------------------
    # MAKE MOVE
    # ---------------------------------------------------
    def make_move(self, move):

        self.board[move.startRow][move.startCol] = "--"
        self.board[move.endRow][move.endCol] = move.pieceMoved

        self.moveLog.append(move)
        self.whiteToMove = not self.whiteToMove

        if move.pieceMoved == "wK":
            self.whiteKingLocation = (move.endRow, move.endCol)
        elif move.pieceMoved == "bK":
            self.blackKingLocation = (move.endRow, move.endCol)
            
        # pawn promotion
        if move.isPawnPromotion:
            self.board[move.endRow][move.endCol] = move.pieceMoved[0] + 'Q'

        # Castling rook move: king moves two squares, rook jumps next to it.
        if move.isCastleMove:
            if move.endCol - move.startCol == 2:  # kingside
                self.board[move.endRow][move.endCol - 1] = self.board[move.endRow][7]
                self.board[move.endRow][7] = "--"
            else:  # queenside
                self.board[move.endRow][move.endCol + 1] = self.board[move.endRow][0]
                self.board[move.endRow][0] = "--"

        self.update_castle_rights(move)
        self.castleRightsLog.append(self.currentCastlingRights.copy())

    # ---------------------------------------------------
    # UNDO MOVE
    # ---------------------------------------------------
    def undo_move(self):

        if len(self.moveLog) != 0:
            move = self.moveLog.pop()

            self.board[move.startRow][move.startCol] = move.pieceMoved
            self.board[move.endRow][move.endCol] = move.pieceCaptured

            self.whiteToMove = not self.whiteToMove

            if move.pieceMoved == "wK":
                self.whiteKingLocation = (move.startRow, move.startCol)
            elif move.pieceMoved == "bK":
                self.blackKingLocation = (move.startRow, move.startCol)

            if move.isCastleMove:
                if move.endCol - move.startCol == 2:  # kingside
                    self.board[move.endRow][7] = self.board[move.endRow][move.endCol - 1]
                    self.board[move.endRow][move.endCol - 1] = "--"
                else:  # queenside
                    self.board[move.endRow][0] = self.board[move.endRow][move.endCol + 1]
                    self.board[move.endRow][move.endCol + 1] = "--"

            self.castleRightsLog.pop()
            self.currentCastlingRights = self.castleRightsLog[-1].copy()

    # ---------------------------------------------------
    # GET ALL LEGAL MOVES
    # ---------------------------------------------------
    def get_valid_moves(self):

        self.checkmate = False
        self.stalemate = False
        moves = self.get_all_possible_moves()

        if self.whiteToMove:
            self.get_castle_moves(self.whiteKingLocation[0], self.whiteKingLocation[1], moves)
        else:
            self.get_castle_moves(self.blackKingLocation[0], self.blackKingLocation[1], moves)

        for i in range(len(moves) - 1, -1, -1):
            self.make_move(moves[i])
            self.whiteToMove = not self.whiteToMove

            if self.in_check():
                moves.remove(moves[i])

            self.whiteToMove = not self.whiteToMove
            self.undo_move()

        if len(moves) == 0:
            if self.in_check():
                self.checkmate = True
            else:
                self.stalemate = True

        return moves

    # ---------------------------------------------------
    # CHECK DETECTION
    # ---------------------------------------------------
    def in_check(self):

        if self.whiteToMove:
            return self.square_under_attack(self.whiteKingLocation[0],
                                            self.whiteKingLocation[1])
        else:
            return self.square_under_attack(self.blackKingLocation[0],
                                            self.blackKingLocation[1])

    def square_under_attack(self, r, c):

        self.whiteToMove = not self.whiteToMove
        opponent_moves = self.get_all_possible_moves()
        self.whiteToMove = not self.whiteToMove

        for move in opponent_moves:
            if move.endRow == r and move.endCol == c:
                return True
        return False

    # ---------------------------------------------------
    # GENERATE ALL POSSIBLE MOVES
    # ---------------------------------------------------
    def get_all_possible_moves(self):

        moves = []

        for r in range(8):
            for c in range(8):
                turn = self.board[r][c][0]
                if (turn == "w" and self.whiteToMove) or \
                   (turn == "b" and not self.whiteToMove):

                    piece = self.board[r][c][1]

                    if piece == "P":
                        self.get_pawn_moves(r, c, moves)
                    elif piece == "R":
                        self.get_rook_moves(r, c, moves)
                    elif piece == "N":
                        self.get_knight_moves(r, c, moves)
                    elif piece == "B":
                        self.get_bishop_moves(r, c, moves)
                    elif piece == "Q":
                        self.get_queen_moves(r, c, moves)
                    elif piece == "K":
                        self.get_king_moves(r, c, moves)

        return moves

    def get_pawn_moves(self, r, c, moves):
        if self.whiteToMove:
            if r - 1 >= 0 and self.board[r - 1][c] == "--":
                moves.append(Move((r, c), (r - 1, c), self.board))
                if r == 6 and self.board[r - 2][c] == "--":
                    moves.append(Move((r, c), (r - 2, c), self.board))
            if r - 1 >= 0 and c - 1 >= 0:
                if self.board[r - 1][c - 1][0] == 'b':
                    moves.append(Move((r, c), (r - 1, c - 1), self.board))
            if r - 1 >= 0 and c + 1 <= 7:
                if self.board[r - 1][c + 1][0] == 'b':
                    moves.append(Move((r, c), (r - 1, c + 1), self.board))
        else:
            if r + 1 <= 7 and self.board[r + 1][c] == "--":
                moves.append(Move((r, c), (r + 1, c), self.board))
                if r == 1 and self.board[r + 2][c] == "--":
                    moves.append(Move((r, c), (r + 2, c), self.board))
            if r + 1 <= 7 and c - 1 >= 0:
                if self.board[r + 1][c - 1][0] == 'w':
                    moves.append(Move((r, c), (r + 1, c - 1), self.board))
            if r + 1 <= 7 and c + 1 <= 7:
                if self.board[r + 1][c + 1][0] == 'w':
                    moves.append(Move((r, c), (r + 1, c + 1), self.board))

    def get_rook_moves(self, r, c, moves):
        directions = ((-1, 0), (0, -1), (1, 0), (0, 1))
        enemy_color = "b" if self.whiteToMove else "w"
        for d in directions:
            for i in range(1, 8):
                endRow = r + d[0] * i
                endCol = c + d[1] * i
                if 0 <= endRow < 8 and 0 <= endCol < 8:
                    endPiece = self.board[endRow][endCol]
                    if endPiece == "--":
                        moves.append(Move((r, c), (endRow, endCol), self.board))
                    elif endPiece[0] == enemy_color:
                        moves.append(Move((r, c), (endRow, endCol), self.board))
                        break
                    else:
                        break
                else:
                    break

    def get_knight_moves(self, r, c, moves):
        knightMoves = ((-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1))
        ally_color = "w" if self.whiteToMove else "b"
        for m in knightMoves:
            endRow = r + m[0]
            endCol = c + m[1]
            if 0 <= endRow < 8 and 0 <= endCol < 8:
                endPiece = self.board[endRow][endCol]
                if endPiece[0] != ally_color:
                    moves.append(Move((r, c), (endRow, endCol), self.board))

    def get_bishop_moves(self, r, c, moves):
        directions = ((-1, -1), (-1, 1), (1, -1), (1, 1))
        enemy_color = "b" if self.whiteToMove else "w"
        for d in directions:
            for i in range(1, 8):
                endRow = r + d[0] * i
                endCol = c + d[1] * i
                if 0 <= endRow < 8 and 0 <= endCol < 8:
                    endPiece = self.board[endRow][endCol]
                    if endPiece == "--":
                        moves.append(Move((r, c), (endRow, endCol), self.board))
                    elif endPiece[0] == enemy_color:
                        moves.append(Move((r, c), (endRow, endCol), self.board))
                        break
                    else:
                        break
                else:
                    break

    def get_queen_moves(self, r, c, moves):
        self.get_rook_moves(r, c, moves)
        self.get_bishop_moves(r, c, moves)

    def get_king_moves(self, r, c, moves):
        kingMoves = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))
        ally_color = "w" if self.whiteToMove else "b"
        for i in range(8):
            endRow = r + kingMoves[i][0]
            endCol = c + kingMoves[i][1]
            if 0 <= endRow < 8 and 0 <= endCol < 8:
                endPiece = self.board[endRow][endCol]
                if endPiece[0] != ally_color:
                    moves.append(Move((r, c), (endRow, endCol), self.board))

    # ---------------------------------------------------
    # CASTLING
    # ---------------------------------------------------
    def get_castle_moves(self, r, c, moves):
        if self.square_under_attack(r, c):
            return
        if (self.whiteToMove and self.currentCastlingRights.wks) or \
           (not self.whiteToMove and self.currentCastlingRights.bks):
            self.get_kingside_castle_moves(r, c, moves)
        if (self.whiteToMove and self.currentCastlingRights.wqs) or \
           (not self.whiteToMove and self.currentCastlingRights.bqs):
            self.get_queenside_castle_moves(r, c, moves)

    def get_kingside_castle_moves(self, r, c, moves):
        if c + 2 <= 7 and self.board[r][c + 1] == "--" and self.board[r][c + 2] == "--":
            rook = "wR" if self.whiteToMove else "bR"
            if self.board[r][7] == rook:
                if not self.square_under_attack(r, c + 1) and not self.square_under_attack(r, c + 2):
                    moves.append(Move((r, c), (r, c + 2), self.board, isCastleMove=True))

    def get_queenside_castle_moves(self, r, c, moves):
        if c - 3 >= 0 and self.board[r][c - 1] == "--" and self.board[r][c - 2] == "--" and self.board[r][c - 3] == "--":
            rook = "wR" if self.whiteToMove else "bR"
            if self.board[r][0] == rook:
                if not self.square_under_attack(r, c - 1) and not self.square_under_attack(r, c - 2):
                    moves.append(Move((r, c), (r, c - 2), self.board, isCastleMove=True))

    def update_castle_rights(self, move):
        # King move removes both rights.
        if move.pieceMoved == "wK":
            self.currentCastlingRights.wks = False
            self.currentCastlingRights.wqs = False
        elif move.pieceMoved == "bK":
            self.currentCastlingRights.bks = False
            self.currentCastlingRights.bqs = False

        # Rook move removes that rook's side.
        if move.pieceMoved == "wR":
            if move.startRow == 7 and move.startCol == 0:
                self.currentCastlingRights.wqs = False
            elif move.startRow == 7 and move.startCol == 7:
                self.currentCastlingRights.wks = False
        elif move.pieceMoved == "bR":
            if move.startRow == 0 and move.startCol == 0:
                self.currentCastlingRights.bqs = False
            elif move.startRow == 0 and move.startCol == 7:
                self.currentCastlingRights.bks = False

        # Rook capture removes that rook's side too.
        if move.pieceCaptured == "wR":
            if move.endRow == 7 and move.endCol == 0:
                self.currentCastlingRights.wqs = False
            elif move.endRow == 7 and move.endCol == 7:
                self.currentCastlingRights.wks = False
        elif move.pieceCaptured == "bR":
            if move.endRow == 0 and move.endCol == 0:
                self.currentCastlingRights.bqs = False
            elif move.endRow == 0 and move.endCol == 7:
                self.currentCastlingRights.bks = False


class Move():
    ranksToRows = {"1": 7, "2": 6, "3": 5, "4": 4,
                   "5": 3, "6": 2, "7": 1, "8": 0}
    rowsToRanks = {v: k for k, v in ranksToRows.items()}
    filesToCols = {"a": 0, "b": 1, "c": 2, "d": 3,
                   "e": 4, "f": 5, "g": 6, "h": 7}
    colsToFiles = {v: k for k, v in filesToCols.items()}

    def __init__(self, startSq, endSq, board, isCastleMove=False):
        self.startRow = startSq[0]
        self.startCol = startSq[1]
        self.endRow = endSq[0]
        self.endCol = endSq[1]
        self.pieceMoved = board[self.startRow][self.startCol]
        self.pieceCaptured = board[self.endRow][self.endCol]
        self.isCastleMove = isCastleMove or (self.pieceMoved[1] == "K" and abs(self.startCol - self.endCol) == 2)
        
        self.isPawnPromotion = False
        if (self.pieceMoved == 'wP' and self.endRow == 0) or \
           (self.pieceMoved == 'bP' and self.endRow == 7):
            self.isPawnPromotion = True

        self.moveID = self.startRow * 1000 + self.startCol * 100 + self.endRow * 10 + self.endCol

    def __eq__(self, other):
        if isinstance(other, Move):
            return self.moveID == other.moveID
        return False

    def getChessNotation(self):
        if self.isCastleMove:
            return "O-O" if self.endCol - self.startCol == 2 else "O-O-O"
        return self.getRankFile(self.startRow, self.startCol) + self.getRankFile(self.endRow, self.endCol)

    def getRankFile(self, r, c):
        return self.colsToFiles[c] + self.rowsToRanks[r]
