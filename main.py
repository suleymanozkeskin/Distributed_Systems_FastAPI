# main.py
from fastapi import FastAPI, HTTPException
from models import User, UserCreate, SessionLocals, databases_list
from raft import nodes
import asyncio
import time
import random  # Added for simulating network latency

app = FastAPI()

def get_leader():
    for node in nodes:
        if node.state == "leader":
            return node
    return None

async def wait_for_commit(commit_index, timeout=10):
    start_time = time.time()
    while True:
        committed_count = sum(1 for node in nodes if node.commit_index >= commit_index)
        if committed_count > len(nodes) // 2:
            break
        if time.time() - start_time > timeout:
            raise HTTPException(status_code=500, detail="Commit timeout")
        await asyncio.sleep(0.1)

@app.post("/users")
async def create_user(user: UserCreate):
    while True:
        leader = get_leader()
        if leader is None:
            await asyncio.sleep(0.1)
            continue

        # Convert UserCreate to User
        db_user = User(id=random.randint(1, 10000), name=user.name, email=user.email, location=user.location)

        # Create a log entry
        entry = {
            "term": leader.term,
            "command": ("set", db_user.email, db_user.__dict__)
        }

        # Append the log entry to the leader's log
        leader.log.append(entry)
        leader.commit_index = len(leader.log) - 1  # Update the leader's commit index

        # Wait for the log entry to be committed on the majority of the nodes
        await wait_for_commit(leader.commit_index)

        return {"detail": "User created"}



async def create_users_concurrently(num_users):
    tasks = []
    for _ in range(num_users):
        user = UserCreate(name="Test", email=f"test{random.randint(1, 10000)}@example.com", location="US")
        tasks.append(create_user(user))
    await asyncio.gather(*tasks)



@app.get("/create-users/{num_users}")
async def create_users_endpoint(num_users: int):
    await create_users_concurrently(num_users)
    return {"detail": f"Created {num_users} users concurrently"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
