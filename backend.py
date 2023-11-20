from bottle import Bottle, run, request, response, static_file
import reversi_misc
import json
import random
import re
import os
import subprocess
from typing import Optional, Tuple
import reversi_solver_misc


def get_initial_obf():
    black, white = reversi_misc.initial_position("cross")
    return reversi_misc.bitboards_to_obf(black, white, True)

# Bottleアプリケーションのインスタンスを作成
app = Bottle()

# ゲームの状態を管理する辞書（例）
initial_game_state = {
    'game_record': '',
    'obf67': get_initial_obf(),
    'gameState': 'in_progress',
    'black_can_be_agent': 99999999,
    'white_can_be_agent': 99999999,
}
game_state = initial_game_state
XO2BW = {'X': 'black', 'O': 'white'}

@app.route('/<filename:path>')
def send_static(filename):
    return static_file(filename, root='./')

@app.get("/")
def index():
    return static_file("index.html", root="./", mimetype="text/html")

@app.route('/get_game_state', method='GET')
def get_game_state():
    response.content_type = 'application/json'
    return json.dumps(game_state)

@app.route('/make_move', method='POST')
def make_move():
    global game_state
    # リクエストからデータを取得
    data = request.json
    move = data.get('move')

    # ここでゲームのロジック
    if game_state['gameState'] == 'finished':
        response.content_type = 'application/json'
        return json.dumps({'error': 'Game is already finished.'})
    assert game_state['obf67'] == reversi_misc.gamerecord_to_obf(game_state['game_record'])
    player, opponent = reversi_misc.obf_to_bitboards(game_state['obf67'])
    bb_moves = reversi_misc.get_moves(player, opponent)
    assert bb_moves > 0
    square_index = reversi_misc.str2index(move)
    if bb_moves & (1 << square_index) == 0:
        response.content_type = 'application/json'
        return json.dumps({'error': 'Illegal move.'})
    game_state[XO2BW[game_state["obf67"][65]]+'_can_be_agent'] = min(game_state[XO2BW[game_state["obf67"][65]]+'_can_be_agent'], len(game_state['game_record']))
    game_state['game_record'] += move
    game_state['obf67'] = reversi_misc.gamerecord_to_obf(game_state['game_record'])
    player, opponent = reversi_misc.obf_to_bitboards(game_state['obf67'])
    bb_moves = reversi_misc.get_moves(player, opponent)
    if bb_moves == 0:
        game_state['gameState'] = 'finished'  # PとOを入れ替えて確認していないのは、gamerecord_to_obfで確認済みだから。

    # 更新されたゲームの状態を返す
    response.content_type = 'application/json'
    return json.dumps(game_state)

@app.route('/make_random_move', method='GET')
def make_random_move():
    global game_state

    # ここでゲームのロジック
    if game_state['gameState'] == 'finished':
        response.content_type = 'application/json'
        return json.dumps({'error': 'Game is already finished.'})
    game_state[XO2BW[game_state["obf67"][65]]+'_can_be_agent'] = min(game_state[XO2BW[game_state["obf67"][65]]+'_can_be_agent'], len(game_state['game_record']))
    assert game_state['obf67'] == reversi_misc.gamerecord_to_obf(game_state['game_record'])
    player, opponent = reversi_misc.obf_to_bitboards(game_state['obf67'])
    bb_moves = reversi_misc.get_moves(player, opponent)
    assert bb_moves > 0
    movenum = bin(bb_moves).count("1")
    square_index = random.randrange(movenum)
    for i in range(64):
        if bb_moves & (1 << i) != 0:
            if square_index == 0:
                square_index = i
                break
            square_index -= 1
    assert bb_moves & (1 << square_index) > 0
    game_state['game_record'] += reversi_misc.index2str(square_index)
    game_state['obf67'] = reversi_misc.gamerecord_to_obf(game_state['game_record'])
    player, opponent = reversi_misc.obf_to_bitboards(game_state['obf67'])
    bb_moves = reversi_misc.get_moves(player, opponent)
    if bb_moves == 0:
        game_state['gameState'] = 'finished'  # PとOを入れ替えて確認していないのは、gamerecord_to_obfで確認済みだから。

    # 更新されたゲームの状態を返す
    response.content_type = 'application/json'
    return json.dumps(game_state)

@app.route('/undo_move', method='GET')
def undo_move():
    global game_state
    
    # ここでゲームのロジック
    if len(game_state['game_record']) == 0:
        response.content_type = 'application/json'
        return json.dumps({'error': 'No move to undo.'})
    game_state['game_record'] = game_state['game_record'][:-2]
    if game_state['gameState'] == 'finished':
        game_state['gameState'] = 'in_progress'
    game_state['obf67'] = reversi_misc.gamerecord_to_obf(game_state['game_record'])
    if game_state[XO2BW[game_state["obf67"][65]]+'_can_be_agent'] == len(game_state['game_record']):
        game_state[XO2BW[game_state["obf67"][65]]+'_can_be_agent'] = 99999999

    # 更新されたゲームの状態を返す
    response.content_type = 'application/json'
    return json.dumps(game_state)

@app.route('/reset_game', method='GET')
def reset_game():
    global game_state
    game_state = {
        'game_record': '',
        'obf67': get_initial_obf(),
        'gameState': 'in_progress',
        'black_can_be_agent': 99999999,
        'white_can_be_agent': 99999999,
    }

    # 更新されたゲームの状態を返す
    response.content_type = 'application/json'
    return json.dumps(game_state)

def simple_solver(player: int, opponent: int, depth: int) -> Tuple[int, str]:
    bb_moves = reversi_misc.get_moves(player, opponent)
    if bb_moves == 0:
        if reversi_misc.get_moves(opponent, player) == 0:
            return (reversi_misc.ComputeFinalScore(player, opponent), "end")
        if depth == 0:
            return (-100, "unknown")
        score = simple_solver(opponent, player, depth)[0]
        if score == -100:
            return (-100, "ps")
        return (-score, "ps")
    if depth == 0:
        return (-100, "unknown")
    best_score = -100
    best_move = ""
    for move in [i for i in range(64) if (bb_moves & (1 << i)) > 0]:
        flipped = reversi_misc.flip(move, player, opponent)
        assert flipped > 0
        score, _ = simple_solver(
            opponent ^ flipped, player ^ flipped ^ (1 << move), depth - 1
        )
        if score == -100:
            continue
        score = -score
        if score > best_score:
            best_score = score
            best_move = reversi_misc.index2str(move)
    return (best_score, best_move)


def simple_solver_root(
    player: int, opponent: int, depth: int = 3
) -> Optional[Tuple[int, str]]:
    score, move = simple_solver(player, opponent, depth)
    if score > 0:
        return (score, move)
    return None


def deploy_one_problem_to_edax(obf, n_cores):
    assert re.fullmatch(r"[-OX]{64}\s[OX];", obf) is not None
    obffilename = "obf.txt"
    with open(obffilename, "w") as f:
        f.write(obf + "\n")
    ab = 64 if obf.count("-") < 16 else 1
    cmd = f"stdbuf -oL ./Edax_mod2 -solve {obffilename} -n-tasks {n_cores} -level 60 -hash-table-size 23 -verbose 2 -alpha -{ab} -beta {ab} -width 200"
    proc = subprocess.Popen(
        cmd.strip().split(" "),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        universal_newlines=True,
        bufsize=0,
    )
    result_stdout = []
    while True:
        line = proc.stdout.readline()
        if not line and proc.poll() is not None:
            break
        if line:
            result_stdout.append(line.rstrip())
    return reversi_solver_misc.compute_one_verbose2_problem(result_stdout)[
        "principal_variation"
    ][0]


def search_best_move_from_table(filename, player, opponent):
    bb_moves = reversi_misc.get_moves(player, opponent)
    nega_max_next_result = -100
    best_i = None
    for i in range(64):
        if (bb_moves & (1 << i)) > 0:
            flipped = reversi_misc.flip(i, player, opponent)
            assert flipped > 0
            next_player = opponent ^ flipped
            next_opponent = player ^ flipped ^ (1 << i)
            next_bb_moves = reversi_misc.get_moves(next_player, next_opponent)
            pass_flag = 1
            if next_bb_moves == 0:
                if reversi_misc.get_moves(next_opponent, next_player) == 0:
                    continue
                else:
                    next_player, next_opponent = next_opponent, next_player
                    pass_flag = -1
            next_obf = reversi_misc.bitboards_to_obf(next_player, next_opponent)
            next_obf_unique = reversi_misc.obf_unique(next_obf)
            next_query = reversi_misc.obf_to_base81encoding(next_obf_unique)
            next_result = reversi_misc.read_table(next_query, filename)
            if next_result is not None:
                if next_result == "4":
                    print(f"info: game-theoretic value (for the player-to-move) of choosing {reversi_misc.index2str(i)} ∈ [-64, -2]")
                elif next_result == "3":
                    print(f"info: game-theoretic value (for the player-to-move) of choosing {reversi_misc.index2str(i)} ∈ [-64, 0]")
                elif next_result == "2":
                    print(f"info: game-theoretic value (for the player-to-move) of choosing {reversi_misc.index2str(i)} = 0")
                elif next_result == "1":
                    print(f"info: game-theoretic value (for the player-to-move) of choosing {reversi_misc.index2str(i)} ∈ [0, +64]")
                elif next_result == "0":
                    print(f"info: game-theoretic value (for the player-to-move) of choosing {reversi_misc.index2str(i)} ∈ [+2, +64]")
                if nega_max_next_result < -int(next_result) * pass_flag:
                    nega_max_next_result = -int(next_result) * pass_flag
                    best_i = i
            else:
                print(f"info: game-theoretic value (for the player-to-move) of choosing {reversi_misc.index2str(i)} is unknown")
    return best_i

def get_optimal_move(player, opponent):
    if bin(player | opponent).count("1") == 4:
        return "f5"
    dfs_answer = simple_solver_root(player, opponent)
    if dfs_answer is not None:
        print(f"info: dfs_answer = {dfs_answer[1]}")
        assert re.fullmatch(r"[a-h][1-8]", dfs_answer[1]) is not None
        return dfs_answer[1]
    if bin(player | opponent).count("1") < (64 - 36):
        filename = "all_result_abtree_encoded_sorted_unique.csv"
        table_answer = search_best_move_from_table(filename, player, opponent)
        if table_answer is not None:
            print(f"info: table_answer = {reversi_misc.index2str(table_answer)}")
            return reversi_misc.index2str(table_answer)
    n_workers = min(max(1, os.cpu_count()), 8)
    edax_answer = deploy_one_problem_to_edax(
        reversi_misc.bitboards_to_obf(player, opponent), n_workers
    )
    assert re.fullmatch(r"[a-h][1-8]", edax_answer) is not None
    print(f"info: edax_answer = {edax_answer}")
    return edax_answer


@app.route('/do_agent_move', method='GET')
def do_agent_move():
    global game_state

    # ここでゲームのロジック
    if game_state['gameState'] == 'finished':
        response.content_type = 'application/json'
        return json.dumps({'error': 'Game is already finished.'})
    if game_state[XO2BW[game_state["obf67"][65]]+'_can_be_agent'] != 99999999:
        response.content_type = 'application/json'
        return json.dumps({'error': XO2BW[game_state["obf67"][65]]+' can not be an agent.'})
    assert game_state['obf67'] == reversi_misc.gamerecord_to_obf(game_state['game_record'])
    player, opponent = reversi_misc.obf_to_bitboards(game_state['obf67'])
    move = get_optimal_move(player, opponent)
    game_state['game_record'] += move
    game_state['obf67'] = reversi_misc.gamerecord_to_obf(game_state['game_record'])
    player, opponent = reversi_misc.obf_to_bitboards(game_state['obf67'])
    bb_moves = reversi_misc.get_moves(player, opponent)
    if bb_moves == 0:
        game_state['gameState'] = 'finished'  # PとOを入れ替えて確認していないのは、gamerecord_to_obfで確認済みだから。

    # 更新されたゲームの状態を返す
    response.content_type = 'application/json'
    return json.dumps(game_state)


# WSGIサーバーでアプリケーションを実行
run(app, host='localhost', port=8080)
