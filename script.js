document.addEventListener('DOMContentLoaded', () => {
    const boardElement = document.getElementById('gameBoard');
    const resetButton = document.getElementById('resetButton');
    const undoButton = document.getElementById('undoButton');
    const randomMoveButton = document.getElementById('randomMoveButton');
    const agentMoveButton = document.getElementById('agentMoveButton');
    const gameRecordElement = document.getElementById('gameRecord');
    const agentStatusElement = document.getElementById('agentStatus');
    const errorMessageElement = document.getElementById('errorMessage');
    const currentTurnElement = document.getElementById('currentTurn');
    const emptyCellsCountElement = document.getElementById('emptyCellsCount');

    // ゲーム状態を取得して描画
    const fetchGameState = async () => {
        const response = await fetch('/get_game_state');
        const gameState = await response.json();
        renderBoard(gameState.obf67);
        gameRecordElement.textContent = gameState.game_record;
        updateAgentStatus(gameState);
        updateCurrentTurn(gameState);
        updateTurnAndEmptyCells(gameState.obf67)
    };
    
    // 現在の手番の更新
    const updateCurrentTurn = (gameState) => {
        const currentTurn = gameState.obf67[65] === 'X' ? '黒' : '白';
        currentTurnElement.textContent = currentTurn;
    };

    // 空白マスの数を更新
    const updateTurnAndEmptyCells = (obf67) => {
        const emptyCellsCount = (obf67.match(/-/g) || []).length;
        emptyCellsCountElement.textContent = emptyCellsCount;
    };

    // AI操作状態の更新
    const updateAgentStatus = (gameState) => {
        const blackStatus = gameState.black_can_be_agent === 99999999 ? '可能' : '不可能';
        const whiteStatus = gameState.white_can_be_agent === 99999999 ? '可能' : '不可能';
        agentStatusElement.textContent = `黒: ${blackStatus}, 白: ${whiteStatus}`;
    };

    // ボードの描画
    const renderBoard = (obf67) => {
        boardElement.innerHTML = '';
        for (let i = 0; i < 64; i++) {
            const cell = document.createElement('div');
            cell.classList.add('cell');
            if (obf67[i] === 'X') {
                cell.classList.add('black');
            } else if (obf67[i] === 'O') {
                cell.classList.add('white');
            }
            cell.addEventListener('click', () => makeMove(i));
            boardElement.appendChild(cell);
        }
    };

    // 手を打つ
    const makeMove = async (index) => {
        const response = await fetch('/make_move', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ move: indexToCoordinate(index) })
        });
        handleResponse(response);
    };

    // レスポンス処理
    const handleResponse = async (response) => {
        const data = await response.json();
        if (data.error) {
            errorMessageElement.textContent = data.error;
        } else {
            errorMessageElement.textContent = '';
        }
        fetchGameState();
    };

    // インデックスを座標に変換
    const indexToCoordinate = (index) => {
        const row = Math.floor(index / 8);
        const col = index % 8;
        return String.fromCharCode(97 + col) + (row + 1);
    };

    // リセットボタンのイベントリスナー
    resetButton.addEventListener('click', async () => {
        const response = await fetch('/reset_game', { method: 'GET' });
        handleResponse(response);
    });

    // 手を戻すボタンのイベントリスナー
    undoButton.addEventListener('click', async () => {
        const response = await fetch('/undo_move', { method: 'GET' });
        handleResponse(response);
    });

    // ランダムな手のボタンのイベントリスナー
    randomMoveButton.addEventListener('click', async () => {
        const response = await fetch('/make_random_move', { method: 'GET' });
        handleResponse(response);
    });

    // AIに手を指させるボタンのイベントリスナー
    agentMoveButton.addEventListener('click', async () => {
        const response = await fetch('/do_agent_move', { method: 'GET' });
        handleResponse(response);
    });

    fetchGameState();
});
