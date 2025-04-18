# reservation_mpi.py

from mpi4py import MPI
import socket, json, uuid, select

SELECTION_TIMEOUT = 10  # seconds

class Tags:
    WORK   = 0
    RESULT = 1

def wait_for_selection(sel_sock, match_id, category, user_id, timeout):
    sel_sock.sendall(json.dumps({
        "cmd":      "SUBSCRIBE",
        "match_id": match_id,
        "category": category,
        "user":     user_id
    }).encode() + b"\n")

    ready, _, _ = select.select([sel_sock], [], [], timeout)
    if ready:
        msg = sel_sock.recv(1024).decode().strip()
        if not msg:
            return None
        data = json.loads(msg)
        return data.get("seat_id")
    return None

def handle_reservation(user_request):
    return uuid.uuid4().int % 2 == 0

def coordinator(req_host, req_port):
    comm = MPI.COMM_WORLD
    size = comm.Get_size()

    # connect to request server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((req_host, req_port))

    # --- 1) Initial seeding: no in‑flight jobs yet, so explicitly ask NEXT ---
    for worker_rank in range(1, size):
        sock.sendall(json.dumps({"cmd": "NEXT"}).encode() + b"\n")
        line = sock.recv(4096).decode().strip()
        req = json.loads(line)
        comm.send(
            (req["match_id"], req["category"], req["user"]),
            dest=worker_rank,
            tag=Tags.WORK
        )

    status = MPI.Status()
    # --- 2) Main loop: for each DONE from a worker, echo it, then read the *server‑pushed* next ---
    while True:
        match_id, category, user_done = comm.recv(
            source=MPI.ANY_SOURCE, tag=Tags.RESULT, status=status
        )
        worker_rank = status.Get_source()

        # notify server that this user is done
        done_msg = {"cmd":"DONE","match_id": match_id, "category": category, "user": user_done}
        sock.sendall(json.dumps(done_msg).encode() + b"\n")

        # now the server *pushes* the next request immediately—just read it
        line = sock.recv(4096).decode().strip()
        req = json.loads(line)
        comm.send(
            (req["match_id"], req["category"], req["user"]),
            dest=worker_rank,
            tag=Tags.WORK
        )

def worker(sel_host, sel_port):
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()

    sel_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sel_sock.connect((sel_host, sel_port))

    while True:
        m, c, u = comm.recv(source=0, tag=Tags.WORK)
        print(f"[Worker {rank}] Serving {m}-{c}:{u}")

        seat = wait_for_selection(sel_sock, m, c, u, SELECTION_TIMEOUT)
        if seat:
            print(f"[Worker {rank}] {u} got seat={seat}")
            success = True
        else:
            print(f"[Worker {rank}] {u} timed out")
            success = False

        # echo back the *same* triple
        comm.send((m, c, u), dest=0, tag=Tags.RESULT)

def main():
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    if rank == 0:
        coordinator(req_host="127.0.0.1", req_port=5000)
    else:
        worker(sel_host="127.0.0.1", sel_port=6000)

if __name__ == "__main__":
    main()
