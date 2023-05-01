# raft.py
import time
import threading
from models import SessionLocals, User
import random  # Added for simulating network latency
import asyncio
from models import databases_list 
from concurrent.futures import ThreadPoolExecutor



class RaftNode:
    def __init__(self, node_id, role):
        self.node_id = node_id
        self.db = databases_list[node_id] # Assign corresponding database 
        self.role = role
        self.state = "follower"
        self.leader_id = None
        self.term = 0
        self.votes_received = 0
        self.election_timeout = random.uniform(10, 15)
        self.heartbeat_interval = 1.5
        self.last_heartbeat_received = time.time()
        self.session = SessionLocals[self.node_id]()
        self.key_value_store = {}
        self.log = []
        self.commit_index = -1
        self.last_applied = -1

    def become_leader(self):
        self.state = "leader"
        self.leader_id = self.node_id
        print(f"Node {self.node_id} (DB: {self.db}) became the leader")

    def become_follower(self, leader_id=None):
        if self.state != "follower" or (self.state == "follower" and self.leader_id != leader_id):
            print(f"Node {self.node_id} (DB: {self.db}) became a follower of Node {leader_id}")
            self.state = "follower"
            self.leader_id = leader_id


    async def run(self):
        while True:
            if self.state == "follower":
                if time.time() - self.last_heartbeat_received > self.election_timeout:
                    await self.start_election()
            elif self.state == "leader":
                await self.send_heartbeats()
                await asyncio.sleep(self.heartbeat_interval)

    async def start_election(self):
        self.state = "candidate"
        self.term += 1
        self.votes_received = 1  # Vote for itself
        await self.send_request_vote()

    async def send_request_vote(self):
        last_log_index = len(self.log) - 1
        last_log_term = self.log[last_log_index]["term"] if last_log_index >= 0 else -1
        for node in nodes:
            if node.node_id != self.node_id:
                await asyncio.sleep(random.uniform(0.1, 0.5))  # Add a sleep statement to simulate network latency
                t = threading.Thread(target=node.receive_request_vote, args=(self.node_id, self.term, last_log_index, last_log_term))
                t.start()


    def receive_request_vote(self, candidate_id, candidate_term, candidate_last_log_index, candidate_last_log_term):
        if self.term <= candidate_term:
            last_log_index = len(self.log) - 1
            last_log_term = self.log[last_log_index]["term"] if last_log_index >= 0 else -1

            if candidate_last_log_term > last_log_term or (candidate_last_log_term == last_log_term and candidate_last_log_index >= last_log_index):
                self.term = candidate_term
                self.state = "follower"
                self.leader_id = None
                self.last_heartbeat_received = time.time()
                t = threading.Thread(target=nodes[candidate_id].receive_vote, args=(self.node_id,))
                t.start()

    def receive_vote(self, voter_id):
        self.votes_received += 1
        if self.state == "candidate" and self.votes_received > len(nodes) // 2:
            self.become_leader()

    async def send_heartbeats(self):
        success_count = 1  # Count the leader's success
        for node in nodes:
            if node.node_id != self.node_id:
                await asyncio.sleep(random.uniform(0.01, 0.1))  # Reduce the range of network latency
                success, _ = await node.receive_heartbeat(self.node_id, self.term, self.commit_index, self.log)
                if success:
                    success_count += 1

        if success_count > len(nodes) // 2:
            self.commit_index = len(self.log) - 1



    async def receive_heartbeat(self, leader_id, leader_term, leader_commit_index, leader_log):
        success = False
        if leader_term >= self.term:
            self.last_heartbeat_received = time.time()
            self.become_follower(leader_id)
            self.term = leader_term

            # Log matching
            local_log_len = len(self.log)
            leader_log_len = len(leader_log)

            if local_log_len > 0 and leader_log_len > 0:
                for index, entry in enumerate(leader_log):
                    if index >= local_log_len or self.log[index]["term"] != entry["term"]:
                        self.log = self.log[:index] + leader_log[index:]
                        break
            elif leader_log_len > 0:
                self.log = leader_log

            # Update commit index
            if leader_commit_index > self.commit_index:
                self.commit_index = min(leader_commit_index, len(self.log) - 1)

            # Apply committed entries
            while self.last_applied < self.commit_index:
                self.last_applied += 1
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self.apply_log_entry, self.log[self.last_applied])


            success = True

        return success, self.commit_index


    def apply_log_entry(self, entry):
        # Apply the log entry to the state machine (e.g., updating the session)
        if "command" in entry:
            command = entry["command"]
            # Assuming the command is a tuple (operation, key, value)
            operation, key, value = command
            if operation == "set":
                with self.session.begin():
                    # Check if the user already exists
                    result = self.session.query(User).filter_by(email=key).first()
                    if result is not None:
                        self.session.delete(result)
                    filtered_value = {k: v for k, v in value.items() if k != '_sa_instance_state'}
                    user = User(**filtered_value)
                    self.session.add(user)
                    self.session.flush()
                    self.session.refresh(user)
                    self.session.commit()
            elif operation == "delete":
                with self.session.begin():
                    result = self.session.query(User).filter_by(email=key).first()
                    if result is not None:
                        self.session.delete(result)
                        self.session.commit()


    def handle_leader_failure(self):
        # If the leader node fails, promote the synchronous node as the new leader
        # and one of the asynchronous nodes as the new synchronous node.
        if self.state == "follower" and self.role == "sync":
            self.start_election()
            # If this synchronous node becomes the leader, change the role of one of the asynchronous nodes to "sync".
            if self.state == "leader":
                for node in nodes:
                    if node.role == "async":
                        node.role = "sync"
                        break

# handle snychronous node failures , if there is no synchronous node at all, promote only one of the asynchronous nodes as the new synchronous node.

    def handle_sync_node_failure(self):
        if self.state == "follower" and self.role == "sync":
            self.start_election()
            if self.state == "leader":
                for node in nodes:
                    if node.role == "async":
                        node.role = "sync"
                        break

                    

   

# Initialize your nodes here (specify the roles for each node: "sync" or "async")
nodes = [RaftNode(i, "sync" if i == 1 else "async") for i in range(7)]

# assign a leader yourself for only once at the beginning
nodes[0].become_leader()

# Run each node in a separate thread
for node in nodes:
    t = threading.Thread(target=asyncio.run, args=(node.run(),))
    t.start()



# # Simulate leader failure
# time.sleep(5)
# nodes[0].handle_leader_failure()

